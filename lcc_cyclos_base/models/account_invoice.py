from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    cyclos_amount_credited = fields.Float(
        string="Cyclos amount credited", track_visibility="always"
    )

    @api.multi
    def action_invoice_paid(self):
        super(AccountInvoice, self).action_invoice_paid()
        categ = self.env.ref("lcc_cyclos_base.product_category_cyclos")
        for invoice in self:
            if invoice.type == "out_invoice" and (invoice.state == "paid") and invoice.has_numeric_lcc_products:
                amount = sum(
                    self.invoice_line_ids.filtered(
                        lambda line: line.product_id.categ_id == categ
                    ).mapped("price_subtotal")
                )
                if amount > 0:
                    invoice.partner_id.action_credit_cyclos_account(amount)
                    invoice.write(
                        {
                            "cyclos_amount_credited": amount,
                        }
                    )
