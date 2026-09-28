"""Owner-bound simulation ledger. No broker, account credentials or live orders."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from uuid import uuid4
from itsdangerous import URLSafeTimedSerializer

from .artifacts import sha256, utc_now
from .strategy import top50_exit_one_worst_sell
from .validation import validate_baseline, verify_file


def auth_secret():
    value = os.getenv('TW_CLEAN_PAPER_AUTH_SECRET', '')
    if value:
        return value
    filename = Path.home() / '.local/state/tw-stock-clean/paper.secret'
    return filename.read_text().strip() if filename.is_file() else ''


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def money(value):
    try:
        value = Decimal(str(value))
        if not value.is_finite(): raise ValueError('PAPER_INVALID_AMOUNT')
        return value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValueError('PAPER_INVALID_AMOUNT') from None


def issue_token(secret, owner):
    if len(secret) < 32 or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', owner):
        raise ValueError('PAPER_AUTH_CONFIGURATION_INVALID')
    return URLSafeTimedSerializer(secret, salt='tw-clean-paper-v1').dumps({'owner': owner})


class PaperStore:
    def __init__(self, filename): self.filename = Path(filename)

    @contextmanager
    def connection(self, *, write=False):
        if write:
            self.filename.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.filename, timeout=10)
        else:
            if not self.filename.is_file(): raise ValueError('PAPER_ACCOUNT_NOT_FOUND')
            db = sqlite3.connect(self.filename.resolve().as_uri() + '?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        try:
            if write:
                db.executescript('''CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, owner TEXT NOT NULL, state TEXT NOT NULL);
                  CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY, owner TEXT NOT NULL, account TEXT NOT NULL, payload TEXT NOT NULL);
                  CREATE TABLE IF NOT EXISTS events(owner TEXT NOT NULL, key TEXT NOT NULL, account TEXT NOT NULL,
                    operation TEXT NOT NULL, request_hash TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL,
                    PRIMARY KEY(owner,key));''')
                db.execute('BEGIN IMMEDIATE')
            yield db
            if write: db.commit()
        except Exception:
            if write: db.rollback()
            raise
        finally: db.close()

    @staticmethod
    def _state(db, owner, account):
        row = db.execute('SELECT state FROM accounts WHERE id=? AND owner=?', (account, owner)).fetchone()
        if row is None: raise ValueError('PAPER_ACCOUNT_NOT_FOUND')
        return json.loads(row['state'])

    @staticmethod
    def _save(db, owner, state):
        db.execute('UPDATE accounts SET state=? WHERE id=? AND owner=?',
                   (json.dumps(state, allow_nan=False), state['paper_account_id'], owner))

    @staticmethod
    def _existing(db, owner, key, operation, payload):
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}', key):
            raise ValueError('PAPER_IDEMPOTENCY_KEY_REQUIRED')
        row = db.execute('SELECT * FROM events WHERE owner=? AND key=?', (owner, key)).fetchone()
        if row:
            if row['operation'] != operation or row['request_hash'] != checksum(payload):
                raise ValueError('PAPER_IDEMPOTENCY_CONFLICT')
            return {**json.loads(row['result']), 'already_applied': True}

    @staticmethod
    def _event(db, owner, key, account, operation, payload, result):
        db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)',
                   (owner, key, account, operation, checksum(payload), json.dumps(result, allow_nan=False), utc_now()))

    def create(self, owner, *, name, initial_cash, key):
        amount = money(initial_cash)
        if not owner or not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or not 0 < amount <= 10**12:
            raise ValueError('PAPER_INVALID_ACCOUNT')
        request = {'name': name.strip(), 'initial_cash': str(amount)}
        with self.connection(write=True) as db:
            old = self._existing(db, owner, key, 'create', request)
            if old: return old
            account = uuid4().hex
            state = {'paper_account_id': account, 'name': name.strip(), 'initial_cash': str(amount),
                     'cash': str(amount), 'nav': str(amount), 'market_value': '0.00', 'mark_asof': None,
                     'positions': {}, 'epoch': 1, 'revision': 0, 'asof': None,
                     'status': 'READY', 'simulation_only': True, 'persisted': True, 'created_at': utc_now()}
            db.execute('INSERT INTO accounts VALUES(?,?,?)', (account, owner, json.dumps(state)))
            self._event(db, owner, key, account, 'create', request, state)
            return state

    def accounts(self, owner):
        if not self.filename.exists(): return []
        with self.connection() as db:
            return [json.loads(row['state']) for row in db.execute('SELECT state FROM accounts WHERE owner=? ORDER BY id', (owner,))]

    def state(self, owner, account):
        with self.connection() as db: return self._state(db, owner, account)

    def history(self, owner, account):
        with self.connection() as db:
            self._state(db, owner, account)
            return [{'operation': row['operation'], 'created_at': row['created_at'], 'result': json.loads(row['result'])}
                    for row in db.execute('SELECT * FROM events WHERE owner=? AND account=? ORDER BY created_at DESC LIMIT 100', (owner, account))]

    def export_snapshot(self, owner):
        """Owner-scoped state transfer; historical events remain in the source DB."""
        return {'schema_version': 'tw.clean.paper_export.v1', 'owner': owner, 'accounts': self.accounts(owner)}

    def import_snapshot(self, owner, snapshot, expected_sha256):
        """Import an explicitly exported owner snapshot; never inspect a live DB."""
        if (not isinstance(snapshot, dict) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', owner)
                or checksum(snapshot) != expected_sha256 or snapshot.get('schema_version') != 'tw.clean.paper_export.v1' or snapshot.get('owner') != owner):
            raise ValueError('PAPER_IMPORT_IDENTITY_OR_CHECKSUM_INVALID')
        accounts = snapshot.get('accounts')
        if not isinstance(accounts, list) or not accounts: raise ValueError('PAPER_IMPORT_EMPTY')
        with self.connection(write=True) as db:
            for state in accounts:
                if (not isinstance(state, dict) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', state.get('paper_account_id', ''))
                        or type(state.get('epoch')) is not int or state['epoch'] < 1
                        or type(state.get('revision')) is not int or state['revision'] < 0
                        or not isinstance(state.get('name'), str) or not 1 <= len(state['name'].strip()) <= 80
                        or 'asof' not in state
                        or state.get('simulation_only') is not True or not isinstance(state.get('positions'), dict)
                        or not 0 < money(state.get('initial_cash', 0)) <= 10**12 or money(state.get('cash', -1)) < 0):
                    raise ValueError('PAPER_IMPORT_STATE_INVALID')
                if state['asof'] is not None:
                    try:
                        if date.fromisoformat(state['asof']).isoformat() != state['asof']: raise ValueError()
                    except (ValueError, TypeError):
                        raise ValueError('PAPER_IMPORT_DATE_INVALID') from None
                for symbol, position in state['positions'].items():
                    if (not re.fullmatch(r'TW[0-9]{4,6}', symbol) or not isinstance(position, dict) or type(position.get('quantity')) is not int
                            or position['quantity'] <= 0 or money(position.get('cost_basis', -1)) < 0):
                        raise ValueError('PAPER_IMPORT_POSITION_INVALID')
                if db.execute('SELECT 1 FROM accounts WHERE id=?', (state['paper_account_id'],)).fetchone():
                    raise ValueError('PAPER_IMPORT_ACCOUNT_ALREADY_EXISTS')
                imported = {**state, 'persisted': True, 'status': 'READY', 'import_source_sha256': expected_sha256}
                db.execute('INSERT INTO accounts VALUES(?,?,?)', (state['paper_account_id'], owner, json.dumps(imported, allow_nan=False)))
                key = 'import_' + state['paper_account_id']
                self._event(db, owner, key, state['paper_account_id'], 'import', {'snapshot_sha256': expected_sha256}, imported)
        return {'status': 'IMPORTED', 'accounts': len(accounts), 'source_sha256': expected_sha256, 'simulation_only': True}

    def preview(self, owner, account, asof, service):
        try:
            if date.fromisoformat(asof).isoformat() != asof: raise ValueError()
        except (ValueError, TypeError):
            raise ValueError('PAPER_DATE_INVALID') from None
        config = service.config
        validate_baseline(config)
        model = config.get('product', {}).get('default_model', 'model_a')
        spec = config['models'][model]
        if spec.get('role') != 'baseline' or spec.get('production_allowed') is not True or spec.get('stages') != ['model_a_frozen']:
            raise ValueError('MODEL_NOT_ADMITTED_FOR_PAPER_ACCOUNT')
        stage = config['model_stages']['model_a_frozen']
        verify_file(stage['model_path'], stage['model_sha256'])
        signal = service._stored_signal(model, asof)
        if signal is None or signal.status != 'READY' or signal.artifact_dir is None:
            raise ValueError('PAPER_VALIDATED_SIGNAL_REQUIRED')
        days = service.trading_days()
        if asof not in days or days.index(asof) + 1 == len(days):
            raise ValueError('PAPER_NEXT_OPEN_UNAVAILABLE')
        execute = days[days.index(asof) + 1]
        prices = service.catalog.query_local_source('prices', execute, execute)
        prices = prices.assign(instrument='TW' + prices.stock_id.astype(str).str.replace(r'^TW', '', regex=True).str.zfill(4)).set_index('instrument')
        if prices.index.duplicated().any(): raise ValueError('PAPER_DUPLICATE_PRICE')
        with self.connection(write=True) as db:
            state = self._state(db, owner, account)
            if state['asof'] and asof <= state['asof']: raise ValueError('PAPER_DATE_ALREADY_APPLIED')
            positions = json.loads(json.dumps(state['positions'])); cash = money(state['cash'])
            settings = config.get('simulation', {}); lot = config.get('paper', {}).get('lot_size', 10)
            if type(lot) is not int or not 1 <= lot <= 1000: raise ValueError('PAPER_LOT_SIZE_INVALID')
            intents = top50_exit_one_worst_sell(signal.rows, set(positions),
                         max_positions=int(settings.get('max_positions', 50)), full_ranks=signal.full_ranks)
            actions = []; buys = list(intents[intents.action.eq('buy')].instrument)
            minimum = money(settings.get('min_cost', 20))
            try:
                rate = Decimal(str(settings.get('buy_cost_rate', .001425)))
                sell_rate = Decimal(str(settings.get('sell_cost_rate', .004425))) - Decimal('.003')
            except InvalidOperation:
                raise ValueError('PAPER_FEE_CONFIGURATION_INVALID') from None
            if minimum < 0 or any(not value.is_finite() or not 0 <= value < 1 for value in (rate, sell_rate)):
                raise ValueError('PAPER_FEE_CONFIGURATION_INVALID')
            for item in intents.itertuples():
                if item.instrument not in prices.index: raise ValueError('PAPER_NEXT_OPEN_UNAVAILABLE')
                price = Decimal(str(prices.loc[item.instrument, 'open']))
                if not price.is_finite() or price <= 0: raise ValueError('PAPER_NEXT_OPEN_UNAVAILABLE')
                if item.action == 'sell':
                    quantity = positions.pop(item.instrument)['quantity']; gross = money(price * quantity)
                    commission = max(minimum, money(gross * sell_rate)); tax = money(gross * Decimal('.003'))
                    cash += gross - commission - tax
                else:
                    budget = cash / (len(buys) - buys.index(item.instrument))
                    quantity = int(min(budget / (price * (1 + rate)), (budget - minimum) / price) / lot) * lot
                    if quantity <= 0: continue
                    gross = money(price * quantity); commission = max(minimum, money(gross * rate)); tax = money(0)
                    if gross + commission > cash: continue
                    cash -= gross + commission
                    positions[item.instrument] = {'quantity': quantity, 'cost_basis': str(gross + commission)}
                if cash < 0: raise ValueError('PAPER_NEGATIVE_CASH')
                actions.append({'instrument': item.instrument, 'action': item.action, 'quantity': quantity,
                                'price': str(price), 'commission': str(commission), 'tax': str(tax)})
            market_value = money(0)
            for instrument, position in positions.items():
                if instrument not in prices.index: raise ValueError('PAPER_MARK_PRICE_UNAVAILABLE')
                close = Decimal(str(prices.loc[instrument, 'close']))
                if not close.is_finite() or close <= 0: raise ValueError('PAPER_MARK_PRICE_UNAVAILABLE')
                position['mark_price'] = str(close); market_value += money(close * position['quantity'])
            after = {**state, 'cash': str(money(cash)), 'positions': positions, 'asof': asof,
                     'mark_asof': execute, 'market_value': str(market_value), 'nav': str(money(cash + market_value)),
                     'revision': state['revision'] + 1}
            payload = {'artifact_type': 'PaperOrderIntentArtifact', 'decision_id': uuid4().hex,
                       'paper_account_id': account, 'epoch': state['epoch'], 'revision': state['revision'],
                       'before_checksum': checksum(state), 'asof': asof, 'execute_date': execute,
                       'source_signal': str(signal.artifact_dir / 'manifest.json'),
                       'source_signal_sha256': sha256(signal.artifact_dir / 'manifest.json'),
                       'source_rows': str(signal.artifact_dir / 'signals.csv'),
                       'source_rows_sha256': sha256(signal.artifact_dir / 'signals.csv'),
                       'model': model, 'actions': actions, 'after': after, 'simulation_only': True}
            payload['input_checksum'] = checksum(payload)
            db.execute('INSERT INTO decisions VALUES(?,?,?,?)', (payload['decision_id'], owner, account, json.dumps(payload)))
            return {**payload, 'status': 'PREVIEW', 'confirmation_required': True}

    def apply(self, owner, *, decision_id, input_checksum, epoch, key, confirm):
        if confirm is not True: raise ValueError('PAPER_CONFIRMATION_REQUIRED')
        request = {'decision_id': decision_id, 'input_checksum': input_checksum, 'epoch': epoch}
        with self.connection(write=True) as db:
            old = self._existing(db, owner, key, 'apply', request)
            if old: return old
            row = db.execute('SELECT * FROM decisions WHERE id=? AND owner=?', (decision_id, owner)).fetchone()
            if row is None: raise ValueError('PAPER_DECISION_NOT_FOUND')
            intent = json.loads(row['payload']); stored_hash = intent.pop('input_checksum')
            if input_checksum != stored_hash or stored_hash != checksum(intent): raise ValueError('PAPER_DECISION_CHECKSUM_MISMATCH')
            state = self._state(db, owner, row['account'])
            if type(epoch) is not int or epoch != state['epoch'] or intent['epoch'] != epoch or intent['before_checksum'] != checksum(state):
                raise ValueError('PAPER_STALE_DECISION')
            if sha256(Path(intent['source_signal'])) != intent['source_signal_sha256']:
                raise ValueError('PAPER_SOURCE_CHANGED')
            if sha256(Path(intent['source_rows'])) != intent['source_rows_sha256']:
                raise ValueError('PAPER_SOURCE_CHANGED')
            self._save(db, owner, intent['after'])
            result = {'status': 'APPLIED', 'decision_id': decision_id, 'state': intent['after'],
                      'actions': intent['actions'], 'simulation_only': True}
            self._event(db, owner, key, row['account'], 'apply', request, result)
            return result

    def reset(self, owner, account, *, epoch, key, confirm):
        if confirm is not True: raise ValueError('PAPER_CONFIRMATION_REQUIRED')
        request = {'account': account, 'epoch': epoch}
        with self.connection(write=True) as db:
            old = self._existing(db, owner, key, 'reset', request)
            if old: return old
            before = self._state(db, owner, account)
            if type(epoch) is not int or before['epoch'] != epoch: raise ValueError('PAPER_STALE_EPOCH')
            after = {**before, 'cash': before['initial_cash'], 'positions': {}, 'epoch': epoch + 1,
                     'revision': 0, 'asof': None, 'mark_asof': None, 'market_value': '0.00', 'nav': before['initial_cash']}
            self._save(db, owner, after)
            result = {'status': 'RESET', 'state': after, 'archived_state': before, 'simulation_only': True}
            self._event(db, owner, key, account, 'reset', request, result)
            return result
