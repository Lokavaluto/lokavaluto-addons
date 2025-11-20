from odoo import models, fields


class ReconversionRule(models.Model):
    """A recommission rule defines if a wallet can use the reconversion process."""

    _name = "reconversion.rule"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Reconversion rule"
    _order = "sequence"

    sequence = fields.Integer(tracking=True)
    name = fields.Char("Name", tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    wallet_domain = fields.Char("Wallet Domain", tracking=True)

    is_reconversion_allowed = fields.Boolean("Is Reconversion Allowed?", tracking=True)
