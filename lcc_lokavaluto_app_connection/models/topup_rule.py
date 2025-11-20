from odoo import models, fields


class TopupRule(models.Model):
    """A topup rule defines if a wallet can topup."""

    _name = "topup.rule"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Top Up Rule"
    _order = "sequence"

    name = fields.Char("Name", tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer(tracking=True)
    wallet_domain = fields.Char("Wallet Domain", tracking=True)

    is_topup_allowed = fields.Boolean("Is Topup Allowed?", tracking=True)
