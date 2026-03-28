import io
import json
import logging

from odoo.http import root
from odoo.exceptions import AccessDenied, MissingError
from odoo.addons.base_rest import http
from werkzeug.exceptions import NotAcceptable
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Response
from werkzeug.datastructures import Headers

from .services import MissingCommonFeature

_logger = logging.getLogger(__name__)

BATCH_PATH = "/batch"

try:
    import pyquerystring
except (ImportError, IOError) as err:
    _logger.debug(err)


##
## Batch request support
##


def _dispatch_sub_request(wsgi_app, environ, path, method, params, body, headers=None):
    """Dispatch a single sub-request through the WSGI app.

    Builds a synthetic WSGI environ that inherits session cookies
    from the original ``environ`` and dispatches it through
    ``wsgi_app``.  Returns ``(status_code, parsed_body,
    response_headers_dict)``.

    ``headers`` is an optional dict of HTTP headers for this
    sub-request (e.g. ``{"X-Client-Features": "wallet/0"}``).
    They are applied after the forwarded session headers, so
    per-sub-request headers override batch-level ones.
    """
    content_type = "application/json"
    data = json.dumps(body if body is not None else params).encode("utf-8")
    builder = EnvironBuilder(
        path=path,
        method=method,
        data=data,
        content_type=content_type,
    )
    sub_environ = builder.get_environ()

    ## Forward relevant headers from the original request so that
    ## session auth, token auth and content negotiation work inside
    ## a batch.
    for header in ("HTTP_COOKIE", "HTTP_AUTHORIZATION", "HTTP_ACCEPT", "HTTP_API_KEY"):
        if header in environ:
            sub_environ[header] = environ[header]

    ## Apply per-sub-request headers.  Header names are converted
    ## from HTTP form (``X-Foo-Bar``) to WSGI environ form
    ## (``HTTP_X_FOO_BAR``).
    for name, value in (headers or {}).items():
        wsgi_key = "HTTP_" + name.upper().replace("-", "_")
        sub_environ[wsgi_key] = value

    ## Capture the sub-response via a simple collector.
    ## The WSGI spec (PEP 3333) allows apps to send body data via
    ## either the returned iterable OR the write() callable from
    ## start_response.  We must capture both.
    captured = {}
    write_buf = io.BytesIO()

    def capture_start_response(status, headers_list, exc_info=None):
        captured["status"] = status
        captured["headers"] = headers_list
        return write_buf.write

    try:
        result_iter = wsgi_app(sub_environ, capture_start_response)
        iter_bytes = b"".join(result_iter)
        if hasattr(result_iter, "close"):
            result_iter.close()
    except Exception:
        _logger.exception("Batch sub-request failed: %s %s", method, path)
        return 500, {"error": "Internal server error"}, {}

    ## Combine bytes from both the write() callable and the iterable.
    write_buf.seek(0)
    write_bytes = write_buf.read()
    response_bytes = write_bytes + iter_bytes if write_bytes else iter_bytes

    status_code = int(captured.get("status", "500").split(" ", 1)[0])

    try:
        response_body = json.loads(response_bytes)
    except (json.JSONDecodeError, ValueError):
        response_body = response_bytes.decode("utf-8", errors="replace")

    ## Collect response headers into a dict, keeping only the
    ## interesting ones (X-* custom headers).
    resp_headers = {}
    for name, value in captured.get("headers", []):
        if name.startswith("X-"):
            resp_headers[name] = value

    return status_code, response_body, resp_headers


def _handle_batch(wsgi_app, environ, start_response):
    """Process a batch request and return aggregated responses."""
    try:
        content_length = int(environ.get("CONTENT_LENGTH", 0) or 0)
        raw_body = environ["wsgi.input"].read(content_length)
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError, KeyError):
        response = Response(
            json.dumps({"error": "Invalid JSON body"}),
            status=400,
            content_type="application/json",
        )
        return response(environ, start_response)

    requests = payload.get("requests")
    if not isinstance(requests, list):
        response = Response(
            json.dumps({"error": "'requests' must be a list"}),
            status=400,
            content_type="application/json",
        )
        return response(environ, start_response)

    responses = []
    for idx, req in enumerate(requests):
        if not isinstance(req, dict) or "path" not in req:
            responses.append({"status": 400, "body": {"error": "Missing 'path'"}})
            continue

        path = req["path"]
        method = req.get("method", "POST").upper()
        params = req.get("params", {})
        body = req.get("body")
        sub_headers = req.get("headers", {})

        status_code, response_body, resp_headers = _dispatch_sub_request(
            wsgi_app,
            environ,
            path,
            method,
            params,
            body,
            headers=sub_headers,
        )
        entry = {"status": status_code, "body": response_body}
        if resp_headers:
            entry["headers"] = resp_headers
        responses.append(entry)

    result = json.dumps({"responses": responses})
    response = Response(result, status=200, content_type="application/json")
    return response(environ, start_response)


##
## CORS Middleware patching
##


def CORSMiddleware(original_app):
    """Add Cross-origin resource sharing headers to every request."""

    ## XXXvlab: There are maybe other ways to ensure that OPTIONS Rest requests
    ## are handled, but this was the shortest way to do without diving
    ## into the actual framework used.

    def __call__(self, environ, start_response):
        def add_cors_headers(status, headers):
            headers = Headers(headers)
            headers.set("Access-Control-Allow-Origin", "*")
            headers.add(
                "Access-Control-Allow-Headers",
                "Origin, Content-Type, accept, *, Cache-Control, Authorization",
            )
            headers.add("Access-Control-Allow-Credentials", "true")
            if not headers.get("Access-Control-Allow-Methods"):
                headers.add(
                    "Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"
                )
            headers.set("Access-Control-Max-Age", "86400")
            # headers.add("Access-Control-Expose-Headers", "")
            return start_response(status, list(headers))

        ## Handle batch requests before normal dispatch.
        if (
            environ.get("PATH_INFO") == BATCH_PATH
            and environ.get("REQUEST_METHOD") == "POST"
        ):
            return _handle_batch(
                lambda sub_env, sub_sr: original_app(self, sub_env, sub_sr),
                environ,
                add_cors_headers,
            )

        if environ.get("REQUEST_METHOD") == "OPTIONS":
            try:
                response = Response(status=200, headers={})
                result = response(environ, add_cors_headers)
            except Exception:
                # _logger.debug(format_last_exception())
                raise
            return result

        try:
            res = original_app(self, environ, add_cors_headers)
        except AccessDenied:
            response = Response(status=401, headers={})
            return response(environ, add_cors_headers)
        except Exception:
            # _logger.debug(format_last_exception())
            raise
        _logger.debug("OK: %r", res)
        return res

    return __call__


root.__class__.__call__ = CORSMiddleware(root.__class__.__call__)


class NewRestApiDispatcher(http.RestApiDispatcher):
    ##
    ## Ensuring that AccessDenied are translated to 401 (Unauthorized) and
    ## not Forbidden.
    ##
    ## That is required for monujo to detect that a re-login would be
    ## welcome (for instance when the API token is not anymore valid).
    ##

    def handle_error(self, exception):
        if isinstance(exception, (MissingError,)):
            extra_info = getattr(exception, "rest_json_info", None) or {}
            extra_info["error"] = exception.args[0]
            return http.wrapJsonException(
                http.NotFound(http.ustr(exception)),
                include_description=True,
                extra_info=extra_info,
            )
        if isinstance(exception, (MissingCommonFeature,)):
            extra_info = getattr(exception, "rest_json_info", None) or {}
            extra_info["error"] = exception.args[0]
            return http.wrapJsonException(
                NotAcceptable(http.ustr(exception)),
                include_description=True,
                extra_info=extra_info,
            )
        if isinstance(exception, (AccessDenied,)):
            extra_info = getattr(exception, "rest_json_info", None)
            return http.wrapJsonException(
                http.Unauthorized(http.ustr(exception)), extra_info=extra_info
            )
        return super().handle_error(exception)

    ##
    ## For querystring parameter when in GET methods, we need to parse the
    ## query string and update the request.params with the parsed values.
    ##
    def pre_dispatch(self, rule, args):
        res = super().pre_dispatch(rule, args)
        if self.request.httprequest.method == "GET":
            self.request.params.update(
                pyquerystring.parse(
                    self.request.httprequest.query_string.decode("utf-8")
                )
            )
        return res


http.RestApiDispatcher = NewRestApiDispatcher
