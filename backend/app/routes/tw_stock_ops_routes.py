"""Operations and monitor compatibility routes extracted from aggregate."""
from __future__ import annotations

from flask import Blueprint

tw_stock_ops_bp = Blueprint("tw_stock_ops", __name__)


def _legacy(name: str, *args):
    from app.routes import tw_stock

    return getattr(tw_stock, name)(*args)


@tw_stock_ops_bp.route("/quant/ops/option-c/dry-run", methods=["POST"])
def trigger_qlib_option_c_ops_dry_run(): return _legacy("trigger_qlib_option_c_ops_dry_run")


@tw_stock_ops_bp.route("/quant/ops/option-c/jobs/<job_id>", methods=["GET"])
def get_qlib_option_c_ops_job(job_id: str): return _legacy("get_qlib_option_c_ops_job", job_id)


@tw_stock_ops_bp.route("/quant/ops/option-c/jobs/<job_id>/logs", methods=["GET"])
def get_qlib_option_c_ops_job_log_tail(job_id: str): return _legacy("get_qlib_option_c_ops_job_log_tail", job_id)


@tw_stock_ops_bp.route("/quant/ops/option-c/latest", methods=["GET"])
def get_qlib_option_c_ops_latest(): return _legacy("get_qlib_option_c_ops_latest")


@tw_stock_ops_bp.route("/quant/ops/daily-auto-update/status", methods=["GET"])
def get_daily_auto_update_status(): return _legacy("get_daily_auto_update_status")


@tw_stock_ops_bp.route("/quant/ops/readonly-status", methods=["GET"])
def get_readonly_ops_status(): return _legacy("get_readonly_ops_status")


@tw_stock_ops_bp.route("/quant/ops/option-c/scheduler", methods=["GET"])
def get_qlib_option_c_scheduler_status(): return _legacy("get_qlib_option_c_scheduler_status")


@tw_stock_ops_bp.route("/quant/ops/option-c/scheduler/tick", methods=["POST"])
def tick_qlib_option_c_scheduler(): return _legacy("tick_qlib_option_c_scheduler")


@tw_stock_ops_bp.route("/quant/ops/option-c/accepted-latest-scheduler", methods=["GET"])
def get_qlib_option_c_accepted_latest_scheduler_status(): return _legacy("get_qlib_option_c_accepted_latest_scheduler_status")


@tw_stock_ops_bp.route("/quant/ops/option-c/accepted-latest-scheduler/tick", methods=["POST"])
def tick_qlib_option_c_accepted_latest_scheduler(): return _legacy("tick_qlib_option_c_accepted_latest_scheduler")


@tw_stock_ops_bp.route("/quant/ops/option-c/eod-pipeline", methods=["GET"])
def get_qlib_option_c_eod_pipeline_status(): return _legacy("get_qlib_option_c_eod_pipeline_status")


@tw_stock_ops_bp.route("/quant/ops/option-c/eod-pipeline/tick", methods=["POST"])
def tick_qlib_option_c_eod_pipeline(): return _legacy("tick_qlib_option_c_eod_pipeline")


@tw_stock_ops_bp.route("/quant/ops/option-c/eod-automation", methods=["GET"])
def get_qlib_option_c_eod_automation_status(): return _legacy("get_qlib_option_c_eod_automation_status")


@tw_stock_ops_bp.route("/quant/ops/option-c/eod-automation/tick", methods=["POST"])
def tick_qlib_option_c_eod_automation(): return _legacy("tick_qlib_option_c_eod_automation")


@tw_stock_ops_bp.route("/quant/ops/option-c/normal-publish", methods=["POST"])
def normal_publish_qlib_option_c_latest(): return _legacy("normal_publish_qlib_option_c_latest")


@tw_stock_ops_bp.route("/monitor/config", methods=["GET"])
def get_monitor_config(): return _legacy("get_monitor_config")


@tw_stock_ops_bp.route("/monitor/config", methods=["POST", "PUT"])
def save_monitor_config(): return _legacy("save_monitor_config")


@tw_stock_ops_bp.route("/monitor/alerts", methods=["GET"])
def get_monitor_alerts(): return _legacy("get_monitor_alerts")


@tw_stock_ops_bp.route("/monitor/alerts", methods=["POST"])
def create_monitor_alert(): return _legacy("create_monitor_alert")


@tw_stock_ops_bp.route("/monitor/alerts/<int:alert_id>", methods=["PUT"])
def update_monitor_alert(alert_id: int): return _legacy("update_monitor_alert", alert_id)


@tw_stock_ops_bp.route("/monitor/history", methods=["GET"])
def get_monitor_history(): return _legacy("get_monitor_history")


@tw_stock_ops_bp.route("/monitor/scan", methods=["POST"])
def scan_monitor(): return _legacy("scan_monitor")


@tw_stock_ops_bp.route("/monitor/scan-all", methods=["POST"])
def scan_all_monitors(): return _legacy("scan_all_monitors")


@tw_stock_ops_bp.route("/monitor/scan-logs", methods=["GET"])
def get_monitor_scan_logs(): return _legacy("get_monitor_scan_logs")


@tw_stock_ops_bp.route("/monitor", methods=["GET"])
def monitor_page(): return _legacy("monitor_page")
