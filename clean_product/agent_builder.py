"""Build immutable candidate-only daily context from validated signal files."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

from .agent import DISCLAIMER, load_prompt
from .artifacts import sha256, utc_now, write_json
from .config import path, trading_days
from .validation import read_signal_artifact, validate_baseline, verify_file


def build_prompt(config: dict, asof: str, output_root: Path) -> dict:
    validate_baseline(config)
    model = config.get('product', {}).get('default_model', 'model_a')
    signal_root = path(config['artifact_root']) / 'signals' / model / asof
    signal, rows = read_signal_artifact(signal_root, config, model, asof)
    if signal['status'] != 'READY':
        raise ValueError('AGENT_SOURCE_SIGNAL_BLOCKED')
    stage = config['model_stages']['model_a_frozen']
    verify_file(stage['model_path'], stage['model_sha256'])
    output_root = output_root.resolve()
    directory = output_root / asof
    directory.mkdir(parents=True, exist_ok=False)  # Never replace prior evidence.
    model_id = config['models'][model]['canonical_id']
    target = next((day for day in trading_days(config) if day > asof), None)
    safety = {'readonly_only': True, 'not_order': True, 'not_target_position': True,
              'not_investment_advice': True, 'production_trade_enabled': False}
    compact = [{'instrument': item.instrument, 'candidate_rank': int(item.candidate_rank),
                'qlib_score': float(item.score)} for item in rows.head(50).itertuples()]
    strategy = 'candidate_only_no_strategy_replay'
    execution = 'not_applicable_candidate_only_no_strategy_replay'
    snapshot = directory / 'snapshot'
    write_json(snapshot / 'payload.json', {'asof': asof, 'model_id': model_id,
               'snapshot_candidate_only': True, 'rankings': compact, 'no_apply': True})
    write_json(snapshot / 'manifest.json', {'artifact_type': 'ReadonlyStrategySnapshot',
               'asof': asof, 'model_id': model_id, 'source_signal_manifest': str(signal_root / 'manifest.json'),
               'source_signal_sha256': sha256(signal_root / 'manifest.json'),
               'payload_sha256': sha256(snapshot / 'payload.json'), 'snapshot_candidate_only': True, **safety})
    sources = {'controlled_model_signal_manifest': signal_root / 'manifest.json',
               'controlled_model_signal_csv': signal_root / 'signals.csv',
               'readonly_snapshot_manifest': snapshot / 'manifest.json',
               'readonly_snapshot_payload': snapshot / 'payload.json'}
    lineage = {}
    for key, filename in sources.items():
        lineage[key] = str(filename.resolve()); lineage[key + '_sha256'] = sha256(filename)
    context = {'schema_version': 'tw_agent_daily_prompt_context_v1', 'safety': safety,
               'date_context': {'signal_asof': asof, 'target_date': target, 'execution_price_mode': execution},
               'model_context': {'base_model_id': model_id, 'candidate_boundary': 'qlib_top50'},
               'strategy': {'strategy_rule': strategy, 'snapshot_candidate_only': True},
               'rankings': {'qlib_top50_compact': compact}, 'source_lineage': lineage,
               'answer_policy': {'required_disclaimer': DISCLAIMER},
               'paper_portfolio': {'apply_allowed': False, 'reason': 'candidate_only_no_account_evidence'}}
    write_json(directory / 'prompt_context.json', context)
    (directory / 'prompt_text.md').write_text(
        'Readonly research only. Explain verified candidate ranks. No account or replay evidence is present.\n'
        'Scores are cross-sectional ranks, not returns or probabilities. If evidence is absent, say so.\n'
        'Return JSON with answer, citations and warnings. ' + DISCLAIMER + '\n', encoding='utf-8')
    checksum = 'sha256:' + hashlib.sha256((directory / 'prompt_context.json').read_bytes()
                  + b'\n' + (directory / 'prompt_text.md').read_bytes()).hexdigest()
    manifest = {'artifact_type': 'tw_agent_daily_prompt', 'schema_version': 'tw_agent_daily_prompt_v1',
                'signal_asof': asof, 'target_date': target, 'model_ids': {'base': model_id},
                'strategy_rule': strategy, 'execution_price_mode': execution,
                'source_artifacts': lineage, 'created_at': utc_now(), 'checksum': checksum,
                'validation': {'ok': True}, 'latest_pointer_written': False, **safety}
    write_json(directory / 'manifest.json', manifest)
    checked = deepcopy(config)
    checked.setdefault('agent', {})['prompt_root'] = str(output_root)
    load_prompt(checked, asof)
    return {'status': 'READY', 'asof': asof, 'manifest': str(directory / 'manifest.json'),
            'checksum': checksum, 'candidate_only': True, 'latest_pointer_written': False}
