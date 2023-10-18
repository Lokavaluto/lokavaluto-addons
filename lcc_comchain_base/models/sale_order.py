from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_top_up_requests(self, backend_keys):
        res = super(SaleOrder, self)._get_top_up_requests(backend_keys)
        if all(not backend_key.startswith("comchain:") for backend_key in backend_keys):
            return res

        ## XXXvlab: without ``sudo()`` we can't get the ``sale.order`` with
        ## status `sent`.
        top_up_requests = (
            self.env["sale.order"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("state", "=", "sent"),
                ],
                order="date_order desc",
            )
        )
        ## check invoice_status
        comchain_product = self.env.ref("lcc_comchain_base.product_product_comchain")
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")

        for sale_order in top_up_requests:
            ## XXXvlab: all this code should be on the res.partner.backend ! And the
            ## following can be removed.
            backend_account = sale_order.partner_id.get_wallet("comchain")

            amount = sum(
                line.product_uom_qty
                for line in sale_order.order_line
                if line.product_id.id == comchain_product.id
            )
            if amount == 0:
                continue

            _logger.debug("append topup amount: %s" % amount)
            res.append(
                {
                    "order_id": sale_order.id,
                    "amount": amount,
                    "date": int(sale_order.date_order.timestamp()),
                    "monujo_backend": [
                        "comchain:%s" % self.env.user.company_id.comchain_currency_name,
                        backend_account.comchain_id,
                    ],
                    "order_url": base_url + sale_order.get_portal_url(),
                    "paid": False,
                }
            )
        return res
