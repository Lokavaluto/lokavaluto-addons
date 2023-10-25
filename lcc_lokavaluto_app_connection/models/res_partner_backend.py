from odoo import models, fields, api
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class ResPartnerBackend(models.Model):
    """Add backend commom property for local currency"""

    _name = "res.partner.backend"

    type = fields.Selection([], string="Type", required=True)
    name = fields.Char("Name", required=True)
    active = fields.Boolean(default=True, track_visibility="always")
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
        track_visibility="always",
    )
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)

    @api.depends("name", "type")
    def _compute_status(self):
        pass

    @api.depends("partner_id.public_profile_id", "partner_id.public_profile_id.name")
    def _compute_partner_name(self):
        for record in self:
            if record.partner_id.public_profile_id:
                record.partner_public_name = record.partner_id.public_profile_id.name

    @api.multi
    def unlink(self):
        raise UserError("You can't delete a numeric wallet. Please archive it instead.")

    def get_lcc_product(self):
        """Return the numeric lcc product to add in sale orders or invoices.
        Need to be overrided by financial backend add-ons"""
        return None

    def get_wallet_data(self):
        """Returns wallet informations
        Need to be overrided by financial backend add-ons"""
        return []

    def credit_wallet(self):
        """Send credit request to the financial backend"""
        res = {
            "success": False,
            "response": "Nothing done - Please install financial backend Odoo add-on.",
        }
        return res

    def get_pending_credit_requests(self):
        """Return data on all the pending requests of the wallets"""
        CreditRequestSU = self.env["credit.request"].sudo()
        return [
            cr.get_credit_request_data()
            for wallet in self
            for cr in CreditRequestSU.search(
                [("wallet_id", "=", wallet.id), ("state", "in", ["pending", "error"])]
            )
        ]
