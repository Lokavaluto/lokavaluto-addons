from odoo import models, fields

class StockLocation(models.Model):

    _inherit = "stock.location"

    pos_id = fields.Many2one("pos.config", string="Related Point of sale")