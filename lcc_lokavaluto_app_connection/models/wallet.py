from random import randint

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
import logging


_logger = logging.getLogger(__name__)


class ResPartnerBackend(models.Model):
    """Add backend commom property for local currency"""

    _name = "res.partner.backend"
    _description = (
        "Object in Odoo which match a wallet in a connected transaction backend."
    )

    type = fields.Selection([("foo", "Value defined only for testing purposes")], string="Type", required=True)
    # You can find real type values in lcc_comchain_base and lcc_cyclos_base
    name = fields.Char("Name", required=True)
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
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    is_reconversion_allowed = fields.Boolean(
        "Is Reconversion Allowed?",
        readonly=True,
        compute="_compute_is_reconversion_allowed",
    )
    is_topup_allowed = fields.Boolean(
        "Is Topup Allowed ?",
        readonly=True,
        compute="_compute_is_topup_allowed"
    )
    tag_ids = fields.Many2many("wallet.tag", string="Tags")

    def _update_search_data(self, backend_keys):
        return {}

    @api.depends("name", "type")
    def _compute_status(self):
        pass

    @api.depends("partner_id.public_profile_id", "partner_id.public_profile_id.name")
    def _compute_partner_name(self):
        for record in self:
            if record.partner_id.public_profile_id:
                record.partner_public_name = record.partner_id.public_profile_id.name

    def get_lcc_product(self):
        """Return the numeric lcc product to add in sale orders or invoices.
        Need to be overrided by financial backend add-ons"""
        return None

    @api.model
    def translate_backend_key_in_wallet_name(self, backend_key):
        return backend_key

    @api.model
    def get_wallets(self, backend_keys):
        """Returns wallet objects list matching the backend_keys contents"""
        Wallet = self.env["res.partner.backend"]

        return Wallet.search(
            [
                (
                    "name",
                    "in",
                    [
                        Wallet.translate_backend_key_in_wallet_name(backend_key)
                        for backend_key in backend_keys
                    ],
                )
            ]
        )

    def get_by_name(self, name: str):
        """Returns wallet object matching the name given"""
        ## XXXvlab: temporary hack to make cyclos ident work
        if "@" in name:
            name = name.split("@", 1)[0]
        return self.search([("name", "=", name)])

    def get_wallet_data(self):
        """Returns wallet informations
        Need to be overrided by financial backend add-ons"""
        return []

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
            if self.search(safe_eval(rule.sender_wallet_domain) + [("id", "=", self.id)], limit=1):
                return rule
        return None

    def _compute_is_reconversion_allowed(self):
        all_rules = self.env["reconversion.rule"].search([("active", "=", True)], order="sequence")
        for record in self:
            # By default, reconversion is NOT allowed
            record.is_reconversion_allowed = False
            for rule in all_rules:
                if self.search(safe_eval(rule.wallet_domain or "[]") + [("id", "=", record.id)]):
                    record.is_reconversion_allowed = rule.is_reconversion_allowed
                    # We stop after the first rule matched
                    break

    def _compute_is_topup_allowed(self):
        all_rules = self.env["topup.rule"].search([("active", "=", True)], order="sequence")
        for record in self:
            # By default, topup is allowed
            record.is_topup_allowed = True
            for rule in all_rules:
                if self.search(safe_eval(rule.wallet_domain or "[]") + [("id", "=", record.id)]):
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
    active = fields.Boolean(default=True, help="The active field allows you to hide the category without removing it.")
