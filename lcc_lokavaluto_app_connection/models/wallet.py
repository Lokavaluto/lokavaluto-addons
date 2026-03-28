import logging
from random import randint

from odoo import api, fields, models
from odoo.exceptions import MissingError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class ResPartnerBackend(models.Model):
    """Object in Odoo which match a wallet in an alternative currency."""

    _name = "res.partner.backend"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Wallet"

    type = fields.Selection(
        related="alt_currency_id.engine",
        string="Type",
        required=True,
    )

    name = fields.Char("Name", required=True)
    alt_currency_id = fields.Many2one(
        "res.alt.currency",
        string="Currency",
        required=True,
        tracking=True,
    )
    ident = fields.Char("Wallet Ident", store=True, tracking=True)
    uri = fields.Char("Wallet URI", compute="_compute_wallet_uri", store=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    partner_public_name = fields.Char(
        "Partner Public Name",
        store=True,
        compute="_compute_partner_name",
    )
    status = fields.Selection(
        [
            ("inactive", "Inactive"),
            ("to_confirm", "To Confirm"),
            ("active", "Active"),
            ("blocked", "Blocked"),
        ],
        string="Status",
        store=True,
        compute="_compute_status",
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        tracking=True,
    )
    is_reconversion_allowed = fields.Boolean(
        "Is Reconversion Allowed?",
        readonly=True,
        compute="_compute_is_reconversion_allowed",
    )
    is_topup_allowed = fields.Boolean(
        "Is Topup Allowed ?", readonly=True, compute="_compute_is_topup_allowed"
    )
    tag_ids = fields.Many2many("wallet.tag", string="Tags", tracking=True)


    @api.depends("alt_currency_id", "ident")
    def _compute_wallet_uri(self):
        for wallet in self:
            wallet.uri = f"{wallet.alt_currency_id.uri}/wallet/{wallet.ident}"

    def _update_search_data(self, currency_uris):
        # Initiate lists
        data = {}
        currencies = self.env["res.alt.currency"].search(
            [
                ("active", "=", True),
                ("uri", "in", currency_uris)
            ]
        )
        for cur in currencies:
            data[f"{cur.engine}:{cur.ident}"] = []

        # Add backend_uris's data
        for wallet in self:
            cur = wallet.alt_currency_id
            if cur.uri in currency_uris:
                data[f"{cur.engine}:{cur.ident}"].append(wallet.ident)

        return data

    @api.depends("name", "type")
    def _compute_status(self):
        pass

    @api.depends("partner_id.public_profile_id", "partner_id.public_profile_id.name")
    def _compute_partner_name(self):
        for record in self:
            if record.partner_id.public_profile_id:
                record.partner_public_name = record.partner_id.public_profile_id.name

    @api.model_create_multi
    def create(self, vals_list):
        res = super(ResPartnerBackend, self).create(vals_list)
        for wallet in self:
            if wallet.type == "foo":
                wallet.ident = wallet.id
        return res

    def get_by_name(self, name: str):
        """Returns wallet object matching the name given"""
        ## XXXvlab: temporary hack to make cyclos ident work
        if "@" in name:
            name = name.split("@", 1)[0]
        return self.search([("name", "=", name)])

    @api.model
    def get_by_uri(self, wallet_uri):
        """Resolve a wallet URI to a single active wallet record.

        The wallet URI format is
        ``{engine}://{currency_ident}/wallet/{wallet_ident}``.

        Args:
            wallet_uri: full wallet URI string.

        Returns:
            Single ``res.partner.backend`` record.

        Raises:
            odoo.exceptions.MissingError: if no active wallet
                matches the URI.
        """
        wallet = self.search(
            [
                ("uri", "=", wallet_uri),
                ("active", "=", True),
                ("status", "=", "active"),
            ]
        )
        if not wallet:
            raise MissingError(f"Wallet not found for URI '{wallet_uri}'")
        return wallet

    def get_auth_context(self):
        """Return backend-specific auth enrichment data for this wallet.

        Called after structural checks (currency exists, caller owns
        an active wallet) have passed.  The caller's existence is
        already proven — this method only adds backend-specific data.

        Override in financial backend add-ons to populate
        backend-namespaced keys (e.g. ``comchain_perms``).
        Values MUST be tuples (not sets) because Odoo may serialize
        ``env.context`` in RPC/caching paths.

        Returns:
            dict: empty in base, enriched by backend overrides.
        """
        self.ensure_one()
        return {}

    def get_authorized_actions(self):
        """Return coarse-grained actions available to the caller.

        Actions are the interface between the generic currency service
        and backend-specific permission systems.  Valid actions:

        - ``validate-credit-request``
        - ``search-all-recipients``
        - ``activate``

        Override in financial backend add-ons to read
        backend-namespaced keys from ``self.env.context`` and map
        them to action strings.

        Returns:
            list: sorted action strings.  Empty in base.
        """
        self.ensure_one()
        return []

    def get_wallet_data(self):
        """Returns wallet informations
        Need to be overrided by financial backend add-ons"""
        return []

    def get_wallet_json_data(self):
        """Returns normalized wallet data in JSON.
        By default, and if no wallet in self, only return alt_currency json data.
        Need to be overrided by financial backend add-ons."""
        data = self.alt_currency_id.get_currency_json_data()
        if self.type == "foo":
            data["accounts"].append(
                {
                    "wallet_uri": self.uri,
                    "active": self.status == "active",
                    "is_topup_allowed": self.is_topup_allowed,
                }
            )
        return data

    def credit_wallet(self, amount):
        """Send credit request to the financial backend"""
        res = {
            "success": False,
            "response": "Nothing done - Please install financial backend Odoo add-on.",
        }
        return res

    def get_wallet_balance(self):
        """Returns wallet balance
        Need to be overrided by financial backend add-ons"""
        res = {
            "success": False,
            "response": "No data - Please install financial backend Odoo add-on.",
        }
        return res

    def get_wallet_commission_rule(self):
        self.ensure_one()
        rules = self.env["commission.rule"].search(
            [("active", "=", True)], order="sequence"
        )
        return next(
            (
                rule
                for rule in rules
                if self.search(safe_eval(rule.wallet_domain) + [("id", "=", self.id)])
            ),
            None,
        )

    def get_first_matching_restriction_rule(self):
        self.ensure_one()
        rules = self.env["wallet.restriction.rule"].search(
            [("active", "=", True)], order="sequence"
        )
        for rule in rules:
            if not rule.sender_wallet_domain:  # it means all senders are concerned
                return rule
            domain = safe_eval(rule.sender_wallet_domain) + [("id", "=", self.id)]
            if self.search(domain, limit=1):
                return rule
        return None

    def _compute_is_reconversion_allowed(self):
        all_rules = self.env["reconversion.rule"].search(
            [("active", "=", True)], order="sequence"
        )
        for record in self:
            # By default, reconversion is NOT allowed
            record.is_reconversion_allowed = False
            for rule in all_rules:
                if self.search(
                    safe_eval(rule.wallet_domain or "[]") + [("id", "=", record.id)]
                ):
                    record.is_reconversion_allowed = rule.is_reconversion_allowed
                    # We stop after the first rule matched
                    break

    def _compute_is_topup_allowed(self):
        all_rules = self.env["topup.rule"].search(
            [("active", "=", True)], order="sequence"
        )
        for record in self:
            # By default, topup is allowed
            record.is_topup_allowed = True
            for rule in all_rules:
                if self.search(
                    safe_eval(rule.wallet_domain or "[]") + [("id", "=", record.id)]
                ):
                    record.is_topup_allowed = rule.is_topup_allowed
                    # We stop after the first rule matched
                    break


class WalletTag(models.Model):
    _description = "Wallet Tags"
    _name = "wallet.tag"
    _order = "name"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string="Tag Name", required=True, translate=True)
    color = fields.Integer(string="Color", default=_get_default_color)
    active = fields.Boolean(
        default=True,
        help="The active field allows you to hide the category without removing it.",
    )
