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


class ComchainActivateInfo(Datamodel):
    _name = "comchain.activate.info"

    partner_id = fields.Integer(required=True)
    type = fields.Integer(required=True)
    credit_min = fields.Float(required=True)
    credit_max = fields.Float(required=True)


class ComchainActivateList(Datamodel):
    _name = "comchain.activate.list"

    accounts = fields.List(NestedModel('comchain.activate.info'), required=True)


class ComchainAccountInfo(Datamodel):
    _name = "comchain.account"

    partner_id = fields.Integer(required=True)
    name = fields.String(required=True)
    comchain_address = fields.String(required=True)
