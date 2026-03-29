from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel


class WalletUpdate(Datamodel):
    _name = "wallet.update"

    data = fields.Dict(required=True)
