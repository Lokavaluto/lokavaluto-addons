# Copyright  from 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tools.translate import _
from odoo import models, api


class PortalWizardUser(models.TransientModel):
    _inherit = "portal.wizard.user"

    def get_error_messages(self):
        error_msg = super(PortalWizardUser, self).get_error_messages()
        partners_error_attached = self.env["res.partner"]
        for wizard_user in self.with_context(active_test=False).filtered(
            lambda w: w.in_portal and not w.partner_id.user_ids
        ):
            if wizard_user.partner_id.contact_id:
                partners_error_attached |= wizard_user.partner_id
        if partners_error_attached:
            error_msg.append(
                "%s\n- %s"
                % (
                    _(
                        "Some contacts represent a job position and not a physical person, they can't be linked with a portal user: "
                    ),
                    "\n- ".join(partners_error_attached.mapped("display_name")),
                )
            )
        return error_msg
