from odoo.addons.lcc_members_portal.controllers.portal_private_registration import (
    PortalPrivateRegistration,
)


class PortalPrivateRegistrationWallet(PortalPrivateRegistration):
    def _compute_private_form_data(self, data):
        values = super(
            PortalPrivateRegistrationWallet, self
        )._compute_private_form_data(data)
        values["refuse_numeric_wallet_creation"] = (
            data.get("refuse_numeric_wallet_creation", "off") == "on"
        )
        return values
