# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.http import request
from odoo.addons.partner_profiles_portal.controllers.portal_partner_profile import CustomerPortalPartnerProfile


class CustomerPortalPartnerProfileLcc(CustomerPortalPartnerProfile):

    def _get_profile_fields(self):
        fields = super(CustomerPortalPartnerProfileLcc, self)._get_profile_fields()
        lcc_fields = [
            "industry_id",
            "detailed_activity",
            "reasons_choosing_mlc",
            "itinerant",
            "accept_coupons",
            "accept_digital_currency",
            "phone_pro",
            "opening_time",
            "discount",
        ]
        fields.extend(lcc_fields) 
        return fields

    def _get_page_opening_values(self):
        values = super(CustomerPortalPartnerProfileLcc, self)._get_page_opening_values()
        values.update(
            {"industries": request.env["res.partner.industry"].sudo().search([])}
        )
        return values

    def _get_page_saving_values(self, profile, kw):
        values = super(CustomerPortalPartnerProfileLcc, self)._get_page_saving_values(profile, kw)
        if kw["website_description"] != "":
            values.update(
                {"website_description": kw["website_description"]}
            )
        return values