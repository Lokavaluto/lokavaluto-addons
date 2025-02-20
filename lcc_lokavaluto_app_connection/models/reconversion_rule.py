from odoo import models, fields


class ReconversionRule(models.Model):
    """A recommission rule defines if a wallet can use the reconversion process."""

    _name = "reconversion.rule"
    _description = "Define if a user can ask for a reconversion on its wallets."
    _order = "sequence"

    sequence = fields.Integer()
    name = fields.Char("Name")
    active = fields.Boolean(default=True)
    wallet_domain = fields.Char("Wallet Domain")

    is_reconversion_allowed = fields.Boolean("Is Reconversion Allowed?")
