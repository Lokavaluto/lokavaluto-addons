from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


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

    address = fields.String(required=True)
    type = fields.Integer(required=True)
    credit_min = fields.Float(required=True)
    credit_max = fields.Float(required=True)
    recipient_id = fields.Integer(required=False)


class ComchainDiscardInfo(Datamodel):
    _name = "comchain.discard.info"

    address = fields.String(required=True)
    recipient_id = fields.Integer(required=True)


class ComchainActivateList(Datamodel):
    _name = "comchain.activate.list"

    accounts = fields.List(NestedModel("comchain.activate.info"), required=True)


class ComchainDiscardList(Datamodel):
    _name = "comchain.discard.list"

    accounts = fields.List(NestedModel("comchain.discard.info"), required=True)


class ComchainAccountInfo(Datamodel):
    _name = "comchain.account"

    partner_id = fields.Integer(required=True)
    name = fields.String(required=True)
    comchain_address = fields.String(required=True)


class ComchainCreditInfo(Datamodel):
    _name = "comchain.credit.info"

    comchain_address = fields.String(required=True)
    amount = fields.Float(required=True)


class ComchainCreditResponse(Datamodel):
    _name = "comchain.credit.response"

    order_url = fields.String(required=True)


class ComchainCreditRequest(Datamodel):
    _name = "comchain.credit.request"

    credit_id = fields.Integer(required=True)
    amount = fields.Float(required=True)
    date = fields.Date(required=True)
    name = fields.String(required=True)
    monujo_backend = fields.List(fields.String(), required=True)
