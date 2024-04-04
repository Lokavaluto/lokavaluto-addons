import json
import logging
import traceback


from odoo.http import root, request
from odoo.exceptions import AccessDenied
from odoo.addons.base_rest.http import HttpRestRequest
from werkzeug.wrappers import Response
from werkzeug.exceptions import BadRequest
from werkzeug.datastructures import Headers


_logger = logging.getLogger(__name__)


try:
    import pyquerystring
except (ImportError, IOError) as err:
    _logger.debug(err)





##
## CORS Middleware patching
##


class CORSMiddleware(object):
    """Add Cross-origin resource sharing headers to every request."""

    ## XXXvlab: There are maybe other ways to ensure that OPTIONS Rest requests
    ## are handled, but this was the shortest way to do without diving
    ## into the actual framework used.

    def __init__(self, app, origin="*"):
        self.app = app
        self.origin = origin

    def __call__(self, environ, start_response):
        def add_cors_headers(status, headers):
            headers = Headers(headers)
            headers.set("Access-Control-Allow-Origin", self.origin)
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
            return start_response(status, headers.to_list())

        if environ.get("REQUEST_METHOD") == "OPTIONS":
            try:
                response = Response(status=200, headers={})
                result = response(environ, add_cors_headers)
            except Exception:
                # _logger.debug(format_last_exception())
                raise
            return result

        try:
            return self.app(environ, add_cors_headers)
        except AccessDenied as e:
            response = Response(status=401, headers={})
            return response(environ, add_cors_headers)


root.dispatch = CORSMiddleware(root.dispatch)


##
## Monkeypatching of HttpRestRequest
##


def __init__(self, httprequest):
    super(HttpRestRequest, self).__init__(httprequest)
    if self.httprequest.method != "GET":
        data = self.httprequest.get_data().decode(self.httprequest.charset)
        _logger.debug("data: %s" % data)
        if not data:
            data = "{}"
        try:
            self.params = json.loads(data)
        except ValueError as e:
            msg = "Invalid JSON data: %s" % str(e)
            _logger.info("%s: %s", self.httprequest.path, msg)
            raise BadRequest(msg)
    else:
        # We reparse the query_string in order to handle data structure
        # more information on https://github.com/aventurella/pyquerystring
        self.params = pyquerystring.parse(self.httprequest.query_string.decode("utf-8"))
    self._determine_context_lang()


def dispatch(self):
    try:
        return super(HttpRestRequest, self).dispatch()
    except Exception as exc:
        return self._handle_exception(exc)


HttpRestRequest.__init__ = __init__
HttpRestRequest.dispatch = dispatch

from odoo.addons.website.models.ir_http import Http


## Patching ``Http``, as both ``_serve_page`` or ``_serve_redirect`` assume
## that ``request.website`` exists and that is not the case.
@classmethod
def _serve_fallback(cls, exception):
    # serve attachment before
    parent = super(Http, cls)._serve_fallback(exception)
    if parent:  # attachment
        return parent

    if getattr(request, "website", False):
        website_page = cls._serve_page()
        if website_page:
            return website_page

        redirect = cls._serve_redirect()
        if redirect:
            return request.redirect(
                _build_url_w_params(redirect.url_to, request.params), code=redirect.type
            )

    return False


Http._serve_fallback = _serve_fallback
