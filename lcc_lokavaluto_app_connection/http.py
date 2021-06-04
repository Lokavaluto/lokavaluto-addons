import json
import logging

from odoo.addons.base_rest.http import HttpRestRequest
from werkzeug.exceptions import (
    BadRequest,
)

_logger = logging.getLogger(__name__)

try:
    import pyquerystring
except (ImportError, IOError) as err:
    _logger.debug(err)


def __init__(self, httprequest):
    _logger.debug('data:ICI')
    super(HttpRestRequest, self).__init__(httprequest)
    if self.httprequest.mimetype == "application/json":
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