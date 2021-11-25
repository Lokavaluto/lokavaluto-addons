from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    comchain_server_url = fields.Char(
        related='company_id.comchain_server_url',
        readonly=False,
        string='Url for comchain serveur'
    )

    ## Temporary way to handle only one comchain currency per odoo
    currency_name = fields.Char(
        related='company_id.comchain_currency_name',
        readonly=False,
        string='Currency Name'
    )
