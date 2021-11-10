from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


class AddressesInfo(Datamodel):
    _name = "comchain.addresses.info"

    partner_id = fields.Integer(required=True, allow_none=False)
    display_name = fields.String(required=True, allow_none=False)


class ComchainPartnersInfo(Datamodel):
    _name = "comchain.partners.info"

    addresses = fields.List(fields.String(), required=True)


class ComchainRegisterInfo(Datamodel):
    _name = "comchain.register.info"

    address = fields.String(required=True)
    wallet = fields.String(required=True)
    message_key = fields.String(required=True)