#!/usr/bin/env python3
"""Serve the built frontend and proxy API requests to the local backend.

This is intended for long-running ngrok/demo access. It avoids Vite dev
server file watchers, which can fail on servers with low inotify limits.
"""

from __future__ import annotations

import argparse
import http.server
import os
import posixpath
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


class StaticProxyHandler(http.server.SimpleHTTPRequestHandler):
    backend_url = "http://127.0.0.1:5000"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stdout.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), fmt % args))
        sys.stdout.flush()

    def do_GET(self) -> None:
        if self._is_api_request():
            self._proxy_request()
            return
        super().do_GET()

    def do_HEAD(self) -> None:
        if self._is_api_request():
            self._proxy_request()
            return
        super().do_HEAD()

    def do_POST(self) -> None:
        self._proxy_request() if self._is_api_request() else self.send_error(405, "Method Not Allowed")

    def do_PUT(self) -> None:
        self._proxy_request() if self._is_api_request() else self.send_error(405, "Method Not Allowed")

    def do_PATCH(self) -> None:
        self._proxy_request() if self._is_api_request() else self.send_error(405, "Method Not Allowed")

    def do_DELETE(self) -> None:
        self._proxy_request() if self._is_api_request() else self.send_error(405, "Method Not Allowed")

    def translate_path(self, path: str) -> str:
        translated = super().translate_path(path)
        if os.path.exists(translated):
            return translated
        parsed = urllib.parse.urlparse(path)
        clean_path = posixpath.normpath(urllib.parse.unquote(parsed.path))
        if self._looks_like_asset(clean_path):
            return translated
        return str(Path(os.getcwd()) / "index.html")

    def _is_api_request(self) -> bool:
        return urllib.parse.urlparse(self.path).path.startswith("/api/")

    @staticmethod
    def _looks_like_asset(path: str) -> bool:
        name = posixpath.basename(path)
        return "." in name and not path.endswith("/")

    def _body(self) -> bytes | None:
        length = self.headers.get("Content-Length")
        if not length:
            return None
        return self.rfile.read(int(length))

    def _forward_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        for key, value in self.headers.items():
            lowered = key.lower()
            if lowered in HOP_BY_HOP_HEADERS or lowered == "host":
                continue
            headers[key] = value
        headers["Host"] = urllib.parse.urlparse(self.backend_url).netloc
        headers["X-Forwarded-Host"] = self.headers.get("Host", "")
        headers["X-Forwarded-Proto"] = "https" if self.headers.get("X-Forwarded-Proto") == "https" else "http"
        return headers

    def _proxy_request(self) -> None:
        target = self.backend_url.rstrip("/") + self.path
        request = urllib.request.Request(
            target,
            data=None if self.command in {"GET", "HEAD"} else self._body(),
            headers=self._forward_headers(),
            method=self.command,
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                self.send_response(response.status, response.reason)
                self._copy_response_headers(response.headers.items())
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(response.read())
        except urllib.error.HTTPError as exc:
            self.send_response(exc.code, exc.reason)
            self._copy_response_headers(exc.headers.items())
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(exc.read())
        except Exception as exc:
            self.send_error(502, f"Backend proxy failed: {exc}")

    def _copy_response_headers(self, items: Iterable[tuple[str, str]]) -> None:
        for key, value in items:
            lowered = key.lower()
            if lowered in HOP_BY_HOP_HEADERS:
                continue
            self.send_header(key, value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("FRONTEND_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("FRONTEND_PORT", "8000")))
    parser.add_argument("--dist", default=os.environ.get("FRONTEND_DIST", "frontend/dist"))
    parser.add_argument("--backend", default=os.environ.get("BACKEND_URL", "http://127.0.0.1:5000"))
    args = parser.parse_args()

    dist = Path(args.dist).resolve()
    if not (dist / "index.html").exists():
        raise SystemExit(f"frontend build not found: {dist / 'index.html'}")

    os.chdir(dist)
    StaticProxyHandler.backend_url = args.backend
    server = http.server.ThreadingHTTPServer((args.host, args.port), StaticProxyHandler)
    print(f"Serving {dist} on http://{args.host}:{args.port}, proxying /api to {args.backend}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
