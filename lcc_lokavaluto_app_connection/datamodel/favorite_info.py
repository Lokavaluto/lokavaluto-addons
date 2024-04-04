from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel


class FavoriteInfo(Datamodel):
    _name = "partner.favorite.info"

    is_favorite = fields.Boolean(required=True)
