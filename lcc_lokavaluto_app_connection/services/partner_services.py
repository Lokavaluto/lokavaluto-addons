import logging
import re

from odoo.exceptions import (
    AccessDenied,
    MissingError,
)
from odoo.http import request

from odoo.addons.base_rest import restapi
from odoo.addons.base_rest.components.service import to_bool, to_int
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


def _recipient_order_normalize(order):
    """Filters API's order to res.partner.backend order."""
    ORDER_CONV = {
        "name": "partner_public_name",
    }
    new_orders = []
    for order_part in order.split(","):
        _logger.debug(f"order_part: {order_part}")
        olabel_odirection = order_part.strip().split(" ", 1)
        olabel = olabel_odirection[0]
        if olabel not in ORDER_CONV:
            _logger.debug(f"ignore: {olabel}")
            continue  # ignore
        _logger.debug(f"add: {olabel} -> {ORDER_CONV[olabel]}")
        new_orders.append(" ".join([ORDER_CONV[olabel], *olabel_odirection[1:]]))
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
        """This method is used to authenticate and get the token for the user on mobile app."""
        return self.env.user.partner_id.get_partner_wallets_credentials()

    @restapi.method(
        [(["/report-contact-info"], "GET")],
    )
    def report_contact_info(self):
        def contact_info(p):
            res = {
                "name": p.name,
                "street": p.street,
                "street2": p.street2,
                "city": p.city,
                "zip": p.zip,
                "email": p.email,
                "phone": p.phone,
                "mobile": p.mobile,
                "website": p.website,
            }
            if hasattr(p, "logo"):
                res["logo"] = p.logo
            return res

        company_id = self.env.user.company_id
        return {
            "issuer": contact_info(company_id),
            "user": contact_info(self.env.user.partner_id),
        }

    @restapi.method(
        [(["/credit-requests"], "GET")],
        input_param=Datamodel("partner.credit.requests.get.param"),
    )
    def credit_requests(self, partner_credit_requests_get_param):
        ResPartnerBackend = self.env["res.partner.backend"]
        backend_keys = set(self.env.user.partner_id.backends()) & set(
            partner_credit_requests_get_param.backend_keys,
        )
        currency_uris = self._transform_backend_keys_in_currency_uris(backend_keys)

        # Retrieve all the credit requests of the requested currencies
        credit_requests = (
            self.env["credit.request"]
            .sudo()
            .search(
                [
                    ("alt_currency_id.uri", "in", currency_uris),
                    ("state", "in", ["pending"]),
                ],
                order="create_date desc",
            )
        )
        # Retrieve credit requests data
        credit_request_list = [
            self._get_credit_request_data(cr) for cr in credit_requests
        ]
        return credit_request_list

    @restapi.method(
        [(["/pending-topup"], "GET")],
    )
    def pending_topup(self):
        pending_topup_list = []
        backend_keys = request.params["backend_keys"]
        currency_engines = []

        ## Temporary workaround bug of monujo < 1.2.0-rc.2 sending a
        ## wallet internal id (ie: comchain:1f234...7fabb) instead of
        ## a backend internal id (ie: comchain:Lemanopolis).
        supported_backend_keys = self.env.user.partner_id.backends()
        supported_currency_engines = [
            key.split(":", 1)[0] for key in supported_backend_keys
        ]
        cleaned_backend_keys = []
        for backend_key in backend_keys:
            if re.match(r"^(cyclos|comchain):(-?[0-9a-f]{12,})(@.+)?$", backend_key):
                currency_engine = backend_key.split(":")[0]
                if currency_engine in supported_currency_engines:
                    currency_engines.append(currency_engine)
                continue
            cleaned_backend_keys.append(backend_key)
        backend_keys = cleaned_backend_keys
        ## Break of workaround

        backend_keys = set(self.env.user.partner_id.backends()) & set(backend_keys)
        currency_uris = self._transform_backend_keys_in_currency_uris(backend_keys)

        ## Continue the workaround
        currency_uris += [
            cur.uri
            for cur in self.env["res.alt.currency"].search(
                [
                    ("active", "=", True),
                    ("engine", "in", currency_engines),
                ]
            )
        ]
        ## End of the workaround

        wallets = self.env["res.partner.backend"].search(
            [
                ("alt_currency_id.uri", "in", currency_uris),
                ("partner_id.id", "=", self.env.user.partner_id.id),
            ],
        )
        CreditRequestSU = self.env["credit.request"].sudo()
        for wallet in wallets:
            pending_topup_list += [
                self._get_credit_request_data(cr)
                for cr in CreditRequestSU.search(
                    [
                        ("wallet_id", "=", wallet.id),
                        ("state", "in", ["open", "pending", "error"]),
                    ],
                    order="create_date desc",
                )
            ]

        return pending_topup_list

    @restapi.method(
        [(["/remove-pending-topup"], "POST")],
    )
    def remove_pending_topup(self) -> bool:
        try:
            order_id = request.params["order_id"]
        except KeyError:
            msg = "value for 'order_id' not found"
            raise MissingError(msg)
        try:
            int(order_id)
        except ValueError:
            msg = "value for 'order_id' should be an integer"
            raise MissingError(msg)

        credit_ids = self.env["credit.request"].search([("order_id", "=", order_id)])
        if len(credit_ids) == 0:
            msg = f"No top-up found to cancel for given order_id ({order_id!r})"
            raise MissingError(
                msg,
            )
        for credit in credit_ids:
            if (
                credit.requester_id
                and credit.requester_id.id != self.env.user.partner_id.id
            ):
                msg = f"You can not remove credit request {credit.id} as you are not the requester."
                raise AccessDenied(
                    msg,
                )
        credit_ids.sudo().unlink()
        return True

    @restapi.method(
        [(["/can-validate-credit-request"], "GET")],
    )
    def can_validate_credit_request(self) -> bool:
        """Check if the current user has the rights to validate credit requests."""
        return self.env["credit.request"].check_access_rights(
            "write", raise_exception=False
        )

    @restapi.method(
        [(["/validate-credit-request"], "POST")],
        input_param=Datamodel("partner.validate.credit.requests.param"),
    )
    def validate_credit_requests(self, partner_credit_requests_get_param) -> bool:
        request_ids = partner_credit_requests_get_param.ids
        requests = self.env["credit.request"].search([("id", "in", request_ids)])
        requests.validate()
        return True

    @restapi.method(
        [(["/reconversions"], "POST")],
        input_param=Datamodel("partner.reconversions"),
    )
    def reconversions(self, params):
        """Return the reconversions status for transactions matching Odoo debit requests.
        Possible values in the dictionnary: the matching debit_request state
        If no debit request matching the transactions (too many or no requests found), the transaction is not returned.
        """
        txs_list = params.transactions
        res = {}
        DebitRequest = self.env["debit.request"]
        for tx_id in txs_list:
            ## tx_id are expected to be like these:
            ##   cyclos://cyclos.mydomain.org:80/tx/-12039473747344
            ##   comchain://Lemanopolis/tx/0x1234567890abcdef
            ##
            ## Which is BACKEND_ID/tx/TRANSACTION_ID

            m = re.match(
                r"^(?P<engine>[^/:]+)://(?P<ident>[^/]+)/tx/(?P<tx_id>.+)$",
                tx_id,
            )
            if not m:
                _logger.error(f"Invalid transaction id {tx_id}")
                continue
            currency_uri = "{}://{}".format(
                m.group("engine"),
                m.group("ident"),
            )
            backend_tx_id = m.group("tx_id")
            debit_requests = DebitRequest.search(
                [
                    ("alt_currency_id.uri", "=", currency_uri),
                    ("transaction_id", "=", backend_tx_id),
                ],
            )
            if len(debit_requests) != 1:
                _logger.error(
                    f"Impossible to match a debit request for transaction {tx_id}: {len(debit_requests)} requests found",
                )
                continue
            res[tx_id] = debit_requests[0].state
        return res

    @restapi.method(
        [(["/<int:rpid>/get", "/<int:rpid>"], "GET")],
    )
    def get(self, rpid):
        """Return profile information."""
        partners = self.env["res.partner"].search(
            [("active", "=", True), ("id", "=", rpid or self.env.user.partner_id.id)],
        )
        if len(partners) == 0:
            msg = "No partner found - please check your request"
            raise MissingError(msg)
        if not partners[0].public_profile_id:
            msg = "Partner %r (id: %d) doesn't have a public profile"
            raise MissingError(
                msg,
                partners[0].name,
                partners[0].id,
            )

        return partners[0].lcc_profile_info()[0]

    @restapi.method(
        [(["/partner_search", "/search"], "GET")],
        input_param=Datamodel("partner.search.info"),
    )
    def search_recipients(self, recipients_search_info):
        """Search recipients, excluding self and safe wallets."""
        return self._search_recipients_common(
            backend_keys=recipients_search_info.backend_keys,
            value=recipients_search_info.value,
            offset=recipients_search_info.offset,
            limit=recipients_search_info.limit,
            order=recipients_search_info.order,
            website_url=recipients_search_info.website_url,
            sender_wallet_ident=recipients_search_info.sender_wallet_ident,
            apply_restriction_rules=True,
            exclude_safe_wallets=True,
            exclude_self=True,
        )

    @restapi.method(
        [(["/can-search-all-recipients"], "GET")],
    )
    def can_search_all_recipients(self) -> bool:
        """Check if the current user has the rights to search all recipients."""
        return self.env.user.has_group(
            "lcc_lokavaluto_app_connection.group_wallet_accounts_manager"
        )

    @restapi.method(
        [(["/search_all"], "GET")],
        input_param=Datamodel("partner.search.info"),
    )
    def search_all_recipients(self, recipients_search_info):
        """Admin-only search for all recipients, without restrictions."""

        if not self.can_search_all_recipients():
            raise AccessDenied()

        return self._search_recipients_common(
            backend_keys=recipients_search_info.backend_keys,
            value=recipients_search_info.value,
            offset=recipients_search_info.offset,
            limit=recipients_search_info.limit,
            order=recipients_search_info.order,
            website_url=recipients_search_info.website_url,
        )

    @restapi.method(
        [(["/get_recipient_by_uri"], "GET")],
    )
    def search_recipient_by_uri(self):
        """Search recipient by uri."""
        recipient_id = request.params["data"]["rp"]
        backend_keys = set(self.env.user.partner_id.backends()) & set(
            request.params["backend_keys"],
        )
        currency_uris = self._transform_backend_keys_in_currency_uris(backend_keys)
        ## XXXvlab: temporary fix to work with cyclos
        if "@" in request.params["data"]["rpb"]:
            request.params["data"]["rpb"] = request.params["data"]["rpb"].split("@", 1)[
                0
            ]

        domain = [
            ("status", "=", "active"),
            ("alt_currency_id.uri", "in", currency_uris),
            ("partner_id.active", "=", True),
            ("partner_id.is_main_profile", "=", True),  # only main profiles
        ]
        try:
            recipients = self.env["res.partner.backend"].search(
                [
                    ("partner_id.id", "=", recipient_id),
                    ("name", "=", request.params["data"]["rpb"]),
                    *domain,
                ],
            )
        except e:
            msg = "An error occured while searching recipient."
            raise MissingError(msg, e)

        if len(recipients) == 0:
            msg = "No recipient found given partner id."
            raise MissingError(msg)
        if len(recipients) > 1:
            msg = "Too many recipients found given partner id."
            raise MissingError(msg)

        partner = recipients[0].partner_id
        recipient = partner.lcc_profile_info()[0]
        recipient["monujo_backends"] = partner.lcc_backend_ids._update_search_data(
            currency_uris
        )

        return recipient

    @restapi.method(
        [
            (
                [
                    "/pending-wallets",
                ],
                "GET",
            ),
        ],
        input_param=Datamodel("account.search.info"),
    )
    def pending_wallets(self, account_search_info):
        _logger.debug(f"PARAMS: {account_search_info}")
        backend_keys = self.env.user.partner_id.backends() & set(
            account_search_info.backend_keys,
        )
        currency_uris = self._transform_backend_keys_in_currency_uris(backend_keys)
        recipients = self.env["res.partner.backend"].search(
            [
                ("status", "=", "to_confirm"),
                ("alt_currency_id.uri", "in", currency_uris),
            ],
        )

        domain = [("id", "in", recipients.mapped("partner_id.id"))]
        offset = account_search_info.offset or 0
        limit = account_search_info.limit or 0
        order = account_search_info.order
        _logger.debug(f"DOMAIN: {domain}")
        partners = self.env["res.partner"].search(
            domain,
            limit=limit,
            offset=offset,
            order=order,
        )
        _logger.debug(f"partners: {partners}")
        if backend_keys:  # filter out partners not having the queried backends
            partners = partners.filtered(lambda r: r.backends() & set(backend_keys))

        return self._get_formatted_recipients(partners, currency_uris)

    @restapi.method(
        [
            (
                [
                    "/accounts",
                ],
                "GET",
            ),
        ],
        input_param=Datamodel("account.search.info"),
    )
    def old_pending_wallets(self, account_search_info):
        _logger.warning(
            "Deprecated API entrypoint /accounts called (should use /pending-wallets)",
        )
        return self.pending_wallets(account_search_info)

    @restapi.method(
        [(["/<int:id>/favorite/set"], "PUT")],
    )
    def set_favorite(self, _id) -> bool:
        """Set partner as favorite."""
        partner = self._get(_id)
        partner.write({"favorite_user_ids": [(4, self.env.uid)]})
        return True

    @restapi.method(
        [(["/<int:id>/favorite/unset"], "PUT")],
    )
    def unset_favorite(self, _id) -> bool:
        """Unset partner as favorite."""
        partner = self._get(_id)
        partner.write({"favorite_user_ids": [(3, self.env.uid)]})
        return True

    @restapi.method(
        [(["/<int:id>/favorite/toggle"], "PUT")],
    )
    def new_toggle_favorite(self, _id):
        """Toggle partner as favorite/not favorite."""
        partner = self._get(_id)
        if partner.is_favorite:
            return self.unset_favorite(_id)
        return self.set_favorite(_id)

    @restapi.method(
        [(["/is_transaction_allowed"], "GET")],
        input_param=Datamodel("partner.check.transaction.get.params"),
    )
    def is_transaction_allowed(self, partner_is_transaction_allowed_get_params):
        """Check that transaction is allowed between sender and recipient, based on wallet restriction rules."""
        Wallet = self.env["res.partner.backend"]
        sender_wallet = Wallet.get_by_name(
            partner_is_transaction_allowed_get_params.sender_wallet_ident,
        )
        recipient_wallet = Wallet.get_by_name(
            partner_is_transaction_allowed_get_params.recipient_wallet_ident,
        )

        matched_wallet_restriction_rule = (
            sender_wallet.get_first_matching_restriction_rule()
        )
        if matched_wallet_restriction_rule:
            return matched_wallet_restriction_rule.recipient_is_allowed_by_rule(
                recipient_wallet,
            )

        # if no wallet restriction rule matches, all recipients are allowed
        return True

    ##########################################################
    # Private methods
    ##########################################################
    # The following method are 'private' and should be never never NEVER call
    # from the controller.

    def _get(self, _id):
        return self.env["res.partner"].sudo().browse(_id)

    def _search_recipients_common(
        self,
        backend_keys,
        value="",
        offset=0,
        limit=None,
        order="name asc",
        website_url=None,
        sender_wallet_ident=None,
        apply_restriction_rules=False,
        exclude_safe_wallets=False,
        exclude_self=False,
    ):
        """Search recipients by name, email, phone or website_url.

        Resolves backend_keys to currencies, builds the search domain,
        applies value/website_url filters, orders by favorites first,
        and optionally enforces wallet restriction rules.

        XXXvlab: upon empty search string, returns favorites only.
        Always orders by favorite first.
        """
        backend_keys = set(self.env.user.partner_id.backends()) & set(
            backend_keys,
        )
        # Transform backend_keys in backend_URI if needed
        # TO BE REMOVED once Monujo sends URIs through the API
        currency_uris = self._transform_backend_keys_in_currency_uris(backend_keys)
        alt_currency_ids = self.env["res.alt.currency"].search(
            [("uri", "in", currency_uris)],
        )
        domain = [
            ("status", "=", "active"),
            ("alt_currency_id", "in", alt_currency_ids.ids),
            ("partner_id.active", "=", True),
            ("partner_id.public_profile_id.name", "!=", False),  # only main profiles
        ]

        if exclude_self:
            domain += [("partner_id.id", "!=", self.env.user.partner_id.id)]

        if exclude_safe_wallets:
            for alt_currency in alt_currency_ids:
                for safe_wallet_partner in alt_currency._safe_wallet_partners():
                    domain += [("partner_id.id", "!=", safe_wallet_partner.id)]

        offset = offset or 0
        limit = limit or None
        order = _recipient_order_normalize(order or "name asc")

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
                ],
            )
        if website_url:
            partner_id = website_url.split("-")[-1]
            try:
                partner_id = int(partner_id)
                domain.extend([("partner_id.id", "=", partner_id)])
            except ValueError:
                msg = "Url not valid."
                raise MissingError(msg)
        _logger.debug(f"DOMAIN: {domain}")

        ## XXXvlab: as ``is_favorite`` cannot be stored, it can't be used
        ## here for a direct search. We'll implement 2 search to fake an
        ## order by ``is_favorite``
        rpb = self.env["res.partner.backend"].sudo()
        recipients_fav = rpb.search(
            [("partner_id.favorite_user_ids", "in", self.env.uid), *domain],
            limit=limit,
            offset=offset,
            order=order,
        )
        _logger.debug(f"recipients_fav: {recipients_fav}")
        len_recipients = len(recipients_fav)
        recipients = recipients_fav
        if (limit is None or len_recipients < limit) and value:
            if len_recipients == 0:
                fav_count = (
                    0
                    if offset == 0
                    else rpb.search_count(
                        [("partner_id.favorite_user_ids", "in", self.env.uid), *domain],
                    )
                )
                offset -= fav_count
            else:
                if limit is not None:
                    limit -= len_recipients

                offset = 0

            if limit != 0:
                recipients_no_fav = rpb.search(
                    [("partner_id.favorite_user_ids", "not in", self.env.uid), *domain],
                    limit=limit,
                    offset=offset,
                    order=order,
                )
                _logger.debug(f"recipients_no_fav: {recipients_no_fav}")
                recipients |= recipients_no_fav
        _logger.debug(f"recipients: {recipients}")

        if apply_restriction_rules:
            sender_partner = self.env.user.partner_id
            if sender_wallet_ident:
                sender_wallet = rpb.get_by_name(
                    name=sender_wallet_ident,
                )
            else:
                sender_wallet = sender_partner.lcc_backend_ids.filtered(
                    lambda p: p.alt_currency_id.uri in currency_uris
                )
                if len(sender_wallet) > 1:
                    raise MissingError(
                        "Several sender wallets found, only one expected"
                    )

            if (
                sender_wallet
            ):  # notice : bool(self.env["res.partner.backend"]) returns False
                matched_wallet_restriction_rule = (
                    sender_wallet.get_first_matching_restriction_rule()
                )
                if matched_wallet_restriction_rule:
                    recipients = [
                        recipient_wallet
                        for recipient_wallet in recipients
                        if matched_wallet_restriction_rule.recipient_is_allowed_by_rule(
                            recipient_wallet,
                        )
                    ]
                # if no wallet restriction rule matches, all recipients are allowed

        ## Group by partner
        rows = []
        for recipient in recipients:
            partner = recipient.partner_id
            lcc_profile_info = partner.lcc_profile_info()
            if not lcc_profile_info:
                continue
            row = lcc_profile_info[0]
            row["monujo_backends"] = partner.lcc_backend_ids._update_search_data(
                currency_uris
            )
            rows.append(row)

        return {"count": len(rows), "rows": rows}

    def _transform_backend_keys_in_currency_uris(self, backend_keys):
        """
        Transition function to transform backend keys format in backend URI format.
        TO BE REMOVED once Monujo uses backend URIs
        """
        currency_uris = []
        for backend in backend_keys:
            separator_count = backend.count("://")
            if separator_count == 1:
                # backend matches wished URI structure
                currency_uris.append(backend)
            elif separator_count == 0:
                # backend is OLD format
                engine, ident = backend.split(":", 1)
                currency_uris.append(f"{engine}://{ident}")
            else:
                raise MissingError(f"Invalid backend id {backend}")
        return currency_uris

    def _get_formatted_recipients(self, recipients, currency_uris):
        rows = []
        if currency_uris:
            for partner in recipients:
                row = partner.lcc_profile_info()[0]
                row["monujo_backends"] = partner.lcc_backend_ids._update_search_data(
                    currency_uris,
                )
                rows.append(row)
        return {"count": len(rows), "rows": rows}

    def _prepare_params(self, params):
        for key in ["country", "state"]:
            if key in params:
                val = params.pop(key)
                if val.get("id"):
                    params[f"{key}_id"] = val["id"]
        return params

    def _get_credit_request_data(self, cr):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        data = {
            "credit_id": cr.id,
            "order_id": cr.order_id.id if cr.order_id else 0,
            "order_url": base_url + cr.order_id.get_portal_url() if cr.order_id else "",
            "amount": cr.amount,
            "date": int(cr.create_date.timestamp()),
            "name": cr.partner_id.name,
            "monujo_backend": cr.wallet_id.get_wallet_data(),
            "paid": cr.state != "open",
        }

        if cr.requester_id:
            data["requester"] = {"name": cr.requester_id.name, "id": cr.requester_id.id}

        return data

    ##########################################################
    # Request Validators
    ##########################################################
    def _validator_create(self):
        return {
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
        _logger.debug(f"res: {res}")
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
