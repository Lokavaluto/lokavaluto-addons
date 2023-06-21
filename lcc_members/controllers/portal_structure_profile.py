# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.http import request
from odoo.addons.partner_profiles_portal.controllers.portal_structure_profile import CustomerPortalStructureProfile


class CustomerPortalStructureProfileLcc(CustomerPortalStructureProfile):

    def _get_main_profile_fields(self):
        fields = super(CustomerPortalStructureProfileLcc, self)._get_main_profile_fields()
        lcc_fields = [
            "main_industry_id",
            "main_detailed_activity",
            "main_reasons_choosing_mlc",
            "main_itinerant",
            "main_accept_coupons",
            "main_accept_digital_currency",
            "main_opening_time",
        ]
        fields.extend(lcc_fields) 
        return fields

    def _get_main_boolean_structure_fields(self):
        fields = super(CustomerPortalStructureProfileLcc, self)._get_main_boolean_structure_fields()
        lcc_fields = [
            "main_itinerant",
            "main_accept_coupons",
            "main_accept_digital_currency",
        ]
        fields.extend(lcc_fields)
        return fields

    def _get_page_opening_values(self):
        values = super(CustomerPortalStructureProfileLcc, self)._get_page_opening_values()
        values.update(
            {"industries": request.env["res.partner.industry"].sudo().search([])}
        )
        return values

    def _get_page_saving_main_values(self, kw):
        values = super(CustomerPortalStructureProfileLcc, self)._get_page_saving_main_values(kw)
        if kw.get("main_website_description", "") != "":
            values.update(
                {"website_description": kw["main_website_description"]}
            )
        if kw.get("main_discount", "") != "":
            values.update(
                {"discount": kw["main_discount"]}
            )
        return values