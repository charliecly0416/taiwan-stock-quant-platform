from __future__ import annotations


def test_paper_routes_are_registered_on_extracted_blueprint(app) -> None:
    paths = {
        "/api/tw-stock/sim/accounts",
        "/api/tw-stock/sim/accounts/<account_uid>",
        "/api/tw-stock/sim/accounts/<account_uid>/positions",
        "/api/tw-stock/sim/accounts/<account_uid>/trades",
        "/api/tw-stock/sim/orders/draft",
        "/api/tw-stock/sim/orders/<sim_order_uid>/confirm",
        "/api/tw-stock/sim/orders/<sim_order_uid>/cancel",
        "/api/tw-stock/paper-portfolio/state",
        "/api/tw-stock/paper-portfolio/apply-runs",
        "/api/tw-stock/paper-portfolio/latest-decision",
        "/api/tw-stock/paper-portfolio/apply-decision",
        "/api/tw-stock/paper-portfolio/reset",
    }
    rows = [rule for rule in app.url_map.iter_rules() if rule.rule in paths]
    # ``/sim/accounts`` is intentionally registered for both GET and POST.
    assert len(rows) == len(paths) + 1
    assert all(rule.endpoint.startswith("tw_stock_paper.") for rule in rows)
