import logging

from odoo.http import root
from odoo.exceptions import AccessDenied
from odoo.addons.base_rest import http
from werkzeug.wrappers import Response
from werkzeug.datastructures import Headers


_logger = logging.getLogger(__name__)

try:
    import pyquerystring
except (ImportError, IOError) as err:
    _logger.debug(err)


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
            # headers.add("Access-Control-Expose-Headers", "")
            return start_response(status, list(headers))

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
        except AccessDenied as e:
            response = Response(status=401, headers={})
            return response(environ, add_cors_headers)
        except Exception as e:
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
