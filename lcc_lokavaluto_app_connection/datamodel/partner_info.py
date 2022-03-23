from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel
from odoo.addons.datamodel.fields import NestedModel


class PartnerInfoGetParam(Datamodel):
    _name = "partner.info.get.param"

    website_url = fields.String(required=False, allow_none=True)
    backend_keys = fields.List(fields.String())


class PartnerCreditRequestsGetParam(Datamodel):
    _name = "partner.credit.requests.get.param"

    backend_keys = fields.List(fields.String())


class PartnerSearchInfo(Datamodel):
    _name = "partner.search.info"

    value = fields.String(required=False, allow_none=True)
    backend_keys = fields.List(fields.String())
    offset = fields.Integer(required=False, allow_none=True)
    limit = fields.Integer(required=False, allow_none=True)
    website_url = fields.String(required=False, allow_none=True)
    order = fields.String(required=False, allow_nano=True)


class PartnerCreditRequest(Datamodel):
    _name = "partner.credit.request"

    credit_id = fields.Integer(required=True)
    amount = fields.Float(required=True)
    date = fields.Date(required=True)
    name = fields.String(required=True)
    monujo_backend = fields.List(fields.String(), required=True)


class PartnerValidateCreditRequest(Datamodel):
    _name = "partner.validate.credit.requests.param"

    ids = fields.List(fields.Integer(), required=True)
