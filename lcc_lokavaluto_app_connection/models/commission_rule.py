from odoo import models, fields


class CommissionRule(models.Model):
    """A commission rule defines the way to calculate the reconversion
    commission amount for digital currencies."""

    _name = "commission.rule"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Define the way a commission must be applied on debit requests"

    name = fields.Char("Name", tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer(tracking=True)
    wallet_domain = fields.Char("Wallet Domain", tracking=True)

    calculation_rule = fields.Selection(
        [
            ("fix", "Fix amount"),
            ("percentage", "Percentage"),
        ],
        string="Calculation Rule",
        tracking=True,
    )

    calculation_value = fields.Float("Value", tracking=True)

    def calculate_commission_amount(self, debit_amount):
        self.ensure_one()
        if self.calculation_rule == "fix":
            return self.calculation_value
        elif self.calculation_rule == "percentage":
            return debit_amount * self.calculation_value / 100
