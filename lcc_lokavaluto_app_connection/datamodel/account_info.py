
from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel


class AccountSearchInfo(Datamodel):
    _name = "account.search.info"

    value = fields.String(required=False, allow_none=True)
    backend_keys = fields.List(fields.String())

    offset = fields.Integer(required=False, allow_none=True)
    limit = fields.Integer(required=False, allow_none=True)
    order = fields.String(required=False, allow_nano=True)
