# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = "account.invoice"

    @api.onchange('state')
    def _check_membership(self):
        for invoice in self:
            self.partner_id._recompute_todo(invoice.partner_id._fields['membership_state'])
        invoice.partner_id.recompute()