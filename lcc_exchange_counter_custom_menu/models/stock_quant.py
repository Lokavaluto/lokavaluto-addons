from odoo import models, fields

class StockQuant(models.Model):

    _inherit = "stock.quant"

    note = fields.Text('Note', help="Indiquez ici les modifs de l'ajustement de stock")