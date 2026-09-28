from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

BASE_URL = os.getenv("TW_CLEAN_FRONTEND_URL", "http://127.0.0.1:4173")
OUTPUT = Path(os.getenv("TW_CLEAN_ACCEPTANCE_DIR", "tmp/clean_frontend_acceptance"))
CHROME = os.getenv("TW_CLEAN_CHROME", "/home/chuliyang/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def allowed_request(method: str, url: str, base_url: str) -> bool:
    target, base = urlsplit(url), urlsplit(base_url)
    readonly_method = method == "GET" or (method == "POST" and target.path == "/api/tw-stock/agent/simple-chat")
    return (readonly_method and base.scheme == "http"
            and base.hostname in ("127.0.0.1", "localhost", "::1")
            and (target.scheme, target.hostname, target.port) == (base.scheme, base.hostname, base.port)
            and target.username is None and target.password is None)


def commission_replay_fixture() -> dict:
    """Exercise actual replay math with isolated, hand-checkable fixture data."""
    import tempfile
    import pandas as pd
    from clean_product.replay import replay

    with tempfile.TemporaryDirectory(prefix="clean-commission-fixture-") as directory:
        config = {
            "data_root": str(Path(directory) / "data"),
            "artifact_root": str(Path(directory) / "artifacts"),
            "execution": "next_open", "strategy": "top50_exit_one_worst_sell",
            "simulation": {"initial_cash": 1000, "max_positions": 1,
                           "buy_cost_rate": .01, "sell_cost_rate": 0, "min_cost": 20},
            "model_stages": {"model_a_frozen": {}},
            "models": {"model_a": {"stages": ["model_a_frozen"]}},
        }
        prices = pd.DataFrame([
            {"stock_id": "2330", "date": "2026-09-23", "open": 10., "close": 10.},
            {"stock_id": "2330", "date": "2026-09-24", "open": 10., "close": 9.},
        ])
        result = replay(config, {"prices": prices}, "model_a",
                        "2026-09-23", "2026-09-24", fixture=True)
    assert result["status"] == "READY" and result["fixture"] is True
    assert result["trades"][0]["quantity"] == 98 and result["total_fees"] == 20
    assert result["account"]["cash"] == 0 and result["final_nav"] == 882
    assert math.isclose(result["cumulative_return"], -.118)
    assert math.isclose(result["max_drawdown"], -.118)
    return result


def canonical_comparison_case() -> dict:
    """Real frozen historical inputs, materialized only in an isolated directory."""
    import tempfile
    from clean_product.config import load_config
    from clean_product.models import ModelRunner
    from clean_product.service import ProductService

    with tempfile.TemporaryDirectory(prefix='clean-comparison-case-') as directory:
        config = load_config()
        config['artifact_root'] = directory
        for model in ('model_a', 'model_a_plus_b'):
            runner = ModelRunner(config)
            if runner.config['artifact_root'].resolve() != Path(directory).resolve():
                raise ValueError('runtime artifact override conflicts with isolated acceptance')
            result = runner.run(model, '2026-05-07')
            assert result.status == 'READY', result.reason
        service = ProductService(config)
        def no_recompute(*args, **kwargs):
            raise AssertionError('materialized historical comparison was bypassed')
        service.runner.run = no_recompute
        result = service.compare('model_a', 'model_a_plus_b', '2026-05-07')
        assert result['status'] == 'READY' and result['overlap_top50'] == 49
        return result


def main() -> int:
    from playwright.sync_api import sync_playwright

    if not allowed_request("GET", BASE_URL, BASE_URL):
        raise ValueError("acceptance requires a local HTTP server")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    network, console_errors, page_errors, failures, gaps, nonblocking_gaps, observations = [], [], [], [], [], [], []
    rejected_requests, failed_requests = [], []
    checks = {}
    fixture_checks = {}
    comparison_checks, navigation_checks = {}, {}
    paper_checks = {}
    mocked_paper_requests = set()
    fixture_replay = commission_replay_fixture()
    historical_comparison = canonical_comparison_case()
    viewports = {"desktop": (1440, 1000), "tablet": (820, 1100), "mobile": (390, 844)}

    def received(response):
        network.append({"method": response.request.method, "url": response.url, "status": response.status,
                        "mocked_paper": response.request in mocked_paper_requests})
        if '/api/' in response.url and response.status == 200:
            payload = response.json()
            if payload.get('status') == 'BLOCKED':
                item = {"endpoint": response.url, "status": "BLOCKED",
                        "reason": payload.get('reason', payload.get('message'))}
                if (('/api/tw-stock/compare?' in response.url and payload.get('mainline_blocking') is False
                     and 'date=2026-05-07' not in response.url)
                        or payload.get('reason') == 'isolated_navigation_case'):
                    nonblocking_gaps.append({**item, "mainline_blocking": False})
                else:
                    gaps.append(item)

    def guard(route):
        request = route.request
        if allowed_request(request.method, request.url, BASE_URL):
            route.continue_()
        else:
            rejected_requests.append({"method": request.method, "url": request.url})
            route.abort()

    def submit(page, form, endpoint, viewport, *, fixture=False):
        with page.expect_response(lambda r: endpoint in r.url, timeout=90000) as event:
            page.locator(form + " button").first.click()
        response = event.value
        payload = response.json()
        observations.append({"viewport": viewport, "endpoint": endpoint, "http": response.status,
                             "status": payload.get("status"), "reason": payload.get("reason"),
                             "fixture": fixture})
        shadow_compare_blocked = (endpoint == '/api/tw-stock/compare?' and payload.get('status') == 'BLOCKED'
                                  and payload.get('mainline_blocking') is False and payload.get('asof') != '2026-05-07')
        if response.status != 200 or (payload.get("status") != "READY" and not shadow_compare_blocked):
            item = {"viewport": viewport, "endpoint": endpoint, "status": payload.get("status"),
                    "reason": payload.get("reason", payload.get("message"))}
            (nonblocking_gaps if shadow_compare_blocked else gaps).append({**item, "mainline_blocking": False} if shadow_compare_blocked else item)
        return payload

    def capture(page, viewport, view):
        layout = page.evaluate("""() => {
            const width = document.documentElement.clientWidth;
            const boundary = document.querySelector('.boundary');
            const boundaryBox = boundary.getBoundingClientRect();
            const controls = [...document.querySelectorAll('#view input, #view select, #view button')]
                .map(el => ({tag: el.tagName, name: el.name, box: el.getBoundingClientRect()}))
                .filter(el => el.box.width > 0 && el.box.height > 0);
            return {
                overflow_x: document.documentElement.scrollWidth > width,
                content_characters: document.querySelector('#view').innerText.trim().length,
                controls_outside_viewport: controls.filter(el => el.box.left < -1 || el.box.right > width + 1)
                    .map(el => ({tag: el.tag, name: el.name})),
                readonly_boundary_visible: boundaryBox.width > 0 && boundaryBox.height > 0
                    && getComputedStyle(boundary).visibility !== 'hidden'
                    && boundary.innerText.includes('只读研究'),
            };
        }""")
        checks[viewport][view] = layout
        assert layout['content_characters'] > 0, "blank main view"
        assert not layout['controls_outside_viewport'], "form controls outside viewport"
        assert layout['readonly_boundary_visible'], "missing readonly boundary"
        page.screenshot(path=str(OUTPUT / f"{viewport}_{view}.png"), full_page=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=CHROME)
        try:
            for name, (width, height) in viewports.items():
                checks[name] = {}
                context = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
                context.route("**/*", guard)
                page = context.new_page()
                page.on("response", received)
                page.on("requestfailed", lambda request: failed_requests.append({"url": request.url, "error": request.failure}))
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                try:
                    page.goto(BASE_URL, wait_until="networkidle")
                    page.locator('.cross-panel').wait_for(timeout=30000)
                    if page.locator('.cross-panel tbody tr').count():
                        technical_cells = page.locator('.cross-panel tbody tr').first.locator('td')
                        for index in (2, 3, 4):
                            assert technical_cells.nth(index).inner_text() not in ('—', ''), "missing technical context"
                    else:
                        assert page.locator('.cross-panel .empty').count() == 1, "blocked context is blank"
                    explanation = submit(page, '#explain-form', '/api/tw-stock/agent/explain/', name)
                    page.locator('#explain-result .explanation-result, #explain-result .empty').wait_for()
                    if explanation['status'] != 'READY':
                        assert explanation['reason'] in page.locator('#explain-result').inner_text()
                    with page.expect_response(lambda r: '/agent/simple-chat' in r.url) as chat_response:
                        page.locator('#agent-form button').click()
                    chat = chat_response.value.json()
                    page.locator('#agent-result .explanation-result').wait_for()
                    assert chat['mode'] == 'artifact_local' and chat['readonly'] is True
                    if chat['blocked']:
                        assert chat['reason'] in page.locator('#agent-result').inner_text()
                    capture(page, name, 'overview')

                    page.locator('[data-view="rankings"]').click()
                    page.locator('#rankings-form').wait_for()
                    page.go_back()
                    page.locator('.candidate-panel').wait_for()
                    page.go_forward()
                    page.locator('#rankings-form').wait_for()
                    current = submit(page, '#rankings-form', '/api/tw-stock/rankings?', name)
                    if current['status'] != 'READY':
                        page.locator('#rankings-result .empty').wait_for()
                        assert current['reason'] in page.locator('#rankings-result').inner_text()
                    # Historical positive path is distinct from the current artifact gate.
                    page.locator('#rankings-form input[name="date"]').fill('2025-06-23')
                    for limit in ([30, 50] if name == 'desktop' else [50]):
                        page.locator('select[name="limit"]').select_option(str(limit))
                        payload = submit(page, '#rankings-form', '/api/tw-stock/rankings?', name)
                        page.locator('#rankings-result tbody tr').first.wait_for()
                        assert len(payload['rows']) == limit
                        assert page.locator('#rankings-result tbody tr').count() == limit
                    if name == 'desktop':
                        with page.expect_response(lambda r: '/ranking-changes?' in r.url, timeout=90000) as event:
                            page.locator('[data-load-changes]').click()
                        changes = event.value.json()
                        assert changes['status'] == 'READY'
                        page.locator('#ranking-changes-result .panel').wait_for()
                        observations.append({"viewport": name, "endpoint": "ranking-changes", "status": changes['status'],
                                             "entered": changes['entered'], "exited": changes['exited']})
                    capture(page, name, 'rankings')

                    page.locator('[data-view="compare"]').click()
                    page.locator('#compare-form').wait_for()
                    page.locator('#compare-form input[name="date"]').fill('2026-05-07')
                    if name == 'desktop':
                        page.locator('input[name="includeReplay"]').check()
                    comparison = submit(page, '#compare-form', '/api/tw-stock/compare?', name)
                    page.locator('#compare-result .comparison-summary, #compare-result .split-blocked').first.wait_for()
                    if name == 'desktop' and comparison['status'] == 'READY':
                        page.locator('#compare-result .comparison-summary.four').wait_for()
                        for side in ('left', 'right'):
                            window = comparison['window'][side]
                            if window['status'] != 'READY':
                                gaps.append({"viewport": name, "endpoint": "comparison replay " + side,
                                             "status": window['status'], "reason": window.get('reason')})
                    capture(page, name, 'compare')
                    def historical_route(route):
                        if allowed_request(route.request.method, route.request.url, BASE_URL):
                            route.fulfill(status=200, content_type='application/json', body=json.dumps(historical_comparison))
                        else:
                            guard(route)
                    context.route('**/api/tw-stock/compare?*', historical_route)
                    page.locator('input[name="includeReplay"]').uncheck()
                    submit(page, '#compare-form', '/api/tw-stock/compare?', name, fixture=True)
                    page.locator('#compare-result .comparison-summary').wait_for()
                    assert page.locator('#compare-result .comparison-summary strong').first.inner_text() == '49'
                    assert page.locator('#compare-result tbody tr').count() == len(historical_comparison['rows'])
                    comparison_checks[name] = {'passed': True, 'asof': '2026-05-07', 'overlap': 49,
                                               'source': 'verified frozen assets; isolated materialization; mocked browser response'}
                    page.screenshot(path=str(OUTPUT / f'{name}_compare_historical.png'), full_page=True)
                    context.unroute('**/api/tw-stock/compare?*', historical_route)

                    page.locator('[data-view="replay"]').click()
                    page.locator('#replay-form').wait_for()
                    page.locator('input[name="start"]').fill("2025-06-23")
                    page.locator('input[name="end"]').fill("2025-06-30")
                    replay = submit(page, '#replay-form', '/api/tw-stock/replay?', name)
                    if replay['status'] == 'READY':
                        page.locator('#replay-result .comparison-summary.four').wait_for()
                        assert all(math.isfinite(replay[key]) for key in ('final_nav', 'max_drawdown', 'total_fees'))
                    else:
                        page.locator('#replay-result .empty').wait_for()
                        assert replay.get('reason', '') in page.locator('#replay-result').inner_text()
                    capture(page, name, 'replay')

                    page.locator('[data-view="market"]').click()
                    page.locator('#market-form').wait_for()
                    page.locator('input[name="start"]').fill("2026-09-21")
                    page.locator('input[name="end"]').fill("2026-09-24")
                    market = submit(page, '#market-form', '/api/tw-stock/market/', name)
                    page.locator('#market-result .line-chart').wait_for()
                    assert all(market['summary'][key] is not None for key in ('ma20', 'rsi14', 'ret20'))
                    formatted = page.evaluate("n => n.toLocaleString('zh-TW', {maximumFractionDigits: 2})", market['summary']['ma20'])
                    assert page.locator('#market-result .technical-strip strong').nth(1).inner_text() == formatted
                    capture(page, name, 'market')

                    # All paper traffic is fulfilled locally; guard still forbids
                    # real paper POSTs. No live account or token is involved.
                    paper_state = {'status': 'READY', 'paper_account_id': 'fixture-account',
                                   'cash': '1000.00', 'epoch': 1, 'positions': {}, 'simulation_only': True}
                    paper_calls = []
                    def paper_route(route):
                        request = route.request
                        if not allowed_request('GET', request.url, BASE_URL) or request.method not in ('GET', 'POST'):
                            guard(route)
                            return
                        mocked_paper_requests.add(request)
                        suffix = urlsplit(request.url).path
                        body = request.post_data_json if request.method == 'POST' else None
                        paper_calls.append({'path': suffix, 'method': request.method, 'payload': body})
                        if suffix.endswith('/sim/accounts'):
                            result = {'status': 'READY', 'accounts': [paper_state]}
                        elif suffix.endswith('/preview'):
                            result = {'status': 'PREVIEW', 'paper_account_id': 'fixture-account',
                                      'epoch': 1, 'decision_id': 'fixture-decision', 'input_checksum': 'fixture-checksum',
                                      'actions': [{'instrument': 'TW2330', 'action': 'buy', 'quantity': 90, 'price': '10'}]}
                        elif suffix.endswith('/apply-decision'):
                            assert body['confirm'] is True and body['decision_id'] == 'fixture-decision'
                            result = {'status': 'APPLIED', 'state': {**paper_state, 'cash': '80.00'}}
                        elif suffix.endswith('/reset'):
                            assert body['confirm'] is True
                            result = {'status': 'RESET', 'state': {**paper_state, 'epoch': 2}}
                        elif suffix.endswith('/apply-runs'):
                            result = {'status': 'READY', 'runs': [{'operation': 'reset',
                                      'created_at': '2026-09-24T09:00:00Z', 'result': {'status': 'RESET'}}]}
                        else:
                            result = paper_state
                        route.fulfill(status=200, content_type='application/json', body=json.dumps(result))
                    context.route('**/api/tw-stock/paper-portfolio/*', paper_route)
                    context.route('**/api/tw-stock/sim/accounts', paper_route)
                    page.locator('[data-view="paper"]').click()
                    page.locator('#paper-form').wait_for()
                    page.locator('#paper-form [name="token"]').fill('fixture-only-not-a-real-token')
                    page.locator('#paper-form button').click()
                    page.locator('#paper-result').get_by_text('READY', exact=True).wait_for()
                    page.locator('#paper-form [name="operation"]').select_option('preview')
                    page.locator('#paper-form [name="date"]').fill('2026-09-23')
                    page.locator('#paper-form button').click()
                    page.locator('#paper-result').get_by_text('PREVIEW', exact=True).wait_for()
                    page.locator('#paper-form [name="operation"]').select_option('apply')
                    page.locator('#paper-form button').click()
                    page.locator('#paper-result').get_by_text('模拟操作未完成', exact=True).wait_for()
                    assert not any(item['path'].endswith('/apply-decision') for item in paper_calls)
                    page.locator('#paper-form [name="confirm"]').check()
                    page.locator('#paper-form button').click()
                    page.locator('#paper-result').get_by_text('APPLIED', exact=True).wait_for()
                    page.locator('#paper-form [name="operation"]').select_option('reset')
                    page.locator('#paper-form [name="confirm"]').check()
                    page.locator('#paper-form button').click()
                    page.locator('#paper-result').get_by_text('RESET', exact=True).wait_for()
                    page.locator('#paper-form [name="operation"]').select_option('history')
                    page.locator('#paper-form button').click()
                    page.locator('#paper-result').get_by_text('最近模拟记录', exact=True).wait_for()
                    assert page.locator('#paper-result tbody tr').count() == 1
                    assert page.evaluate('localStorage.length + sessionStorage.length') == 0
                    page.locator('#paper-form [name="token"]').fill('')
                    capture(page, name, 'paper')
                    paper_checks[name] = {'passed': True, 'transport': 'mocked; no live account writes',
                                          'confirmation_gate': True, 'history': True, 'token_not_persisted': True}
                    context.unroute('**/api/tw-stock/paper-portfolio/*', paper_route)
                    context.unroute('**/api/tw-stock/sim/accounts', paper_route)
                    page.locator('[data-view="system"]').click()
                    page.locator('text=数据集状态').wait_for()
                    capture(page, name, 'system')

                    # Keep successful fixture rendering separate from real-data gaps.
                    page.locator('[data-view="replay"]').click()
                    page.locator('#replay-form').wait_for()
                    page.locator('input[name="start"]').fill(fixture_replay['start'])
                    page.locator('input[name="end"]').fill(fixture_replay['end'])
                    def fixture_route(route):
                        if allowed_request(route.request.method, route.request.url, BASE_URL):
                            route.fulfill(status=200, content_type="application/json",
                                          body=json.dumps(fixture_replay))
                        else:
                            guard(route)
                    context.route('**/api/tw-stock/replay?*', fixture_route)
                    submit(page, '#replay-form', '/api/tw-stock/replay?', name, fixture=True)
                    metrics = page.locator('#replay-result .comparison-summary strong')
                    metrics.first.wait_for()
                    assert metrics.all_inner_texts() == ['-11.80%', '-11.80%', 'NT$ 882', '1']
                    assert page.locator('#replay-result .account-panel strong').all_inner_texts() == [
                        'NT$ 0', 'NT$ 882', '1', 'next_open']
                    assert page.locator('#replay-result tbody tr td').nth(3).inner_text() == '98'
                    points = page.locator('#replay-result polyline').get_attribute('points')
                    assert len(points.split()) == 2
                    fixture_checks[name] = {"passed": True, "fixture": True,
                                            "metrics": metrics.all_inner_texts(), "nav_points": 2}
                    page.screenshot(path=str(OUTPUT / f"{name}_replay_fixture.png"), full_page=True)
                    context.unroute('**/api/tw-stock/replay?*', fixture_route)
                    # Hold one overview request and navigate before it completes.
                    held = []
                    context.route('**/api/tw-stock/cross-analysis?*', lambda route: held.append(route))
                    page.goto(BASE_URL, wait_until='domcontentloaded')
                    page.wait_for_function("document.querySelector('#asof')?.textContent.includes('资料截至')")
                    for _ in range(100):
                        if held: break
                        page.wait_for_timeout(50)
                    assert held, 'overview request was not held'
                    page.locator('[data-view="rankings"]').click()
                    page.locator('#rankings-form').wait_for()
                    for route in held:
                        route.fulfill(status=200, content_type='application/json', body=json.dumps({
                            'status': 'BLOCKED', 'reason': 'isolated_navigation_case', 'rows': []}))
                    page.wait_for_load_state('networkidle')
                    assert page.locator('#rankings-form').count() == 1
                    assert page.locator('.candidate-panel').count() == 0
                    navigation_checks[name] = {'passed': True, 'old_response_cannot_replace_current_view': True}
                    context.unroute('**/api/tw-stock/cross-analysis?*')
                except Exception as exc:
                    failures.append({"viewport": name, "error": str(exc)})
                    page.screenshot(path=str(OUTPUT / f"{name}_failure.png"), full_page=True)
                finally:
                    context.close()
        finally:
            browser.close()

    # Mock paper POST responses never leave the browser; audit separately.
    forbidden = rejected_requests + [item for item in network if not allowed_request(item['method'], item['url'], BASE_URL)
                                    and not item['mocked_paper']]
    failed = [item for item in network if item['status'] >= 400]
    overflow = any(view['overflow_x'] for views in checks.values() for view in views.values())
    complete = all(len(views) == 7 for views in checks.values())
    ui_passed = (complete and len(fixture_checks) == len(comparison_checks) == len(navigation_checks) == len(paper_checks) == len(viewports)
                 and not (failures or forbidden or failed or failed_requests or console_errors or page_errors or overflow))
    source_files = sorted({str(path.relative_to(ROOT))
                           for pattern in ('clean_product/*.py', 'backend/app/**/*.py', 'configs/product.yaml',
                                           'frontend/src/*', 'frontend/dist/assets/*', 'frontend/dist/index.html',
                                           'scripts/accept_clean_frontend.py', 'scripts/verify_clean_product.py')
                           for path in ROOT.glob(pattern) if path.is_file()})
    summary = {
        "base_url": BASE_URL, "scope": "seven_views_all_three_viewports", "ui_passed": ui_passed,
        "passed": ui_passed and not gaps, "release_acceptance": "NOT_EVALUATED",
        "checks": checks, "failures": failures, "business_gaps": gaps,
        "nonblocking_business_gaps": nonblocking_gaps,
        "fixture_replay_checks": fixture_checks,
        "historical_comparison_checks": comparison_checks, "navigation_race_checks": navigation_checks,
        "paper_fixture_checks": paper_checks,
        "visual_review": "NOT_PERFORMED", "layout_verification": "DOM geometry and content assertions",
        "forbidden_request_count": len(forbidden), "failed_response_count": len(failed),
        "failed_request_count": len(failed_requests),
        "console_error_count": len(console_errors), "page_error_count": len(page_errors),
        "screenshots": sorted(path.name for path in OUTPUT.glob('*.png')),
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_files},
    }
    reports = {'summary.json': summary, 'network_audit.json': network, 'observations.json': observations,
               'request_audit.json': {"rejected": rejected_requests, "failed": failed_requests},
               'console_audit.json': {"console_errors": console_errors, "page_errors": page_errors}}
    for filename, payload in reports.items():
        (OUTPUT / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == "__main__":
    import argparse
    from threading import Thread

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve-build", action="store_true",
                        help="Serve the built UI and readonly API on an isolated local port; stop after acceptance.")
    args = parser.parse_args()
    server = None
    thread = None
    try:
        if args.serve_build:
            from flask import send_from_directory
            from werkzeug.serving import make_server
            from backend.app import create_app

            dist = ROOT / "frontend" / "dist"
            if not (dist / "index.html").is_file():
                parser.error("build frontend first: cd frontend && corepack pnpm build")
            app = create_app({'AGENT_REMOTE_DISABLED': True})
            app.add_url_rule("/", "acceptance_index", lambda: send_from_directory(dist, "index.html"))
            app.add_url_rule("/assets/<path:name>", "acceptance_assets", lambda name: send_from_directory(dist / "assets", name))
            server = make_server("127.0.0.1", 0, app, threaded=True)
            BASE_URL = f"http://127.0.0.1:{server.server_port}"
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
        raise SystemExit(main())
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=5)
