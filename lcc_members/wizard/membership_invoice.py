# -*- coding: utf-8 -*-

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
        #add team_id to contact
        values = {"team_id": self.team_id.id}
        self.env["res.partner"].browse(self._context.get("active_ids")).write(values)
        res = super(MembershipInvoice, self).membership_invoice()
        #add team_id to the created invoices
        invoice_ids = None
        for d in res['domain']:
            if d[0] == 'id' and d[1] == 'in':
                invoice_ids = d[2]
                if invoice_ids:
                    self.env['account.invoice'].browse(invoice_ids).write({
                    'team_id':self.team_id.id
                    })
        return res
