import json
import logging
import traceback


from odoo.http import root
from odoo.addons.base_rest.http import HttpRestRequest
from werkzeug.wrappers import Response
from werkzeug.exceptions import BadRequest
from werkzeug.datastructures import Headers


_logger = logging.getLogger(__name__)


try:
    import pyquerystring
except (ImportError, IOError) as err:
    _logger.debug(err)


def format_last_exception(prefix="  | "):
    """Format the last exception for display it in tests.

    This allows to raise custom exception, without loosing the context of what
    caused the problem in the first place:

    >>> def f():
    ...     raise Exception("Something terrible happened")
    >>> try:  ## doctest: +ELLIPSIS
    ...     f()
    ... except Exception:
    ...     formated_exception = format_last_exception()
    ...     raise ValueError('Oups, an error occured:\\n%s'
    ...         % formated_exception)
    Traceback (most recent call last):
    ...
    ValueError: Oups, an error occured:
      | Traceback (most recent call last):
    ...
      | Exception: Something terrible happened

    """

    return '\n'.join(
        str(prefix + line)
        for line in traceback.format_exc().strip().split('\n'))


##
## CORS Middleware patching
##


class CORSMiddleware(object):
    """Add Cross-origin resource sharing headers to every request.

    """

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
            headers.add("Access-Control-Allow-Headers", 
                    "Origin, Content-Type, accept, *, Cache-Control, Authorization")
            headers.add("Access-Control-Allow-Credentials", "true")
            if not headers.get('Access-Control-Allow-Methods'):
                headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            #headers.add("Access-Control-Expose-Headers", "")
            return start_response(status, headers.to_list())

        if environ.get("REQUEST_METHOD") == "OPTIONS":
            try:
                response = Response(status=200, headers={})
                result = response(environ, add_cors_headers)
            except Exception:
                _logger.debug(format_last_exception())
                raise
            return result

        return self.app(environ, add_cors_headers)

root.dispatch = CORSMiddleware(root.dispatch)


##
## Monkeypatching of HttpRestRequest
##

def __init__(self, httprequest):
    super(HttpRestRequest, self).__init__(httprequest)
    if self.httprequest.method != "GET":
        data = self.httprequest.get_data().decode(self.httprequest.charset)
        _logger.debug('data: %s' % data)
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
        self.params = pyquerystring.parse(
            self.httprequest.query_string.decode("utf-8")
        )
    self._determine_context_lang()


HttpRestRequest.__init__ = __init__
