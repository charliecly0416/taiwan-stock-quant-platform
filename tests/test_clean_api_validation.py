"""Reject invalid inputs before loading artifacts or computing model signals."""
import pytest

from backend.app import create_app
from backend.app.routes.tw_stock import _date_range_arg


@pytest.mark.parametrize("query", [
    "paper?model=missing&date=2026-09-24",
    "rankings?model=../missing&date=2026-09-24",
    "data/prices?start=not-a-date&end=2026-09-24",
    "data/prices?start=2026-09-25&end=2026-09-24",
    "rankings?date=../../manifest",
    "rankings?date=20260924",
    "rankings?date=",
    "compare?start=2026-09-24",
    "compare?end=2026-09-24",
    "compare?start=2026-09-25&end=2026-09-24",
    "compare?start=2020-01-01&end=2026-09-24",
    "compare?left=missing&right=model_a",
    "ranking-changes?lookback=0",
    "ranking-changes?lookback=61",
    "cross-analysis?limit=0",
    "cross-analysis?limit=invalid",
])
def test_bad_queries_are_blocked_before_service_construction(query, monkeypatch):
    import backend.app.routes.tw_stock as routes

    def forbidden_service():
        pytest.fail("invalid request reached model/data loading")

    monkeypatch.setattr(routes, "ProductService", forbidden_service)
    monkeypatch.setattr(routes, "DataCatalog", forbidden_service)
    app = create_app()
    app.testing = True
    response = app.test_client().get("/api/tw-stock/" + query)
    assert response.status_code == 422
    payload = response.get_json()
    assert payload["status"] == "BLOCKED"
    assert payload["readonly"] is True
    assert payload["simulation_only"] is True


def test_leap_day_uses_last_valid_day_in_previous_year():
    assert _date_range_arg("2024-02-29", None) == ("2023-02-28", "2024-02-29")
    assert _date_range_arg("2026-09-24", None) == ("2025-09-24", "2026-09-24")


def test_explicit_start_survives_leap_day_default():
    assert _date_range_arg("2024-02-29", "2024-01-01") == ("2024-01-01", "2024-02-29")


def test_data_api_serializes_missing_prices_as_json_null(monkeypatch):
    import json
    import pandas as pd
    from backend.app.routes.tw_stock import DataCatalog

    monkeypatch.setattr(DataCatalog, "query_local_source",
                        lambda *args: pd.DataFrame([{"stock_id": "2330", "date": "2026-09-24",
                                                    "open": float("nan"), "close": 10., "volume": float("inf")}]))
    response = create_app().test_client().get("/api/tw-stock/data/prices?start=2026-09-24&end=2026-09-24")
    assert response.status_code == 200
    payload = json.loads(response.get_data(as_text=True),
                         parse_constant=lambda value: pytest.fail(f"non-standard JSON constant: {value}"))
    assert payload["rows"][0]["open"] is None
    assert payload["rows"][0]["volume"] is None
    assert payload["rows"][0]["close"] == 10
    assert payload["simulation_only"] is True
