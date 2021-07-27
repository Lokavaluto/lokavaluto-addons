from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


class PartnerSearchInfo(Datamodel):
    _name = "partner.search.info"

    value = fields.String(required=True, allow_none=False)
    backend_keys = fields.List(fields.String())
    is_favorite = fields.Boolean(requiered=False, allow_none=True)
