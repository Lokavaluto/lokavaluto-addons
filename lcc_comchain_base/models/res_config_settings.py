from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Temporary way to handle only one comchain currency per odoo
    comchain_currency_name = fields.Char(
        related="company_id.comchain_currency_name",
        readonly=False,
        string="Currency Name",
    )
