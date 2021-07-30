from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


class PartnerIndustry(Datamodel):
    _name = "partner.industry.info"

    ids = fields.List(fields.Integer())#, required=False, nullable=True)


