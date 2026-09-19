import jwt
import pytest

import app as application
from app.config.settings import Config, DEFAULT_SECRET_KEY
from app.utils.auth import generate_token, verify_token


@pytest.mark.parametrize('secret', [None, '', '   ', DEFAULT_SECRET_KEY, 'change-me', 'your-secret-key-change-me'])
def test_unsafe_secret_blocks_factory_before_startup_hooks(monkeypatch, secret):
    if secret is None:
        monkeypatch.delenv('SECRET_KEY', raising=False)
    else:
        monkeypatch.setenv('SECRET_KEY', secret)
    monkeypatch.setattr(application, 'start_pending_order_worker', lambda: pytest.fail('worker started'))
    with pytest.raises(RuntimeError, match='persistent SECRET_KEY'):
        application.create_app()
    with pytest.raises(RuntimeError, match='persistent SECRET_KEY'):
        _ = Config.SECRET_KEY


def test_configured_key_is_stable_and_rejects_public_example_token(monkeypatch):
    secret = 'configured-signing-key-for-research-startup-test'
    monkeypatch.setenv('SECRET_KEY', secret)
    monkeypatch.setattr('app.utils.auth._verify_token_version', lambda *_: True)
    token = generate_token(1, 'researcher')
    assert verify_token(token)['sub'] == 'researcher'
    assert Config.SECRET_KEY == secret
    forged = jwt.encode({'sub': 'admin', 'role': 'admin'}, DEFAULT_SECRET_KEY, algorithm='HS256')
    assert verify_token(forged) is None


def test_research_defaults_do_not_start_trading_services(monkeypatch):
    for name in ('ENABLE_PENDING_ORDER_WORKER', 'ENABLE_PORTFOLIO_MONITOR', 'DISABLE_RESTORE_RUNNING_STRATEGIES', 'POSITION_SYNC_ENABLED'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(application, 'get_pending_order_worker', lambda: pytest.fail('pending worker constructed'))
    monkeypatch.setattr(application, 'get_trading_executor', lambda: pytest.fail('trading executor constructed'))
    application.start_pending_order_worker()
    application.start_portfolio_monitor()
    application.restore_running_strategies()
    application._schedule_post_restore_position_sync()


def test_optional_calibration_and_reflection_are_opt_in(monkeypatch):
    from app.services import ai_calibration, reflection
    for name in ('ENABLE_OFFLINE_AI_CALIBRATION', 'ENABLE_REFLECTION_WORKER'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(ai_calibration, 'AICalibrationService', lambda: pytest.fail('calibration constructed'))
    monkeypatch.setattr(reflection, 'ReflectionService', lambda: pytest.fail('reflection constructed'))
    ai_calibration.start_ai_calibration_worker()
    reflection.start_reflection_worker()
    assert reflection._reflection_thread is None or not reflection._reflection_thread.is_alive()
