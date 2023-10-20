from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Temporary way to handle only one comchain currency per odoo
    comchain_currency_name = fields.Char(
        related="company_id.comchain_currency_name",
        readonly=False,
        string="Currency Name",
    )
    safe_wallet_partner_id = fields.Many2one(
        'res.partner',
        related="company_id.safe_wallet_partner_id",
        readonly=False,
        string='Safe Wallet Partner')
    odoo_wallet_partner_id = fields.Many2one(
        'res.partner',
        related="company_id.odoo_wallet_partner_id",
        readonly=False,
        string="Odoo Wallet Partner")
    comchain_odoo_wallet_password = fields.Char(
        related="company_id.comchain_odoo_wallet_password",
        readonly=False,
        string="Odoo wallet password"
    )
    message_from = fields.Char(
        related="company_id.message_from",
        readonly=False,
        string='Message from')
    message_to = fields.Char(
        related="company_id.message_to",
        readonly=False,
        string='Message to')
