from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    note = fields.Text("Note", help="Indiquez ici les modifs de l'ajustement de stock")

    @api.model
    def _get_inventory_fields_write(self):
        """Returns a list of fields user can edit when editing a quant in `inventory_mode`."""
        res = super()._get_inventory_fields_write()
        res += ["note"]
        return ress
