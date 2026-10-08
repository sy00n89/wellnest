import http.server
import threading
import time

import insights
from conftest import call


def start_server(handler_cls):
    server = http.server.HTTPServer(('127.0.0.1', 0), handler_cls)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class StallingAnthropic(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        time.sleep(3)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


class OddReplyAnthropic(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = b'{"content": "not a list"}'
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_slow_anthropic_returns_fallback_not_500(monkeypatch):
    # A stalled Anthropic used to raise TimeoutError past the handler's
    # except clause and return 500 (found by the Antithesis workload).
    server = start_server(StallingAnthropic)
    monkeypatch.setattr(insights, 'ANTHROPIC_BASE_URL', f'http://127.0.0.1:{server.server_port}')
    monkeypatch.setattr(insights, 'ANTHROPIC_TIMEOUT_SECONDS', 1)

    status, body = call(insights, 'POST', {})
    assert status == 200
    assert body['text'] == insights.FALLBACK_TEXT


def test_unexpected_reply_shape_returns_fallback(monkeypatch):
    server = start_server(OddReplyAnthropic)
    monkeypatch.setattr(insights, 'ANTHROPIC_BASE_URL', f'http://127.0.0.1:{server.server_port}')

    status, body = call(insights, 'POST', {})
    assert status == 200
    assert body['text'] == insights.FALLBACK_TEXT


class TricklingAnthropic(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Length', '1000')
        self.end_headers()
        for _ in range(1000):          # a byte every 0.3 s: never idle long enough to time out
            self.wfile.write(b' ')
            self.wfile.flush()
            time.sleep(0.3)

    def log_message(self, *args):
        pass


def test_slowly_trickling_anthropic_stays_within_the_deadline(monkeypatch):
    # A reply that arrives a little at a time never trips a per-read timeout,
    # so insights took 31 s under Antithesis network slowdowns.
    server = start_server(TricklingAnthropic)
    monkeypatch.setattr(insights, 'ANTHROPIC_BASE_URL', f'http://127.0.0.1:{server.server_port}')
    monkeypatch.setattr(insights, 'DEADLINE_SECONDS', 3)

    started = time.monotonic()
    status, body = call(insights, 'POST', {})
    assert status == 200
    assert body['text'] == insights.FALLBACK_TEXT
    assert time.monotonic() - started < 5
