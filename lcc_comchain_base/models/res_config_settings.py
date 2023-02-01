from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Temporary way to handle only one comchain currency per odoo
    comchain_currency_name = fields.Char(
        related="company_id.comchain_currency_name",
        readonly=False,
        string="Comchain currency name",
    )

    config_comchain_delegated_wallet = fields.Char(
        string='Comchain delegated wallet',
        config_parameter='comchain.delegated_wallet'
    )
    config_comchain_delegated_pwd = fields.Char(
        string='Comchain delegated password',
        config_parameter='comchain.delegated_pwd'
    )
    config_comchain_stock_id = fields.Char(
        string='Comchain stock wallet address',
        config_parameter='comchain.stock_id'
    )
