# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.http import request
from odoo.addons.partner_profiles_portal.controllers.portal_my_account import (
    CustomerPortal,
)


class CustomerPortal(CustomerPortal):
    def _get_optional_main_fields(self):
        fields = super(CustomerPortal, self)._get_optional_main_fields()
        fields.extend(
            [
                "main_industry_id",
                "main_detailed_activity",
                "main_reasons_choosing_mlc",
                "main_itinerant",
                "main_accept_coupons",
                "main_accept_digital_currency",
                "main_opening_time",
            ]
        )
        return fields

    def _get_special_fields(self):
        fields = super(CustomerPortal, self)._get_special_fields()
        fields.extend(
            [
                "main_website_description",
                "main_discount",
            ]
        )
        return fields

    def _get_main_boolean_account_fields(self):
        fields = super(CustomerPortal, self)._get_main_boolean_account_fields()
        fields.extend(
            [
                "main_itinerant",
                "main_accept_coupons",
                "main_accept_digital_currency",
            ]
        )
        return fields

    def _get_page_opening_values(self):
        values = super(CustomerPortal, self)._get_page_opening_values()
        values.update(
            {"industries": request.env["res.partner.industry"].sudo().search([])}
        )
        return values

    def _retrieve_main_values(self, data):
        values = super(CustomerPortal, self)._retrieve_main_values(data)
        if data.get("main_website_description", "") != "":
            values.update({"website_description": data["main_website_description"]})
        if data.get("main_discount", "") != "":
            values.update({"discount": data["main_discount"]})
        return values
