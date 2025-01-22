from odoo import models, fields


class TopupRule(models.Model):
    """A topup rule defines if a wallet can topup."""

    _name = "topup.rule"
    _description = "Define if a user can topup on its wallets."
    _order = "sequence"

    name = fields.Char("Name")
    active = fields.Boolean(default=True)
    sequence = fields.Integer()
    wallet_domain = fields.Char("Wallet Domain")

    is_topup_allowed = fields.Boolean("Is Topup Allowed?")
