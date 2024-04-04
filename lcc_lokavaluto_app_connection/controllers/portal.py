import logging
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal  # Import the class

_logger = logging.getLogger(__name__)


class CustomCustomerPortal(CustomerPortal):  # Inherit in your custom class

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
