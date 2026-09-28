"""The browser audit must prevent remote or write requests before sending them."""
import pytest

from scripts.accept_clean_frontend import allowed_request


@pytest.mark.parametrize("method,url,expected", [
    ("GET", "http://127.0.0.1:4173/api/tw-stock/overview", True),
    ("GET", "http://127.0.0.1:4173/assets/main.js", True),
    ("POST", "http://127.0.0.1:4173/api/tw-stock/overview", False),
    ("POST", "http://127.0.0.1:4173/api/tw-stock/agent/simple-chat", True),
    ("POST", "http://127.0.0.1:4173/api/tw-stock/paper-portfolio/apply-decision", False),
    ("GET", "https://example.invalid/v1/responses", False),
    ("GET", "http://127.0.0.1:5000/api/ready", False),
    ("GET", "http://user:pass@127.0.0.1:4173/", False),
])
def test_acceptance_request_boundary(method, url, expected):
    assert allowed_request(method, url, "http://127.0.0.1:4173") is expected


def test_remote_base_url_is_not_accepted():
    remote = "https://example.invalid/"
    assert not allowed_request("GET", remote, remote)
