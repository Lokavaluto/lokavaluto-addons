from odoo import models, fields, api
from odoo.tools.translate import _

class exchange_counters_inventory(models.Model):
    _name = 'exchangecounters.inventory'
    _description = "MLCC Counter Inventory"
    _inherits = {'stock.inventory': 'stock_inventory_id'}

    counter_id = fields.Many2one(
        'exchangecounters.confi',
        string=_("Counter ID"),
        required=False,
        translate=False,
        readonly=False,
    )

    def action_validate(self):
        if not self.exists():
            return
        self.ensure_one()
        if not self.user_has_groups('lcc_exchange_counters.group_exchange_counters_user'):
            raise UserError(_("Only a exchange counter user can validate its inventory adjustment."))
        if self.state != 'confirm':
            raise UserError(_(
                "You can't validate the inventory '%s', maybe this inventory " +
                "has been already validated or isn't ready.") % (self.name))
        inventory_lines = self.line_ids.filtered(lambda l: l.product_id.tracking in ['lot', 'serial'] and not l.prod_lot_id and l.theoretical_qty != l.product_qty)
        lines = self.line_ids.filtered(lambda l: float_compare(l.product_qty, 1, precision_rounding=l.product_uom_id.rounding) > 0 and l.product_id.tracking == 'serial' and l.prod_lot_id)
        if inventory_lines and not lines:
            wiz_lines = [(0, 0, {'product_id': product.id, 'tracking': product.tracking}) for product in inventory_lines.mapped('product_id')]
            wiz = self.env['stock.track.confirmation'].create({'inventory_id': self.id, 'tracking_line_ids': wiz_lines})
            return {
                'name': _('Tracked Products in Inventory Adjustment'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'stock.track.confirmation',
                'target': 'new',
                'res_id': wiz.id,
            }
        self._action_done()
        self.line_ids._check_company()
        self._check_company()
        return True