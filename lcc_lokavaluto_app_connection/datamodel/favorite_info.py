from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


class FavoriteInfo(Datamodel):
    _name = "partner.favorite.info"

    is_favorite = fields.Boolean(required=True)
