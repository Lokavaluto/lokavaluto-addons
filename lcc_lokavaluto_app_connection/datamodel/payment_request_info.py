from marshmallow import fields, Schema

from odoo.addons.datamodel.core import Datamodel


class PaymentRequestItemSchema(Schema):
    sender_wallet_uri = fields.String(required=True, allow_none=False)
    receiver_wallet_uri = fields.String(required=True, allow_none=False)
    amount = fields.Float(required=True, allow_none=False)
    message = fields.String(required=False, allow_none=True)


class CreatePaymentRequestParam(Datamodel):
    _name = "create.payment.request.params"

    currency_uri = fields.String(required=True, allow_none=False)
    creator_wallet_uri = fields.String(required=True, allow_none=False)
    requests = fields.List(
        fields.Nested(PaymentRequestItemSchema), required=True, allow_none=False
    )


class ListPaymentRequestsParams(Datamodel):
    _name = "list.payment.requests.params"

    currency_uri = fields.String(required=True, allow_none=False)
    wallet_uri = fields.String(required=True, allow_none=False)
    state = fields.List(fields.String(), required=False, allow_none=True)


class UpdatePaymentRequestParams(Datamodel):
    _name = "update.payment.request.params"

    payment_request_id = fields.Integer(required=True, allow_none=False)
    currency_uri = fields.String(required=True, allow_none=False)
    wallet_uri = fields.String(required=True, allow_none=False)
    status = fields.String(required=True, allow_none=False)
    message = fields.String(required=False, allow_none=True)
