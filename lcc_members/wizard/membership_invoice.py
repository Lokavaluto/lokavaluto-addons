# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MembershipInvoice(models.TransientModel):
    _inherit = "membership.invoice"

    team_id = fields.Many2one(
        "crm.team",
        string="Local group",
        required=True,
        domain=[("local_group", "=", True)],
    )

    def membership_invoice(self):
        values = {"team_id": self.team_id.id}
        self.env["res.partner"].browse(self._context.get("active_ids")).write(values)
        return super(MembershipInvoice, self).membership_invoice()
