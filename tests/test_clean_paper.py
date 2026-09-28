import copy
import json

import pandas as pd
import pytest
from itsdangerous import URLSafeTimedSerializer

from backend.app import create_app
from clean_product.artifacts import sha256
from clean_product.models import ModelRunner
from clean_product.paper import PaperStore
from clean_product.service import ProductService


@pytest.fixture
def paper(tmp_path, monkeypatch):
    frozen = tmp_path / 'model.pkl'; frozen.write_bytes(b'fixture-model')
    cfg = {'artifact_root': str(tmp_path / 'artifacts'), 'data_root': str(tmp_path / 'data'),
           'product': {'default_model': 'model_a'}, 'strategy': 'top50_exit_one_worst_sell', 'execution': 'next_open',
           'paper': {'enabled': True, 'store': str(tmp_path / 'paper.sqlite'), 'lot_size': 10},
           'simulation': {'initial_cash': 1000, 'max_positions': 1, 'buy_cost_rate': 0, 'min_cost': 20},
           'models': {'model_a': {'canonical_id': 'fixture', 'role': 'baseline', 'production_allowed': True, 'stages': ['model_a_frozen']}},
           'model_stages': {'model_a_frozen': {'model_path': str(frozen), 'model_sha256': sha256(frozen)}}}
    runner = ModelRunner(cfg)
    runner.stages.register('model_a_frozen', lambda *args, **kwargs: pd.DataFrame([
        {'date': '2026-09-23', 'instrument': 'TW2330', 'rank': 1, 'score': .5}]))
    assert runner.run('model_a', '2026-09-23').status == 'READY'
    service = ProductService(cfg)
    monkeypatch.setattr(service, 'trading_days', lambda: ['2026-09-23', '2026-09-24'])
    monkeypatch.setattr(service.catalog, 'query_local_source', lambda *args: pd.DataFrame([
        {'date': '2026-09-24', 'stock_id': '2330', 'open': 10., 'close': 9.}]))
    store = PaperStore(cfg['paper']['store'])
    state = store.create('alice', name='测试模拟账户', initial_cash=1000, key='create_account_1')
    return store, state, service


def test_persisted_account_is_owner_bound_and_create_is_idempotent(paper):
    store, state, _ = paper
    assert PaperStore(store.filename).state('alice', state['paper_account_id']) == state
    assert store.accounts('bob') == []
    with pytest.raises(ValueError, match='NOT_FOUND'): store.state('bob', state['paper_account_id'])
    repeated = store.create('alice', name='测试模拟账户', initial_cash=1000, key='create_account_1')
    assert repeated['paper_account_id'] == state['paper_account_id'] and repeated['already_applied']


def test_preview_apply_reset_preserve_epoch_and_ledger(paper):
    store, state, service = paper; account = state['paper_account_id']
    preview = store.preview('alice', account, '2026-09-23', service)
    assert store.state('alice', account) == state
    assert preview['actions'][0]['quantity'] == 90
    assert preview['execute_date'] == '2026-09-24'
    args = dict(decision_id=preview['decision_id'], input_checksum=preview['input_checksum'], epoch=1, key='apply_decision_1', confirm=True)
    result = store.apply('alice', **args)
    assert result['state']['cash'] == '80.00' and result['state']['nav'] == '890.00'
    assert store.apply('alice', **args)['already_applied'] is True
    assert len(store.history('alice', account)) == 2
    with pytest.raises(ValueError, match='STALE'): store.apply('alice', **{**args, 'key': 'apply_other_key'})
    reset = store.reset('alice', account, epoch=1, key='reset_account_1', confirm=True)
    assert reset['state']['epoch'] == 2 and reset['state']['cash'] == '1000.00'
    assert reset['archived_state'] == result['state']
    assert store.reset('alice', account, epoch=1, key='reset_account_1', confirm=True)['already_applied']
    with pytest.raises(ValueError, match='STALE'): store.apply('alice', **{**args, 'key': 'apply_after_reset'})


@pytest.mark.parametrize('fault', ['owner', 'checksum', 'confirm', 'source', 'rows'])
def test_rejected_apply_never_changes_account(paper, fault):
    store, state, service = paper
    preview = store.preview('alice', state['paper_account_id'], '2026-09-23', service)
    args = dict(decision_id=preview['decision_id'], input_checksum=preview['input_checksum'], epoch=1, key='apply_decision_1', confirm=True)
    if fault == 'checksum': args['input_checksum'] = 'bad'
    if fault == 'confirm': args['confirm'] = False
    if fault in ('source', 'rows'):
        from pathlib import Path
        Path(preview['source_signal' if fault == 'source' else 'source_rows']).write_text('changed')
    with pytest.raises(ValueError): store.apply('bob' if fault == 'owner' else 'alice', **args)
    assert store.state('alice', state['paper_account_id']) == state


def test_shadow_model_cannot_preview_paper_changes(paper):
    store, state, service = paper
    service.config['models']['model_a']['role'] = 'shadow'
    with pytest.raises(ValueError, match='NOT_ADMITTED'): store.preview('alice', state['paper_account_id'], '2026-09-23', service)


def test_api_requires_signed_identity_and_is_disabled_by_default(paper, monkeypatch):
    store, state, service = paper
    secret = 'fixture-only-auth-secret-32-characters'
    app = create_app({'PRODUCT_CONFIG': service.config, 'PAPER_AUTH_SECRET': secret})
    client = app.test_client(); uri = '/api/tw-stock/paper-portfolio/state?paper_account_id=' + state['paper_account_id']
    assert client.get(uri).status_code == 401
    assert client.get(uri, headers={'Authorization': 'Bearer alice'}).status_code == 401
    sign = URLSafeTimedSerializer(secret, salt='tw-clean-paper-v1')
    headers = {'Authorization': 'Bearer ' + sign.dumps({'owner': 'alice'})}
    assert client.get(uri, headers=headers).json['cash'] == '1000.00'
    wrong = {'Authorization': 'Bearer ' + sign.dumps({'owner': 'bob'})}
    assert client.get(uri, headers=wrong).status_code == 409
    assert client.post('/api/tw-stock/paper-portfolio/apply-decision', headers=headers,
                       json={'owner': 'alice', 'actions': []}).status_code == 409
    app.config['PRODUCT_CONFIG'] = {**service.config, 'paper': {'enabled': False}}
    assert client.get(uri, headers=headers).status_code == 503


def test_import_roundtrip_and_failure_is_atomic(paper, tmp_path):
    from clean_product.paper import checksum
    store, state, service = paper
    snapshot = store.export_snapshot('alice')
    target = PaperStore(tmp_path / 'import.sqlite')
    assert target.import_snapshot('alice', snapshot, checksum(snapshot))['accounts'] == 1
    assert target.state('alice', state['paper_account_id'])['cash'] == state['cash']
    assert target.accounts('bob') == []
    assert target.preview('alice', state['paper_account_id'], '2026-09-23', service)['status'] == 'PREVIEW'
    with pytest.raises(ValueError, match='ALREADY_EXISTS'):
        target.import_snapshot('alice', snapshot, checksum(snapshot))
    with pytest.raises(ValueError, match='IDENTITY_OR_CHECKSUM'):
        PaperStore(tmp_path / 'wrong.sqlite').import_snapshot('bob', snapshot, checksum(snapshot))
    broken = copy.deepcopy(snapshot)
    broken['accounts'].append({**state, 'paper_account_id': 'invalid', 'asof': '2026-02-30'})
    target = PaperStore(tmp_path / 'atomic.sqlite')
    with pytest.raises(ValueError, match='DATE_INVALID'):
        target.import_snapshot('alice', broken, checksum(broken))
    assert target.accounts('alice') == []


@pytest.mark.parametrize('change', [{'positions': {'TW2330': None}}, {'cash': 'NaN'}, {'asof': 123}, {'name': ''}])
def test_import_rejects_invalid_state(paper, tmp_path, change):
    from clean_product.paper import checksum
    store, state, _ = paper
    snapshot = store.export_snapshot('alice'); snapshot['accounts'][0].update(change)
    target = PaperStore(tmp_path / 'invalid.sqlite')
    with pytest.raises(ValueError): target.import_snapshot('alice', snapshot, checksum(snapshot))
    assert target.accounts('alice') == []


def test_concurrent_confirmation_applies_once(paper):
    from concurrent.futures import ThreadPoolExecutor
    store, state, service = paper
    preview = store.preview('alice', state['paper_account_id'], '2026-09-23', service)
    args = dict(decision_id=preview['decision_id'], input_checksum=preview['input_checksum'], epoch=1,
                key='concurrent_apply', confirm=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: store.apply('alice', **args), range(2)))
    assert sum(result.get('already_applied', False) for result in results) == 1
    assert store.state('alice', state['paper_account_id'])['revision'] == 1
    assert len(store.history('alice', state['paper_account_id'])) == 2


def test_sell_uses_separate_commission_and_tax(paper, monkeypatch):
    store, state, service = paper
    account = state['paper_account_id']
    with store.connection(write=True) as db:
        state['positions'] = {'TW2317': {'quantity': 1000, 'cost_basis': '10000.00'}}
        store._save(db, 'alice', state)
    monkeypatch.setattr(service.catalog, 'query_local_source', lambda *a: pd.DataFrame([
        {'stock_id': '2317', 'open': 10., 'close': 10.}, {'stock_id': '2330', 'open': 10., 'close': 10.}]))
    service.config['simulation'].update(buy_cost_rate=0, sell_cost_rate=.013, min_cost=0)
    preview = store.preview('alice', account, '2026-09-23', service)
    sale = next(action for action in preview['actions'] if action['action'] == 'sell')
    assert sale['commission'] == '100.00' and sale['tax'] == '30.00'


@pytest.mark.parametrize('payload', [
    {'paper_account_id': [], 'date': '2026-09-23'},
    {'paper_account_id': 'fixture', 'date': {}},
    {'paper_account_id': 'fixture', 'date': '/private/path'},
])
def test_route_rejects_malformed_input_without_internal_error(paper, payload):
    store, state, service = paper
    secret = 'fixture-only-auth-secret-32-characters'
    app = create_app({'PRODUCT_CONFIG': service.config, 'PAPER_AUTH_SECRET': secret})
    token = URLSafeTimedSerializer(secret, salt='tw-clean-paper-v1').dumps({'owner': 'alice'})
    result = app.test_client().post('/api/tw-stock/paper-portfolio/preview', json=payload,
                                  headers={'Authorization': 'Bearer ' + token})
    assert result.status_code == 409
    assert '/private/path' not in result.get_data(as_text=True)
    assert store.state('alice', state['paper_account_id']) == state


def test_signed_api_create_preview_apply_history_reset_roundtrip(paper, monkeypatch):
    _, _, service = paper
    secret = 'fixture-only-auth-secret-32-characters'
    monkeypatch.setattr('backend.app.routes.paper.ProductService', lambda *a: service)
    client = create_app({'PRODUCT_CONFIG': service.config, 'PAPER_AUTH_SECRET': secret}).test_client()
    token = URLSafeTimedSerializer(secret, salt='tw-clean-paper-v1').dumps({'owner': 'alice'})
    headers = {'Authorization': 'Bearer ' + token}
    def post(endpoint, payload):
        response = client.post('/api/tw-stock/' + endpoint, json=payload, headers=headers)
        assert response.status_code == 200, response.json
        return response.json
    account = post('sim/accounts', {'name': 'API fixture', 'initial_cash': 1000, 'key': 'api_create_account'})
    assert account['nav'] == '1000.00'
    preview = post('paper-portfolio/preview', {'paper_account_id': account['paper_account_id'], 'date': '2026-09-23'})
    applied = post('paper-portfolio/apply-decision', {'decision_id': preview['decision_id'],
                   'input_checksum': preview['input_checksum'], 'epoch': 1, 'key': 'api_apply_decision', 'confirm': True})
    assert applied['state']['nav'] == '890.00'
    history = client.get('/api/tw-stock/paper-portfolio/apply-runs',
                        query_string={'paper_account_id': account['paper_account_id']}, headers=headers)
    assert history.status_code == 200 and len(history.json['runs']) == 2
    reset = post('paper-portfolio/reset', {'paper_account_id': account['paper_account_id'],
                                         'epoch': 1, 'key': 'api_reset_account', 'confirm': True})
    assert reset['state']['epoch'] == 2 and reset['state']['nav'] == '1000.00'
