from marshmallow import fields, Schema

from odoo.addons.datamodel.core import Datamodel


class PaymentRequestRecurrentContractItemSchema(Schema):
    sender_wallet_uri = fields.String(required=True, allow_none=False)
    receiver_wallet_uri = fields.String(required=True, allow_none=False)
    amount = fields.Float(required=True, allow_none=False)
    message = fields.String(required=False, allow_none=True)
    date_start = fields.Date(required=True, allow_none=False)
    date_end = fields.Date(required=False, allow_none=True)
    recurring_rule_type = fields.String(required=True, allow_none=False)
    recurring_interval = fields.Integer(required=True, allow_none=False)

class CreatePaymentRequestRecurrentContractsParam(Datamodel):
    _name = "create.payment.request.recurrent.contracts.params"

    currency_uri = fields.String(required=True, allow_none=False)
    creator_wallet_uri = fields.String(required=True, allow_none=False)
    contracts = fields.List(
        fields.Nested(PaymentRequestRecurrentContractItemSchema), required=True, allow_none=False
    )


class ListPaymentRequestRecurrentContractsParams(Datamodel):
    _name = "list.payment.request.recurrent.contracts.params"

    currency_uri = fields.String(required=True, allow_none=False)
    wallet_uri = fields.String(required=True, allow_none=False)
    state = fields.List(fields.String(), required=False, allow_none=True)


class DeletePaymentRequestRecurrentContractsParams(Datamodel):
    _name = "delete.payment.request.recurrent.contracts.params"

    payment_request_ids = fields.List(fields.Integer(), required=True, allow_none=False)
    currency_uri = fields.String(required=True, allow_none=False)
    wallet_uri = fields.String(required=True, allow_none=False)
