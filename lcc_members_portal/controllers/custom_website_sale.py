# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class CustomWebsiteSale(WebsiteSale):
    @http.route(
        ["/shop/confirm_order"], type="http", auth="public", website=True, sitemap=False
    )
    def confirm_order(self, **post):
        sale_order = request.website.sale_get_order(force_create=True)
        membership = any(sale_order.order_line.mapped("product_id.membership"))

        if not membership:
            res = super(CustomWebsiteSale, self).confirm_order()
            return res

        redirection = self.checkout_redirection(sale_order)
        if redirection:
            return redirection

        sale_order.onchange_partner_shipping_id()
        sale_order.order_line._compute_tax_id()
        request.session["sale_last_order_id"] = sale_order.id
        request.website.sale_get_order(update_pricelist=False)
        extra_step = request.website.viewref("website_sale.extra_info_option")
        if extra_step.active:
            return request.redirect("/shop/extra_info")

        return request.redirect("/shop/payment")
