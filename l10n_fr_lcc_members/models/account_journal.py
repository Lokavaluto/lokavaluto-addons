from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_receipt = fields.Boolean("Print Receipt")
