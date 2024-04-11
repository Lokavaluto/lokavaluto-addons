
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_report_base_filename(self):
        self.ensure_one()
        if self.journal_id.is_receipt:
            return (
                self.move_type == "out_invoice"
                and self.state == "draft"
                and _("Draft Receipt")
                or self.move_type == "out_invoice"
                and self.state in ("open", "in_payment", "paid")
                and _("Receipt - %s") % (self.number)
            )
        else:
            super(AccountMove, self)._get_report_base_filename()
