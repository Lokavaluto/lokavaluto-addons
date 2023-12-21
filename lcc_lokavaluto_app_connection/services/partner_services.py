import logging
from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.base_rest.components.service import to_bool, to_int
from odoo.addons.component.core import Component
from odoo.http import request
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)

_logger = logging.getLogger(__name__)


def _recipient_order_normalize(order):
    """Filters API's order to res.partner.backend order"""
    ORDER_CONV = {
        "name": "partner_public_name",
    }
    new_orders = []
    for order_part in order.split(","):
        _logger.debug("order_part: %s" % order_part)
        olabel_odirection = order_part.strip().split(" ", 1)
        olabel = olabel_odirection[0]
        if olabel not in ORDER_CONV:
            _logger.debug("ignore: %s" % olabel)
            continue  ## ignore
        _logger.debug("add: %s -> %s" % (olabel, ORDER_CONV[olabel]))
        new_orders.append(" ".join(([ORDER_CONV[olabel]] + olabel_odirection[1:])))
    return ", ".join(new_orders)


class PartnerService(Component):
    _inherit = "base.rest.service"
    _name = "partner.service"
    _usage = "partner"
    _collection = "lokavaluto.private.services"
    _description = """
        Partner Services
        Access to the partner services is only allowed to authenticated users.
        If you are not authenticated go to <a href='/web/login'>Login</a>
    """

    def backend_credentials(self):
        """
        This method is used to authenticate and get the token for the user on mobile app.
        """
        partner = self.env.user.partner_id
        response = self._get_backend_credentials(partner)
        return response

    @restapi.method(
        [(["/credit-requests"], "GET")],
        input_param=Datamodel("partner.credit.requests.get.param"),
    )
    def credit_requests(self, partner_credit_requests_get_param):
        credit_request_list = []
        backend_types = []
        for backend_key in partner_credit_requests_get_param.backend_keys:
            backend_types.append(
                self.env["res.partner.backend"].translate_backend_key_in_wallet_name(
                    backend_key
                )
            )
        wallets = self.env["res.partner.backend"].search(
            [("type", "in", backend_types)]
        )
        for wallet in wallets:
            credit_request_list += self._get_credit_requests(
                wallet, ["pending", "error"]
            )
        return credit_request_list

    @restapi.method(
        [(["/pending-topup"], "GET")],
    )
    def pending_topup(self):
        pending_topup_list = []
        wallets = self.env["res.partner.backend"].get_wallets(
            request.params["backend_keys"]
        )
        for wallet in wallets:
            pending_topup_list += self._get_credit_requests(
                wallet, ["open", "pending", "error"]
            )
        return pending_topup_list

    @restapi.method(
        [(["/remove-pending-topup"], "POST")],
    )
    def remove_pending_topup(self):
        try:
            order_id = request.params["order_id"]
        except KeyError:
            raise MissingError("value for 'order_id' not found")
        try:
            top_up_id = int(order_id)
        except ValueError:
            raise MissingError("value for 'order_id' should be an integer")

        credit_ids = self.env["credit.request"].search([("order_id", "=", order_id)])
        if len(credit_ids) == 0:
            raise MissingError(
                "No top-up found to cancel for given order_id (%r)" % order_id
            )
        credit_ids.sudo().unlink()
        return True

    @restapi.method(
        [(["/validate-credit-request"], "POST")],
        input_param=Datamodel("partner.validate.credit.requests.param"),
    )
    def validate_credit_requests(self, partner_credit_requests_get_param):
        request_ids = partner_credit_requests_get_param.ids
        requests = self.env["credit.request"].search([("id", "in", request_ids)])
        requests.validate()
        return True

    @restapi.method(
        [(["/<int:rpid>/get", "/<int:rpid>"], "GET")],
    )
    def get(self, rpid):
        """Return profile information"""
        partners = self.env["res.partner"].search(
            [("active", "=", True), ("id", "=", rpid or self.env.user.partner_id.id)]
        )
        if len(partners) == 0:
            raise MissingError("No partner found - please check your request")
        if not partners[0].public_profile_id:
            raise MissingError(
                "Partner %r (id: %d) doesn't have a public profile",
                partners[0].name, partners[0].id
            )

        return partners[0].lcc_profile_info()[0]

    @restapi.method(
        [(["/partner_search", "/search"], "GET")],
        input_param=Datamodel("partner.search.info"),
    )
    def search_recipients(self, recipients_search_info):
        """
        Search recipients by name, email or phone
        website_url: we can search we url of the web site if needed

        XXXvlab: upon empty search string, returns all favorite only. And
        always order by favorite first.

        """
        _logger.debug("PARAMS: %s" % recipients_search_info)
        value = recipients_search_info.value
        backend_keys = set(self.env.user.partner_id.backends()) & set(
            recipients_search_info.backend_keys
        )

        backend_types = [key.split(":", 1)[0] for key in backend_keys]

        domain = [
            ("status", "=", "active"),
            ("type", "in", backend_types),
            ("partner_id.id", "!=", self.env.user.partner_id.id),
            ("partner_id.active", "=", True),
            ("partner_id.public_profile_id.name", "!=", False),  ## only main profiles
        ]
        offset = recipients_search_info.offset if recipients_search_info.offset else 0
        limit = recipients_search_info.limit if recipients_search_info.limit else None
        order = (
            recipients_search_info.order if recipients_search_info.order else "name asc"
        )
        order = _recipient_order_normalize(order)
        website_url = recipients_search_info.website_url
        if value:
            domain.extend(
                [
                    "|",
                    "|",
                    "|",
                    "|",
                    "|",
                    "|",
                    "|",
                    ("partner_id.public_profile_id.name", "ilike", value),
                    ("partner_id.public_profile_id.business_name", "ilike", value),
                    ("partner_id.public_profile_id.email", "ilike", value),
                    ("partner_id.public_profile_id.phone", "ilike", value),
                    ("partner_id.public_profile_id.mobile", "ilike", value),
                    ("partner_id.industry_id", "ilike", value),
                    ("partner_id.secondary_industry_ids.name", "ilike", value),
                    ("partner_id.keywords", "ilike", value),
                ]
            )
        if website_url:
            partner_id = website_url.split("-")[-1]
            try:
                partner_id = int(partner_id)
                domain.extend([("partner_id.id", "=", partner_id)])
            except ValueError:
                raise MissingError("Url not valid.")
        _logger.debug("DOMAIN: %s" % domain)
        ## XXXvlab: as ``is_favorite`` cannot be stored, it can't be used
        ## here for a direct search. We'll implement 2 search to fake an
        ## order by ``is_favorite``
        recipients_fav = self.env["res.partner.backend"].search(
            [
                ("partner_id.favorite_user_ids", "in", self.env.uid),
            ]
            + domain,
            limit=limit,
            offset=offset,
            order=order,
        )
        _logger.debug("recipients_fav: %s" % recipients_fav)
        len_recipients = len(recipients_fav)
        recipients = recipients_fav
        if (limit is None or len_recipients < limit) and value:
            if len_recipients == 0:
                fav_count = (
                    0
                    if offset == 0
                    else self.env["res.partner.backend"].search_count(
                        [
                            ("partner_id.favorite_user_ids", "in", self.env.uid),
                        ]
                        + domain,
                    )
                )
                offset -= fav_count
            else:
                if limit is not None:
                    limit -= len_recipients

                offset = 0

            if limit != 0:
                recipients_no_fav = self.env["res.partner.backend"].search(
                    [
                        ("partner_id.favorite_user_ids", "not in", self.env.uid),
                    ]
                    + domain,
                    limit=limit,
                    offset=offset,
                    order=order,
                )
                _logger.debug("recipients_no_fav: %s" % recipients_no_fav)
                recipients |= recipients_no_fav
        _logger.debug("recipients: %s" % recipients)

        ## Group by partner
        rows = []
        for recipient in recipients:
            partner = recipient.partner_id
            lcc_profile_info = partner.lcc_profile_info()
            if not lcc_profile_info:
                continue
            row = lcc_profile_info[0]
            row["monujo_backends"] = self._update_search_data(
                partner,
                [k for k in backend_keys if k.startswith("%s:" % recipient.type)],
            )
            rows.append(row)

        return {"count": len(rows), "rows": rows}

    @restapi.method(
        [(["/get_recipient_by_uri"], "GET")],
    )
    def search_recipient_by_uri(self):
        """
        Search recipient by uri

        """
        recipient_id = request.params["data"]["rp"]
        backend_keys = set(self.env.user.partner_id.backends()) & set(
            request.params["backend_keys"]
        )

        backend_types = [key.split(":", 1)[0] for key in backend_keys]
        domain = [
            ("status", "=", "active"),
            ("type", "in", backend_types),
            ("partner_id.active", "=", True),
            ("partner_id.is_main_profile", "=", True),  ## only main profiles
        ]
        try:
            recipients = self.env["res.partner.backend"].search(
                [
                    ("partner_id.id", "=", recipient_id),
                    ("name", "=", request.params["data"]["rpb"]),
                ]
                + domain
            )
        except e:
            raise MissingError("An error occured while searching recipient.", e)

        if len(recipients) == 0:
            raise MissingError("No recipient found given partner id.")
        elif len(recipients) > 1:
            raise MissingError("Too many recipients found given partner id.")

        partner = recipients[0].partner_id
        recipient = partner.lcc_profile_info()[0]
        recipient["monujo_backends"] = self._update_search_data(
            partner,
            [k for k in backend_keys if k.startswith("%s:" % recipients[0].type)],
        )

        return recipient

    @restapi.method(
        [
            (
                [
                    "/accounts",
                ],
                "GET",
            )
        ],
        input_param=Datamodel("account.search.info"),
    )
    def search_accounts(self, account_search_info):
        _logger.debug("PARAMS: %s" % account_search_info)
        backend_keys = self.env.user.partner_id.backends() & set(
            account_search_info.backend_keys
        )

        ## XXXvlab: big ugly shortcut
        backend_types = [key.split(":", 1)[0] for key in backend_keys]

        recipients = self.env["res.partner.backend"].search(
            [("status", "=", "to_confirm"), ("type", "in", backend_types)]
        )

        domain = [("id", "in", recipients.mapped("partner_id.id"))]
        offset = account_search_info.offset if account_search_info.offset else 0
        limit = account_search_info.limit if account_search_info.limit else 0
        order = account_search_info.order
        _logger.debug("DOMAIN: %s" % domain)
        partners = self.env["res.partner"].search(
            domain, limit=limit, offset=offset, order=order
        )
        _logger.debug("partners: %s" % partners)
        if backend_keys:  ## filter out partners not having the queried backends
            partners = partners.filtered(lambda r: r.backends() & set(backend_keys))

        return self._get_formatted_recipients(partners, backend_keys)

    @restapi.method(
        [(["/<int:id>/favorite/set"], "PUT")],
    )
    def set_favorite(self, _id):
        """
        Set partner as favorite
        """
        partner = self._get(_id)
        partner.write(
            {
                "is_favorite": True,
            }
        )
        return {}

    @restapi.method(
        [(["/<int:id>/favorite/unset"], "PUT")],
    )
    def unset_favorite(self, _id):
        """
        Unset partner as favorite
        """
        partner = self._get(_id)
        partner.write(
            {
                "is_favorite": False,
            }
        )
        return {}

    @restapi.method(
        [(["/<int:id>/favorite/toggle"], "PUT")],
    )
    def new_toggle_favorite(self, _id):
        """
        Toggle partner as favorite/not favorite
        """
        partner = self._get(_id)
        if partner.is_favorite:
            return self.unset_favorite(_id)
        else:
            return self.set_favorite(_id)

    ##########################################################
    # Private methods
    ##########################################################
    # The following method are 'private' and should be never never NEVER call
    # from the controller.

    def _get(self, _id):
        return self.env["res.partner"].browse(_id)

    def _get_formatted_recipients(self, recipients, backend_keys):
        rows = []
        if backend_keys:
            for partner in recipients:
                row = partner.lcc_profile_info()[0]
                row["monujo_backends"] = partner._update_search_data(backend_keys)
                rows.append(row)
        return {"count": len(rows), "rows": rows}

    def _prepare_params(self, params):
        for key in ["country", "state"]:
            if key in params:
                val = params.pop(key)
                if val.get("id"):
                    params["%s_id" % key] = val["id"]
        return params

    def _update_search_data(self, partner, backend_keys):
        return {}

    def _get_backend_credentials(self, partner):
        return []

    def _get_credit_requests(self, wallet, status):
        """Return data on all the opened requests of the wallets"""
        CreditRequestSU = self.env["credit.request"].sudo()
        return [
            self._get_credit_request_data(cr)
            for cr in CreditRequestSU.search(
                [("wallet_id", "=", wallet.id), ("state", "in", status)],
                order="create_date desc",
            )
        ]

    def _get_credit_request_data(self, cr):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return {
            "credit_id": cr.id,
            "order_id": cr.order_id.id if cr.order_id else 0,
            "order_url": base_url + cr.order_id.get_portal_url() if cr.order_id else "",
            "amount": cr.amount,
            "date": int(cr.create_date.timestamp()),
            "name": cr.partner_id.name,
            "monujo_backend": cr.wallet_id.get_wallet_data(),
            "paid": cr.state != "open",
        }

    ##########################################################
    # Request Validators
    ##########################################################
    def _validator_create(self):
        res = {
            "name": {"type": "string", "required": True, "empty": False},
            "street": {"type": "string", "nullable": True, "empty": True},
            "street2": {"type": "string", "nullable": True},
            "zip": {"type": "string", "nullable": True, "empty": True},
            "city": {"type": "string", "nullable": True, "empty": True},
            "phone": {"type": "string", "nullable": True, "empty": True},
            "mobile": {"type": "string", "nullable": True, "empty": True},
            "email": {"type": "string", "nullable": True, "empty": True},
            "state": {
                "type": "dict",
                "schema": {
                    "id": {"type": "integer", "coerce": to_int, "nullable": True},
                    "name": {"type": "string"},
                },
            },
            "country": {
                "type": "dict",
                "schema": {
                    "id": {
                        "type": "integer",
                        "coerce": to_int,
                        "required": True,
                        "nullable": False,
                    },
                    "name": {"type": "string"},
                },
            },
            "is_company": {"coerce": to_bool, "type": "boolean"},
            "is_favorite": {"coerce": to_bool, "type": "boolean"},
            "monujo_backends": {"type": "dict"},
        }
        return res

    def _validator_update(self):
        res = self._validator_create()
        for key in res:
            if "required" in res[key]:
                del res[key]["required"]
        return res

    def _validator_search(self):
        return {
            "value": {"type": "string", "nullable": False, "required": True},
            "backend_keys": {
                "type": "list",
                "nullable": True,
                "required": False,
                "empty": True,
                "schema": {"type": "string"},  # , "nullable": False, "required": False}
            },
        }

    def _validator_return_create(self):
        return self._validator_return_get()

    def _validator_return_update(self):
        return self._validator_return_get()

    def _validator_return_search(self):
        return self._validator_return_partners()

    def _validator_return_get(self):
        res = self._validator_create()
        _logger.debug("res: %s" % res)
        res.update({"id": {"type": "integer", "required": True, "empty": False}})
        return res

    def _validator_return_partners(self):
        return {
            "count": {"type": "integer", "required": True},
            "rows": {
                "type": "list",
                "required": True,
                "schema": {"type": "dict", "schema": self._validator_return_get()},
            },
        }

    def _validator_return_favorite(self):
        return self._validator_return_partners()

    def _validator_return_toggle_favorite(self):
        res = self._validator_create()
        res.update({"id": {"type": "integer", "required": True, "empty": False}})
        return res
