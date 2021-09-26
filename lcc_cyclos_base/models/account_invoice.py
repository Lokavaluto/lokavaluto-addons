from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    has_numeric_lcc_products = fields.Boolean(string="Has lcc numeric products", compute='_compute_has_numeric_lcc_products', store=True)
    cyclos_amount_credited = fields.Float(string='Cyclos amount credited', track_visibility='always')
    
    @api.one
    @api.depends(
        'state','invoice_line_ids.product_id', 'invoice_line_ids.price_total'
     )
    def _compute_has_numeric_lcc_products(self):
        self.has_numeric_lcc_products = False
        
        categ = self.env.ref('lcc_cyclos_base.product_category_cyclos')
        lcc_numeric_products = self.invoice_line_ids.filtered(lambda line: line.product_id.categ_id == categ)
        if lcc_numeric_products:
            self.has_numeric_lcc_products = True

    @api.multi
    def action_invoice_paid(self):
        super(AccountInvoice, self).action_invoice_paid()
        categ = self.env.ref('lcc_cyclos_base.product_category_cyclos')
        for invoice in self:
            if invoice.state == 'paid' and invoice.has_numeric_lcc_products:
                amount = sum(self.invoice_line_ids.filtered(lambda line: line.product_id.categ_id == categ).mapped('quantity'))
                invoice.partner_id.action_credit_cyclos_account(amount)
                invoice.write({
                    'cyclos_amount_credited': amount,
                    })
