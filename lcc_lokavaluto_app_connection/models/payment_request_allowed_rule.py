from odoo import models, fields


class PaymentRequestAllowedRule(models.Model):
    """A payment request allowed rule defines if a wallet
    can create payment requests."""

    _name = "payment.request.allowed.rule"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Payment Request Allowed Rule"
    _order = "sequence"

    name = fields.Char("Name", tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer(tracking=True)
    wallet_domain = fields.Char("Wallet Domain", tracking=True)

    is_payment_request_allowed = fields.Boolean(
        "Is Payment Request Allowed?", tracking=True
    )
