
from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_receipt = fields.Boolean("Print Receipt")
