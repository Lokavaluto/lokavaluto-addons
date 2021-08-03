from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


class PartnersMapSearchParam(Datamodel):
    _name = "partners.map.search.param"

    bounding_box = fields.NestedModel("bounding.box.info")
    categories = fields.List(fields.String())