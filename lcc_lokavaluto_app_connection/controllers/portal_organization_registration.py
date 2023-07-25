from odoo.addons.lcc_members_portal.controllers.portal_organization_registration import (
    PortalOrganizationRegistration,
)


class PortalOrganizationRegistrationWallet(PortalOrganizationRegistration):
    def _compute_organization_form_data(self, data):
        values = super(
            PortalOrganizationRegistrationWallet, self
        )._compute_organization_form_data(data)
        values["refuse_numeric_wallet_creation"] = (
            data.get("refuse_numeric_wallet_creation", "off") == "on"
        )
        return values
