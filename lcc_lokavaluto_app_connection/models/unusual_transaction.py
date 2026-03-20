import logging

from odoo import api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class UnusualTransaction(models.Model):
    """
    Unusual Transaction table list the transaction performed by the alternative currencies operator
    which are... unusual.

    The aim is to explicit how the transactions should be considered.
    This is useful for statistic dashboards for instance.
    """

    _name = "unusual.transaction"
    _description = "Unusual Transaction"

    tx_hash = fields.Char(string="Transaction Hash", required=True, index=True)
    alt_currency_id = fields.Many2one(
        "res.alt.currency",
        string="Alternative Currency",
        required=True,
    )
    tx_category = fields.Selection(
        [
            ("pledge", "Pledge"),
            ("reconversion", "Reconversion"),
            ("payment", "Payment"),
            ("technical", "Technical"),
            ("error", "Error")
        ],
        string="Transaction Category",
        required=True,
    )
    description = fields.Text(string="Description", required=False)
    expected_sender_wallet_id = fields.Many2one(
        "res.partner.backend",
        string="Expected Sender Wallet",
        domain="[('alt_currency_id', '=', alt_currency_id)]",
    )
    expected_sender_partner_id = fields.Many2one(
        "res.partner",
        string="Expected Sender Partner",
        related="expected_sender_wallet_id.partner_id",
        store=True,
    )
    expected_receiver_wallet_id = fields.Many2one(
        "res.partner.backend",
        string="Expected Receiver Wallet",
        domain="[('alt_currency_id', '=', alt_currency_id)]",
    )
    expected_receiver_partner_id = fields.Many2one(
        "res.partner",
        string="Expected Receiver Partner",
        related="expected_receiver_wallet_id.partner_id",
        store=True,
    )
