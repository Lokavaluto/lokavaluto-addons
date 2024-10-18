from odoo import models, fields


class AccountInvoice(models.Model):
    _inherit = "account.move"

    contract_id = fields.Many2one("contract.contract", string="Contract")
