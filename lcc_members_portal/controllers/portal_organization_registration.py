# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalOrganizationRegistration(CustomerPortal):
    _ORGANIZATION_REGISTRATION_FIELDS = [
        "company_name",
        "commercial_company_name",
        "website_description",
        "street",
        "street2",
        "city",
        "zipcode",
        "country_id",
        # "team_id",  # TODO: issue occuring when this field is added. INVESTIGATION NEEDED
        "phone",
        "email",
        "website_url",
        "industry_id",
        "detailed_activity",
        "reasons_choosing_mlc",
        "opening_time",
        "discount",
        "function",
        "phone_pro",
        "message_from_candidate",
    ]

    # Variable to update to add other fields in child classes
    _EXTRA_FIELDS = []

    def _organization_get_page_view_values(self, partner, access_token, **kwargs):
        values = {
            "page_name": "portal_organization_registration",
            "partner": partner,
        }
        return self._get_page_view_values(
            partner,
            access_token,
            values,
            "my_organization_registration_history",
            False,
            **kwargs
        )

    def get_organization_membership_product(self):
        product_obj = request.env["product.template"]
        product = product_obj.sudo().get_organization_membership_product(
            request.env.user.partner_id.company_id.id
        )
        return product

    def get_selected_team_id(self, kwargs):
        team_obj = request.env["crm.team"]
        team_id = kwargs.get("team_id")
        return team_obj.sudo().browse(int(team_id))[0]

    def get_selected_country_id(self, kwargs):
        country_obj = request.env["res.country"]
        country_id = kwargs.get("country_id")
        return country_obj.sudo().browse(int(country_id))[0]

    @http.route(
        ["/my/organization_registration"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_organization_registration(self, access_token=None, redirect=None, **kw):
        partner = request.env.user.partner_id

        values = self._organization_get_page_view_values(partner, access_token, **kw)
        product = self.get_organization_membership_product()
        titles = request.env["res.partner.title"].sudo().search([])
        countries = request.env["res.country"].sudo().search([])
        teams = (
            request.env["crm.team"]
            .sudo()
            .search(
                [("local_group", "=", True), ("company_id", "=", partner.company_id.id)]
            )
        )
        industries = request.env["res.partner.industry"].sudo().search([])
        error = dict()
        error_message = []

        values.update(
            {
                "product": product,
                "total_membership": product.list_price,
                "dynamic_price": product.dynamic_price,
                "titles": titles,
                "countries": countries,
                "industries": industries,
                "teams": teams,
                "error": error,
                "error_message": error_message,
            }
        )
        return request.render(
            "lcc_members_portal.portal_organization_registration", values
        )

    @http.route(
        ["/membership/send_request"],
        type="http",
        auth="public",
        website=True,
    )
    def send_registration_request(self, **kwargs):
        # Create a new lead
        values = {}
        for field in self._ORGANIZATION_REGISTRATION_FIELDS:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        for field in self._EXTRA_FIELDS:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        values["name"] = "[NEW APPLICATION] " + values["company_name"]
        main_partner = request.env.user.partner_id
        values["partner_id"] = main_partner.id
        values["company_id"] = main_partner.company_id.id
        values["type"] = "opportunity"
        values["lead_type"] = "membership_web_application"
        values.update({"zip": values.pop("zipcode", "")})
        values.update({"website": values.pop("website_url", "")})
        values["accept_coupons"] = kwargs.get("accept_coupons", "off") == "on"
        values["accept_digital_currency"] = (
            kwargs.get("accept_digital_currency", "off") == "on"
        )
        values["itinerant"] = kwargs.get("itinerant", "off") == "on"
        values["want_newsletter_subscription"] = (
            kwargs.get("want_newsletter_subscription", "off") == "on"
        )
        values["accept_policy"] = kwargs.get("accept_policy", "off") == "on"
        if float(kwargs.get("total_membership", False)):
            values["total_membership"] = float(kwargs.get("total_membership"))
        else:
            values[
                "total_membership"
            ] = self.get_organization_membership_product().list_price

        lead = request.env["crm.lead"].sudo().create(values)
        lead.team_id = kwargs.pop(
            "team_id"
        )  # TODO: see remark above concerning team_id
        return request.render(
            "lcc_members_portal.portal_organization_registration_saved", {}
        )
