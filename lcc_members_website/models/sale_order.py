import logging
from odoo import fields, models, api

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def create_membership(self, vals):
        _logger.debug("TEST 1")
        product_context = dict(self.env.context)
        product_context.setdefault('lang', self.sudo().partner_id.lang)
        SaleOrderLineSudo = self.env['sale.order.line'].sudo().with_context(product_context)
        product = False
        _logger.debug("TEST: %s" % vals)
        if vals.get("member_product_id", False):
            product = self.env["product.product"].search([('id', '=', vals.get("member_product_id"))])
        
        if not product:
            raise UserError(_("The given combination does not exist therefore it cannot be added to cart."))
        product_template = product.product_tmpl_id
        product_id = product.id
        values = {
            'product_id': product_id,
            'product_uom_qty': 1,
            'order_id': vals.get("order_id"),
            'product_uom': product.uom_id.id,
            'price_unit': vals.get('total_membership'),
        }

        order_line = SaleOrderLineSudo.create(values)
        order_line._compute_tax_id()
        _logger.debug("ORDER_line: %s" % order_line.price_unit)
        return {'line_id': order_line.id, 'quantity': 1, 'option_ids': []}

    @api.model
    def create_comp_membership(self, vals):
        vals["name"] = vals["company_name"]
        if not vals.get("partner_id"):
            cooperator = self.env["res.partner"].get_cooperator_from_crn(
                vals.get("company_register_number")
            )
            if cooperator:
                vals["partner_id"] = cooperator.id
                vals["type"] = "increase"
                vals["already_cooperator"] = True
        subscr_request = super(SubscriptionRequest, self).create(vals)

        confirmation_mail_template = subscr_request.get_mail_template_notif(
            True
        )
        confirmation_mail_template.send_mail(subscr_request.id)

        return subscr_request