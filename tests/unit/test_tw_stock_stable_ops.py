from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path
from urllib.error import HTTPError

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_backup_module():
    path = ROOT / "scripts/tw_stock_ops_backup.py"
    spec = importlib.util.spec_from_file_location("tw_stock_ops_backup_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_deployment_verifier_module():
    path = ROOT / "scripts/verify_tw_stock_readonly_deployment.py"
    spec = importlib.util.spec_from_file_location("tw_stock_deployment_verifier_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def use_fixture_inputs(module, *paths: str) -> None:
    module.BACKUP_INPUTS = tuple(paths)


def test_artifact_backup_and_restore_drill_are_isolated(tmp_path):
    module = load_backup_module()
    use_fixture_inputs(
        module,
        "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
        "configs/active_baseline_descriptor.yaml",
    )
    repo = tmp_path / "repo"
    source = repo / "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"asof":"2026-09-18"}\n', encoding="utf-8")
    config = repo / "configs/active_baseline_descriptor.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("active: model_a\n", encoding="utf-8")
    before = source.read_bytes()
    plan = module.backup_plan(repo)
    assert plan["writes_performed"] is False
    assert plan["required_inputs_complete"] is True
    backup = module.create_backup(repo, tmp_path / "backups", skip_database=True)
    result = module.drill(backup)
    assert result["ok"] is True
    assert result["artifact_files_verified"] == 2
    assert result["database_archive_verified"] is True
    assert result["live_database_writes"] is False
    assert result["live_artifact_writes"] is False
    assert source.read_bytes() == before


def test_restore_drill_rejects_archive_tampering(tmp_path):
    module = load_backup_module()
    use_fixture_inputs(module, "data_tw/artifacts/latest.json")
    repo = tmp_path / "repo"
    source = repo / "data_tw/artifacts/latest.json"
    source.parent.mkdir(parents=True)
    source.write_text("{}\n", encoding="utf-8")
    backup = module.create_backup(repo, tmp_path / "backups", skip_database=True)
    with (backup / "artifacts.tar.gz").open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        module.drill(backup)


def test_postgres_credentials_stay_in_child_environment(monkeypatch):
    module = load_backup_module()
    monkeypatch.setenv("DATABASE_URL", "postgresql://ops-user:secret-pass@db.internal:5544/quant")
    env = module.postgres_env(os.environ["DATABASE_URL"])
    assert "DATABASE_URL" not in env
    assert env["PGHOST"] == "db.internal"
    assert env["PGPORT"] == "5544"
    assert env["PGDATABASE"] == "quant"
    assert env["PGUSER"] == "ops-user"
    assert env["PGPASSWORD"] == "secret-pass"


def _fake_command(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)


def test_database_backup_and_archive_drill_use_pg_tools_without_url_argument(tmp_path, monkeypatch):
    module = load_backup_module()
    use_fixture_inputs(module, "configs/tw_product_artifact_registry.yaml")
    repo = tmp_path / "repo"
    source = repo / "configs/tw_product_artifact_registry.yaml"
    source.parent.mkdir(parents=True)
    source.write_text("schema_version: fixture\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    args_log = tmp_path / "pg_dump.args"
    env_log = tmp_path / "pg_dump.env"
    _fake_command(
        fake_bin / "pg_dump",
        f'echo "$@" > "{args_log}"\necho "$PGHOST:$PGPORT:$PGDATABASE:$PGUSER:$PGPASSWORD" > "{env_log}"\n'
        'output=""\nwhile [ "$#" -gt 0 ]; do if [ "$1" = "--file" ]; then shift; output=$1; fi; shift; done\n'
        'printf "fixture custom dump" > "$output"\n',
    )
    _fake_command(fake_bin / "pg_restore", "exit 0\n")
    monkeypatch.setenv("PATH", f"{fake_bin}:/usr/bin:/bin")
    monkeypatch.setenv("DATABASE_URL", "postgresql://ops-user:secret-pass@db.internal:5544/quant")
    backup = module.create_backup(repo, tmp_path / "backups", skip_database=False)
    assert module.drill(backup)["database_archive_verified"] is True
    assert "postgresql://" not in args_log.read_text(encoding="utf-8")
    assert "secret-pass" not in args_log.read_text(encoding="utf-8")
    assert env_log.read_text(encoding="utf-8").strip() == "db.internal:5544:quant:ops-user:secret-pass"
    manifest = (backup / "manifest.json").read_text(encoding="utf-8")
    assert "secret-pass" not in manifest


def test_backup_rejects_missing_required_input(tmp_path):
    module = load_backup_module()
    use_fixture_inputs(module, "configs/required.yaml", "data_tw/artifacts")
    repo = tmp_path / "repo"
    required = repo / "configs/required.yaml"
    required.parent.mkdir(parents=True)
    required.write_text("ok: true\n", encoding="utf-8")
    plan = module.backup_plan(repo)
    assert plan["required_inputs_complete"] is False
    assert plan["required_inputs"][1]["state"] == "missing"
    with pytest.raises(RuntimeError, match="required backup inputs"):
        module.create_backup(repo, tmp_path / "backups", skip_database=True)


def test_backup_rejects_plaintext_database_credentials_in_artifacts(tmp_path):
    module = load_backup_module()
    use_fixture_inputs(module, "data_tw/ops/daily_auto_update/installed.cron")
    repo = tmp_path / "repo"
    cron = repo / "data_tw/ops/daily_auto_update/installed.cron"
    cron.parent.mkdir(parents=True)
    cron.write_text(
        "DATABASE_URL=postgresql://user:plaintext-password@db.internal:5432/quant\n",
        encoding="utf-8",
    )

    plan = module.backup_plan(repo)
    assert plan["required_inputs_complete"] is False
    assert plan["plaintext_credential_findings"] == [
        {"path": "data_tw/ops/daily_auto_update/installed.cron", "code": "authenticated_postgresql_url"}
    ]
    with pytest.raises(RuntimeError, match="plaintext credentials"):
        module.create_backup(repo, tmp_path / "backups", skip_database=True)


def test_daily_cron_wrapper_requires_private_environment_file() -> None:
    wrapper = ROOT / "scripts/run_daily_env.sh"
    source = wrapper.read_text(encoding="utf-8")
    assert 'source "$ENV_FILE"' in source
    assert 'find "$ENV_FILE" -maxdepth 0 -perm /077' in source
    assert "postgresql://" not in source


def test_deployment_verifier_accepts_html_method_not_allowed(monkeypatch):
    module = load_deployment_verifier_module()

    def reject_with_flask_default_html(request, timeout):
        raise HTTPError(
            request.full_url,
            405,
            "METHOD NOT ALLOWED",
            hdrs=None,
            fp=io.BytesIO(b"<!doctype html><title>405 Method Not Allowed</title>"),
        )

    monkeypatch.setattr(module, "urlopen", reject_with_flask_default_html)
    assert module.request_status(
        "http://127.0.0.1:5000",
        "/api/ready",
        method="POST",
        timeout=1,
    ) == 405


def test_deployment_verifier_preserves_html_error_status(monkeypatch):
    module = load_deployment_verifier_module()

    def reject_with_html(request, timeout):
        raise HTTPError(
            request.full_url,
            404,
            "NOT FOUND",
            hdrs=None,
            fp=io.BytesIO(b"<!doctype html><title>404 Not Found</title>"),
        )

    monkeypatch.setattr(module, "urlopen", reject_with_html)
    assert module.request_json(
        "http://127.0.0.1:5000",
        "/api/ready",
        timeout=1,
    ) == (404, {})


def test_watchdog_uses_http_probes_and_portable_python(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    curl_log = tmp_path / "curl.log"
    _fake_command(fake_bin / "curl", f'echo "$@" >> "{curl_log}"\ncase "$*" in *api/health*) echo \'{{"status":"healthy"}}\';; esac\nexit 0\n')
    _fake_command(fake_bin / "python3", "exit 99\n")
    env = os.environ.copy()
    env.update({
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "TW_STOCK_PLATFORM_ROOT": str(tmp_path / "deployment"),
        "TW_STOCK_HEALTH_TIMEOUT": "1",
    })
    env.pop("TW_STOCK_PYTHON", None)
    completed = subprocess.run(["bash", str(ROOT / "scripts/ensure_tw_stock_services.sh")], env=env, capture_output=True, text=True, timeout=10)
    assert completed.returncode == 0
    probes = curl_log.read_text(encoding="utf-8")
    assert "/api/health" in probes
    assert "/api/ready" in probes
    assert ":8000/api/health" in probes
    assert ":4040/api/tunnels" not in probes
    watchdog_log = tmp_path / "deployment/logs/service_watchdog.log"
    assert not watchdog_log.exists() or "started" not in watchdog_log.read_text(encoding="utf-8")


def test_watchdog_returns_failure_when_live_backend_is_not_ready(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _fake_command(
        fake_bin / "curl",
        "case \"$*\" in *api/ready*) exit 22;; *api/health*) echo '{\"status\":\"healthy\"}'; exit 0;; *) exit 0;; esac\n",
    )
    _fake_command(fake_bin / "python3", "exit 99\n")
    deployment = tmp_path / "deployment"
    env = os.environ.copy()
    env.update({
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "TW_STOCK_PLATFORM_ROOT": str(deployment),
        "TW_STOCK_HEALTH_TIMEOUT": "1",
    })
    completed = subprocess.run(
        ["bash", str(ROOT / "scripts/ensure_tw_stock_services.sh")],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 1
    log = (deployment / "logs/service_watchdog.log").read_text(encoding="utf-8")
    assert "liveness passed but readiness is degraded" in log


def test_watchdog_fails_when_backend_is_live_but_not_ready(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _fake_command(
        fake_bin / "curl",
        'case "$*" in *api/ready*) exit 22;; *api/health*) echo \'{"status":"healthy"}\'; exit 0;; *) exit 0;; esac\n',
    )
    _fake_command(fake_bin / "python3", "exit 99\n")
    env = os.environ.copy()
    env.update({
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "TW_STOCK_PLATFORM_ROOT": str(tmp_path / "deployment"),
        "TW_STOCK_HEALTH_TIMEOUT": "1",
    })
    completed = subprocess.run(
        ["bash", str(ROOT / "scripts/ensure_tw_stock_services.sh")],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 1
    log = (tmp_path / "deployment/logs/service_watchdog.log").read_text(encoding="utf-8")
    assert "backend liveness passed but readiness is degraded" in log


def test_watchdog_refuses_duplicate_backend_on_unhealthy_listener(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _fake_command(fake_bin / "curl", 'case "$*" in *5000*) exit 22;; *) exit 0;; esac\n')
    _fake_command(fake_bin / "ss", 'echo "LISTEN 0 128 0.0.0.0:5000 0.0.0.0:*"\n')
    _fake_command(fake_bin / "python3", "exit 99\n")
    env = os.environ.copy()
    env.update({
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "TW_STOCK_PLATFORM_ROOT": str(tmp_path / "deployment"),
        "TW_STOCK_HEALTH_TIMEOUT": "1",
    })
    completed = subprocess.run(["bash", str(ROOT / "scripts/ensure_tw_stock_services.sh")], env=env, capture_output=True, text=True, timeout=10)
    assert completed.returncode == 1
    log = (tmp_path / "deployment/logs/service_watchdog.log").read_text(encoding="utf-8")
    assert "listener failed HTTP liveness; refusing duplicate start" in log
    assert "started backend" not in log


def test_watchdog_uses_one_port_configuration_for_urls(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    curl_log = tmp_path / "curl.log"
    _fake_command(fake_bin / "curl", f'echo "$@" >> "{curl_log}"\ncase "$*" in *api/health*) echo \'{{"status":"healthy"}}\';; esac\nexit 0\n')
    _fake_command(fake_bin / "python3", "exit 99\n")
    env = os.environ.copy()
    env.update({
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "TW_STOCK_PLATFORM_ROOT": str(tmp_path / "deployment"),
        "TW_STOCK_BACKEND_PORT": "5511",
        "TW_STOCK_FRONTEND_PORT": "8811",
        "TW_STOCK_BACKEND_URL": "http://untrusted.invalid:1",
        "TW_STOCK_FRONTEND_URL": "http://untrusted.invalid:2",
        "TW_STOCK_FRONTEND_HEALTH_URL": "http://untrusted.invalid:3/healthy",
        "TW_STOCK_NGROK_STATUS_URL": "http://untrusted.invalid:4/tunnels",
    })
    completed = subprocess.run(["bash", str(ROOT / "scripts/ensure_tw_stock_services.sh")], env=env, capture_output=True, text=True, timeout=10)
    assert completed.returncode == 0
    probes = curl_log.read_text(encoding="utf-8")
    assert "127.0.0.1:5511/api/health" in probes
    assert "127.0.0.1:5511/api/ready" in probes
    assert "127.0.0.1:8811/api/health" in probes
    assert "untrusted.invalid" not in probes


def test_watchdog_cleans_failed_gunicorn_start(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    python_log = tmp_path / "python.log"
    _fake_command(fake_bin / "curl", "exit 22\n")
    _fake_command(fake_bin / "ss", "exit 0\n")
    _fake_command(fake_bin / "python3", f'echo "$@" >> "{python_log}"\nexec /bin/sleep 30\n')
    deployment = tmp_path / "deployment"
    (deployment / "frontend/dist").mkdir(parents=True)
    (deployment / "frontend/dist/index.html").write_text("fixture", encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "TW_STOCK_PLATFORM_ROOT": str(deployment),
        "TW_STOCK_HEALTH_START_ATTEMPTS": "1",
        "TW_STOCK_HEALTH_TIMEOUT": "1",
    })
    completed = subprocess.run(["bash", str(ROOT / "scripts/ensure_tw_stock_services.sh")], env=env, capture_output=True, text=True, timeout=15)
    assert completed.returncode == 1
    assert "-m gunicorn" in python_log.read_text(encoding="utf-8")
    log = (deployment / "logs/service_watchdog.log").read_text(encoding="utf-8")
    assert "backend startup probe failed; cleaned new process group" in log
    assert "frontend startup probe failed; cleaned new process group" in log
    assert "started ngrok" not in log
