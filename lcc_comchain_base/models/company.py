from odoo import models, fields, api


class Company(models.Model):
    _inherit = "res.company"

    @api.model
    def _default_messages(self):
        message = "Top-up from " + str(self.name)
        return message

    comchain_currency_name = fields.Char(string="Currency name")
    activate_automatic_topup = fields.Boolean("Activate Automatic Topup")
    safe_wallet_partner_id = fields.Many2one(
        "res.partner", string="Safe Wallet Partner"
    )
    odoo_wallet_partner_id = fields.Many2one(
        "res.partner", string="Odoo Wallet Partner"
    )
    comchain_odoo_wallet_password = fields.Char(string="Odoo wallet password")
    message_from = fields.Char("Message from", default=_default_messages)
    message_to = fields.Char("Message to", default=_default_messages)
