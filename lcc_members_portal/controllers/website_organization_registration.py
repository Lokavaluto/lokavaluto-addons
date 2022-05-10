# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.http import request


class WebsiteOrganizationRegistration(http.Controller):
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
        "company_email",
        "website_url",
        "industry_id",
        "detailed_activity",
        "reasons_choosing_mlc",
        "opening_time",
        "discount",
        "contact_name",
        "function",
        "email_pro",
        "phone_pro",
        "message_from_candidate",
    ]

    # Variable to update to add other fields in child classes
    _EXTRA_FIELDS = []

    def get_organization_membership_product(self):
        product_obj = request.env["product.template"]
        product = product_obj.sudo().get_organization_membership_product(
            request.website.company_id.id
        )
        return product

    @http.route(
        ["/web/organization_registration"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_organization_registration(self, access_token=None, redirect=None, **kw):

        product = self.get_organization_membership_product()
        titles = request.env["res.partner.title"].sudo().search([])
        countries = request.env["res.country"].sudo().search([])
        teams = (
            request.env["crm.team"]
            .sudo()
            .search(
                [
                    ("local_group", "=", True),
                    ("company_id", "=", request.website.company_id.id),
                ]
            )
        )
        industries = request.env["res.partner.industry"].sudo().search([])
        error = dict()
        error_message = []

        values = {
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

        return request.render(
            "lcc_members_portal.website_organization_registration", values
        )

    @http.route(
        ["/web/send_request"],
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
        values["partner_id"] = 2  # OdooBot-s ID
        values["company_id"] = request.website.company_id.id
        values["type"] = "opportunity"
        values["lead_type"] = "membership_web_application"
        values.update({"zip": values.pop("zipcode", "")})
        values.update({"website": values.pop("website_url", "")})
        values["accept_coupons"] = kwargs.get("accept_coupons", "off") == "on"
        values["accept_digital_currency"] = (
            kwargs.get("accept_digital_currency", "off") == "on"
        )
        values["from_website"] = True
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
            "lcc_members_portal.website_organization_registration_saved", {}
        )
