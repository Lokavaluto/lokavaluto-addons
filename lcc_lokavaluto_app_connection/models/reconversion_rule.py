from odoo import models, fields


class ReconversionRule(models.Model):
    """A recommission rule defines if a wallet can use the reconversion process."""

    _name = "reconversion.rule"

    name = fields.Char("Name")
    active = fields.Boolean(default=True)
    wallet_domain = fields.Char("Wallet Domain")

    is_reconversion_allowed = fields.Boolean("Is Reconversion Allowed?")
