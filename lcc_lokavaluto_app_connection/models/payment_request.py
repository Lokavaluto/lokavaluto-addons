from odoo import api, fields, models


class PaymentRequest(models.Model):
    """
    Represents the request of a user to transfer alternative currency to another user.

    It can be created by the future sender OR the future receiver of the payment.
   IIts purpose is to track the payment process.
    """

    _sql_constraints = [
        (
            "transaction_id_uniq",
            "unique(transaction_id)",
            "Transaction ID must be unique, a request already exists with this transaction ID!",
        ),
    ]

    _name = "payment.request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Payment request"

    alt_currency_id = fields.Many2one(
        "res.alt.currency",
        string="Currency",
        required=True,
        tracking=True,
    )
    amount = fields.Float("Amount", required=True, tracking=True)
    creator_wallet_id = fields.Many2one(
        "res.partner.backend",
        string="Created by Wallet",
        required=True,
        tracking=True,
    )
    creator_partner_id = fields.Many2one(
        "res.partner",
        related="creator_wallet_id.partner_id",
    )
    sender_wallet_id = fields.Many2one(
        "res.partner.backend",
        string="Sender Wallet",
        required=True,
        tracking=True,
    )
    sender_partner_id = fields.Many2one(
        "res.partner",
        related="sender_wallet_id.partner_id",
    )
    receiver_wallet_id = fields.Many2one(
        "res.partner.backend",
        string="Receiver Wallet",
        required=True,
        tracking=True,
    )
    receiver_partner_id = fields.Many2one(
        "res.partner",
        related="receiver_wallet_id.partner_id",
    )

    state = fields.Selection(
        [
            ("open", "Open"),  # request created
            ("paid", "Paid"),  # payment has been executed
            ("cancelled", "Cancelled"),  # payment request cancelled
            ("refused", "Refused"),  # payment request refused by the sender
        ],
        required=True,
        string="State",
        default="open",
        tracking=True,
    )
    message = fields.Char("Message", tracking=True)
    tx_id = fields.Char("Transaction ID", tracking=True)
    refusal_reason = fields.Char("Refusal Reason", tracking=True)

    recurrent_contract_id = fields.Many2one(
        "payment.request.recurrent.contract",
        string="Recurrent Contract",
        ondelete="set null",
        index=True,
        help="The recurrent contract that generated this payment request",
    )
