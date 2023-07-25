from odoo.addons.lcc_members_portal.controllers.website_organization_registration import (
    WebsiteOrganizationRegistration,
)


class WebsiteOrganizationRegistrationWallet(WebsiteOrganizationRegistration):
    def _compute_web_form_data(self, data):
        values = super(
            WebsiteOrganizationRegistrationWallet, self
        )._compute_web_form_data(data)
        values["refuse_numeric_wallet_creation"] = (
            data.get("refuse_numeric_wallet_creation", "off") == "on"
        )
        return values
