"""
健康检查路由
"""
from flask import Blueprint, jsonify
from datetime import datetime, timezone

from app.services.research_readiness import research_readiness, research_runtime_safety
from app.utils.db_postgres import is_postgres_available

health_bp = Blueprint('health', __name__)


@health_bp.route('/', methods=['GET'])
def index():
    """API 首页"""
    return jsonify({
        'name': 'QuantDinger Python API',
        'version': '2.0.0',
        'status': 'running',
        # SafeJSONProvider serializes datetimes as UTC ISO (with Z).
        'timestamp': datetime.now(timezone.utc)
    })


@health_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc)
    })


@health_bp.route('/api/health', methods=['GET'])
def api_health_check():
    """兼容路径：用于容器健康检查/反代探针等场景。"""
    return health_check()


@health_bp.route('/ready', methods=['GET'])
@health_bp.route('/api/ready', methods=['GET'])
def readiness_check():
    """Check the database and the local TW research artifact contract."""
    artifacts = research_readiness()
    database_ready = is_postgres_available()
    runtime_safety = research_runtime_safety()
    ready = database_ready and artifacts["ready"] and runtime_safety["ready"]
    payload = {
        "schema_version": "tw_product_readiness_v1",
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "checked_at": artifacts["checked_at"],
        "signal_asof": artifacts["signal_asof"] if artifacts["ready"] else None,
        "checks": {
            "database": {
                "ready": database_ready,
                "code": "ok" if database_ready else "database_unavailable",
            },
            "research_artifact_contract": artifacts,
            "readonly_runtime_boundary": runtime_safety,
        },
        "scope": "local_application_dependencies",
        "side_effects": "readonly_database_probe_and_file_reads",
    }
    return jsonify(payload), 200 if payload["ready"] else 503
