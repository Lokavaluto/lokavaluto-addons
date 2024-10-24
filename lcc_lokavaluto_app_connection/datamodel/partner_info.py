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


class PartnerValidateCreditRequest(Datamodel):
    _name = "partner.validate.credit.requests.param"

    ids = fields.List(fields.Integer(), required=True)
