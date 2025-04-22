from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel


class PartnerCreditRequestsGetParam(Datamodel):
    _name = "partner.credit.requests.get.param"

    backend_keys = fields.List(fields.String())


class PartnerReconversions(Datamodel):
    _name = "partner.reconversions"

    transactions = fields.List(fields.String())


class PartnerSearchInfo(Datamodel):
    _name = "partner.search.info"

    value = fields.String(required=False, allow_none=True)
    backend_keys = fields.List(fields.String())
    offset = fields.Integer(required=False, allow_none=True)
    limit = fields.Integer(required=False, allow_none=True)
    website_url = fields.String(required=False, allow_none=True)
    order = fields.String(required=False, allow_none=True)
    sender_wallet_ident = fields.String(required=False, allow_none=True)


# Currently the format of sender_wallet_ident, to identify a wallet, is [_CURRENCY_ENGINE]:[_CURRENCY_WALLET_IDENT]
# it corresponds to the field `name` in `res.partner.backend` table.
# Soon it'll be replaced by WALLET_ID :== [_CURRENCY_ENGINE]://[_CURRENCY_IDENT]/wallet/[_CURRENCY_WALLET_IDENT]
# cf https://docs.lokavaluto.fr/o73ElbpVSpWhIxkpiBDmwg#

class PartnerCheckTransaction(Datamodel):
    _name = "partner.check.transaction.get.params"

    sender_wallet_ident = fields.String(required=True, allow_none=False)
    recipient_wallet_ident = fields.String(required=True, allow_none=False)


class PartnerValidateCreditRequest(Datamodel):
    _name = "partner.validate.credit.requests.param"

    ids = fields.List(fields.Integer(), required=True)
