import logging
from odoo import http, _
from odoo.http import request
# from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.sale.controllers.portal import CustomerPortal  # Import the class

_logger = logging.getLogger(__name__)


class CustomCustomerPortal(CustomerPortal):  # Inherit in your custom class
    # @http.route(
    #     ["/my/orders/<int:order_id>/transaction/"],
    #     type="json",
    #     auth="public",
    #     website=True,
    # )
    # def payment_transaction_token(
    #     self, acquirer_id, order_id, save_token=False, access_token=None, **kwargs
    # ):
    #     # Ensure a payment acquirer is selected
    #     if not acquirer_id:
    #         return False

    #     try:
    #         acquirer_id = int(acquirer_id)
    #     except:
    #         return False

    #     order = request.env["sale.order"].sudo().browse(order_id)
    #     if not order or not order.order_line or not order.has_to_be_paid():
    #         return False

    #     # Create transaction
    #     query_string = "&success=1"
    #     vals = {
    #         "acquirer_id": acquirer_id,
    #         "type": order._get_payment_type(),
    #         "return_url": order.get_portal_url(query_string=query_string),
    #     }
    #     # Check reply URL
    #     _logger.debug("Vals: %s" % vals)
    #     transaction = order._create_payment_transaction(vals)
    #     PaymentProcessing.add_payment_transaction(transaction)
    #     return transaction.render_sale_button(
    #         order,
    #         submit_txt=_("Pay & Confirm"),
    #         render_values={
    #             "type": order._get_payment_type(),
    #             "alias_usage": _(
    #                 "If we store your payment information on our server, subscription payments will be made automatically."
    #             ),
    #         },
    #     )

    # @http.route(
    #     "/my/orders/<int:order_id>/transaction/token",
    #     type="http",
    #     auth="public",
    #     website=True,
    # )
    # def payment_token(self, order_id, pm_id=None, **kwargs):
    #     order = request.env["sale.order"].sudo().browse(order_id)
    #     if not order:
    #         return request.redirect("/my/orders")
    #     if not order.order_line or pm_id is None or not order.has_to_be_paid():
    #         return request.redirect(order.get_portal_url())

    #     # try to convert pm_id into an integer, if it doesn't work redirect the user to the quote
    #     try:
    #         pm_id = int(pm_id)
    #     except ValueError:
    #         return request.redirect(order.get_portal_url())

    #     # Create transaction
    #     query_string = "&success=1"
    #     vals = {
    #         "payment_token_id": pm_id,
    #         "type": "server2server",
    #         "return_url": order.get_portal_url(query_string=query_string),
    #     }
    #     _logger.debug("Vals: %s" % vals)
    #     tx = order._create_payment_transaction(vals)
    #     PaymentProcessing.add_payment_transaction(tx)
    #     return request.redirect("/payment/process")

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values["monujo_web_app_url"] = request.env.user.company_id.monujo_web_app_url
        values[
            "monujo_android_app_url"
        ] = request.env.user.company_id.monujo_android_app_url
        values["monujo_ios_app_url"] = request.env.user.company_id.monujo_ios_app_url
        values[
            "show_app_access_buttons"
        ] = request.env.user.partner_id.show_app_access_buttons()
        return values
