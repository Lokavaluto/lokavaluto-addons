import io
import json

from odoo.tests.common import BaseCase

from ..http import _handle_batch


def _make_environ(body, method="POST", path="/batch", headers=None):
    """Build a minimal WSGI environ dict for testing."""
    raw = json.dumps(body).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    }
    if headers:
        environ.update(headers)
    return environ


def _make_wsgi_app(handler):
    """Wrap a handler(environ) -> (status, body) into a WSGI app."""

    def wsgi_app(environ, start_response):
        status_code, response_body = handler(environ)
        data = json.dumps(response_body).encode("utf-8")
        start_response(
            f"{status_code} OK",
            [("Content-Type", "application/json")],
        )
        return [data]

    return wsgi_app


def _collect_response(environ, handle_fn):
    """Call a WSGI handler and return (status_code, parsed_body)."""
    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status

    result_iter = handle_fn(environ, start_response)
    raw = b"".join(result_iter)
    status_code = int(captured["status"].split(" ", 1)[0])
    return status_code, json.loads(raw)


class TestBatchEndpoint(BaseCase):
    """Unit tests for the ``/batch`` WSGI handler."""

    def test_valid_batch_multiple_requests(self):
        """A batch with two valid sub-requests returns both responses."""

        call_log = []

        def handler(environ):
            path = environ["PATH_INFO"]
            call_log.append(path)
            if path == "/api/first":
                return 200, {"result": "one"}
            return 200, {"result": "two"}

        app = _make_wsgi_app(handler)
        environ = _make_environ(
            {
                "requests": [
                    {"path": "/api/first"},
                    {"path": "/api/second"},
                ]
            }
        )

        status, body = _collect_response(
            environ, lambda e, sr: _handle_batch(app, e, sr)
        )

        self.assertEqual(status, 200)
        self.assertEqual(len(body["responses"]), 2)
        self.assertEqual(body["responses"][0]["status"], 200)
        self.assertEqual(body["responses"][0]["body"]["result"], "one")
        self.assertEqual(body["responses"][1]["status"], 200)
        self.assertEqual(body["responses"][1]["body"]["result"], "two")
        self.assertEqual(call_log, ["/api/first", "/api/second"])

    def test_invalid_json_body(self):
        """A batch request with invalid JSON returns 400."""

        raw = b"not json"
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/batch",
            "CONTENT_LENGTH": str(len(raw)),
            "wsgi.input": io.BytesIO(raw),
        }

        status, body = _collect_response(
            environ,
            lambda e, sr: _handle_batch(_make_wsgi_app(lambda e: (200, {})), e, sr),
        )

        self.assertEqual(status, 400)
        self.assertIn("Invalid JSON", body["error"])

    def test_missing_requests_key(self):
        """A batch body without 'requests' returns 400."""

        environ = _make_environ({"not_requests": []})

        status, body = _collect_response(
            environ,
            lambda e, sr: _handle_batch(_make_wsgi_app(lambda e: (200, {})), e, sr),
        )

        self.assertEqual(status, 400)
        self.assertIn("requests", body["error"])

    def test_requests_not_a_list(self):
        """A batch body with 'requests' as a string returns 400."""

        environ = _make_environ({"requests": "not a list"})

        status, body = _collect_response(
            environ,
            lambda e, sr: _handle_batch(_make_wsgi_app(lambda e: (200, {})), e, sr),
        )

        self.assertEqual(status, 400)
        self.assertIn("requests", body["error"])

    def test_sub_request_missing_path(self):
        """A sub-request without 'path' returns status 400 for that item."""

        environ = _make_environ({"requests": [{"method": "GET"}, {"path": "/ok"}]})

        status, body = _collect_response(
            environ,
            lambda e, sr: _handle_batch(
                _make_wsgi_app(lambda e: (200, {"ok": True})), e, sr
            ),
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["responses"][0]["status"], 400)
        self.assertIn("path", body["responses"][0]["body"]["error"])
        self.assertEqual(body["responses"][1]["status"], 200)

    def test_auth_headers_forwarded(self):
        """Auth headers from the batch request are forwarded to sub-requests."""

        received_headers = {}

        def handler(environ):
            received_headers["api_key"] = environ.get("HTTP_API_KEY")
            received_headers["cookie"] = environ.get("HTTP_COOKIE")
            received_headers["auth"] = environ.get("HTTP_AUTHORIZATION")
            return 200, {"ok": True}

        app = _make_wsgi_app(handler)
        environ = _make_environ(
            {"requests": [{"path": "/api/test"}]},
            headers={
                "HTTP_API_KEY": "my-secret-key",
                "HTTP_COOKIE": "session_id=abc123",
                "HTTP_AUTHORIZATION": "Bearer token",
            },
        )

        _collect_response(environ, lambda e, sr: _handle_batch(app, e, sr))

        self.assertEqual(received_headers["api_key"], "my-secret-key")
        self.assertEqual(received_headers["cookie"], "session_id=abc123")
        self.assertEqual(received_headers["auth"], "Bearer token")

    def test_sub_request_exception_returns_500(self):
        """A sub-request that raises an exception returns status 500."""

        def handler(environ):
            raise RuntimeError("boom")

        app = _make_wsgi_app(handler)
        environ = _make_environ({"requests": [{"path": "/api/crash"}]})

        status, body = _collect_response(
            environ, lambda e, sr: _handle_batch(app, e, sr)
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["responses"][0]["status"], 500)

    def test_default_method_is_post(self):
        """Sub-requests without 'method' default to POST."""

        received_method = {}

        def handler(environ):
            received_method["method"] = environ["REQUEST_METHOD"]
            return 200, {"ok": True}

        app = _make_wsgi_app(handler)
        environ = _make_environ({"requests": [{"path": "/api/test"}]})

        _collect_response(environ, lambda e, sr: _handle_batch(app, e, sr))

        self.assertEqual(received_method["method"], "POST")

    def test_explicit_method_honored(self):
        """Sub-requests with explicit 'method' use that method."""

        received_method = {}

        def handler(environ):
            received_method["method"] = environ["REQUEST_METHOD"]
            return 200, {"ok": True}

        app = _make_wsgi_app(handler)
        environ = _make_environ({"requests": [{"path": "/api/test", "method": "GET"}]})

        _collect_response(environ, lambda e, sr: _handle_batch(app, e, sr))

        self.assertEqual(received_method["method"], "GET")

    def test_body_takes_precedence_over_params(self):
        """When both 'body' and 'params' are provided, 'body' is used."""

        received_data = {}

        def handler(environ):
            length = int(environ.get("CONTENT_LENGTH", 0) or 0)
            raw = environ["wsgi.input"].read(length)
            received_data["payload"] = json.loads(raw)
            return 200, {"ok": True}

        app = _make_wsgi_app(handler)
        environ = _make_environ(
            {
                "requests": [
                    {
                        "path": "/api/test",
                        "params": {"from_params": True},
                        "body": {"from_body": True},
                    }
                ]
            }
        )

        _collect_response(environ, lambda e, sr: _handle_batch(app, e, sr))

        self.assertIn("from_body", received_data["payload"])
        self.assertNotIn("from_params", received_data["payload"])

    def test_params_used_when_no_body(self):
        """When only 'params' is provided, it is used as the request body."""

        received_data = {}

        def handler(environ):
            length = int(environ.get("CONTENT_LENGTH", 0) or 0)
            raw = environ["wsgi.input"].read(length)
            received_data["payload"] = json.loads(raw)
            return 200, {"ok": True}

        app = _make_wsgi_app(handler)
        environ = _make_environ(
            {
                "requests": [
                    {
                        "path": "/api/test",
                        "params": {"from_params": True},
                    }
                ]
            }
        )

        _collect_response(environ, lambda e, sr: _handle_batch(app, e, sr))

        self.assertIn("from_params", received_data["payload"])

    def test_mixed_success_and_failure(self):
        """A batch with mixed outcomes returns per-request statuses."""

        def handler(environ):
            if environ["PATH_INFO"] == "/api/fail":
                return 403, {"error": "forbidden"}
            return 200, {"ok": True}

        app = _make_wsgi_app(handler)
        environ = _make_environ(
            {
                "requests": [
                    {"path": "/api/ok"},
                    {"path": "/api/fail"},
                    {"path": "/api/ok2"},
                ]
            }
        )

        status, body = _collect_response(
            environ, lambda e, sr: _handle_batch(app, e, sr)
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["responses"][0]["status"], 200)
        self.assertEqual(body["responses"][1]["status"], 403)
        self.assertEqual(body["responses"][2]["status"], 200)
