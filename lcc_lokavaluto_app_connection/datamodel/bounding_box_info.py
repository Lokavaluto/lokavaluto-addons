from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


class BoundingBoxInfo(DataModel):
    _name = "bounding.box.info"

    minLat = fields.String(required=True, allow_none=False)
    maxLat = fields.String(required=True, allow_none=False)
    minLon = fields.String(required=True, allow_none=False)
    maxLon = fields.String(required=True, allow_none=False)