from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


class PartnerUrlSearchInfo(Datamodel):
    _name = "partner.url.search.info"

    url = fields.String(required=True, allow_none=False)
    backend_keys = fields.List(fields.String())
