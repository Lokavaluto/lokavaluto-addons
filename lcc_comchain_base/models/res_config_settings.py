from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    comchain_server_url = fields.Char(
        related='company_id.comchain_server_url',
        readonly=False,
        string='Url for comchain serveur'
    )
