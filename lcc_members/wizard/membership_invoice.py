
from odoo import api, fields, models


class MembershipInvoice(models.TransientModel):
    _inherit = "membership.invoice"

    @api.model
    def _default_team_id(self):
        return (
            self.env["res.partner"].browse(self._context.get("active_ids")).team_id.id
        )

    team_id = fields.Many2one(
        "crm.team",
        string="Local group",
        required=True,
        domain=[("local_group", "=", True)],
        default=_default_team_id,
    )

    def membership_invoice(self):
        values = {"team_id": self.team_id.id}
        self.env["res.partner"].browse(self._context.get("active_ids")).write(values)
        return super(MembershipInvoice, self).membership_invoice()
