from odoo import models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_report_base_filename(self):
        self.ensure_one()
        if self.journal_id.is_receipt:
            if self.move_type == "out_invoice" and self.state == "draft":
                return _("Draft Receipt - %s") % self.name
            elif self.move_type == "out_invoice" and self.state == "posted":
                return _("Receipt - %s") % self.name
            elif self.move_type == "out_invoice" and self.state == "cancel":
                return _("Cancelled Receipt - %s") % self.name
            else:
                raise UserError(_("The receipt is in a state we do not handle. "
                                  "Please contact the support for this issue."))

        return super(AccountMove, self)._get_report_base_filename()
