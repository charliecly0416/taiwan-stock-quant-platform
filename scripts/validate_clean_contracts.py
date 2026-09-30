"""Clean-scope admission checks and compatibility entrypoint implementation."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from clean_product.config import load_config
from clean_product.validation import validate_baseline, validate_registries, verify_file


def main(default='modules'):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', choices=['arch1', 'm3', 'modules', 'stack'], default=default)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--out-dir'); parser.add_argument('--audit-script', default='clean_product/orchestrator.py')
    args = parser.parse_args(); errors = []; evidence = []
    try:
        cfg = load_config(); validate_baseline(cfg); validate_registries(cfg)
        stage = cfg['model_stages']['model_a_frozen']; verify_file(stage['model_path'], stage['model_sha256'])
    except Exception as exc: errors.append(str(exc))
    suites = {'m3': ['tests/test_clean_daily_isolation.py', 'tests/test_clean_release.py',
                     'tests/test_clean_provider_refresh.py', 'tests/test_clean_maintenance.py',
                     'tests/test_clean_shadow_features.py', 'tests/test_clean_shadow_lane.py'],
              'modules': ['tests/test_clean_signal_integrity.py', 'tests/test_clean_agent_completion.py',
                          'tests/test_clean_paper.py', 'tests/test_clean_contracts.py',
                          'tests/test_clean_release.py', 'tests/test_clean_maintenance.py']}
    if args.check == 'm3' and Path(args.audit_script) != Path('clean_product/orchestrator.py'):
        errors.append('clean M3 audits clean_product/orchestrator.py only; archived orchestrators are not executed')
    if args.check in suites:
        command = [sys.executable, '-m', 'pytest', '-q', *suites[args.check]]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        evidence.append({'command': command, 'exit_code': run.returncode, 'output': run.stdout + run.stderr})
        if run.returncode: errors.append('FOCUSED_CONTRACT_REGRESSION_FAILED')
    if args.check == 'stack':
        run = subprocess.run([sys.executable, str(ROOT/'scripts/verify_clean_product.py')], cwd=ROOT, capture_output=True, text=True)
        evidence.append({'command': 'verify_clean_product.py', 'exit_code': run.returncode, 'output': run.stdout + run.stderr})
        if run.returncode: errors.append('LIVE_ARTIFACT_OR_RESEARCH_STACK_BLOCKED')
    report = {'status': 'PASS' if not errors else 'BLOCKED', 'scope': 'clean_contract_v1',
              'check': args.check, 'errors': errors, 'evidence': evidence,
              'legacy_implementation_executed': False, 'readonly': True, 'latest_pointer_written': False}
    if args.out_dir:
        out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=False)
        (out/'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if not errors else 1


if __name__ == '__main__': raise SystemExit(main())
