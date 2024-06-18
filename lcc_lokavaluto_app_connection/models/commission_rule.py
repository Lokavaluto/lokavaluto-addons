from odoo import models, fields


class CommissionRule(models.Model):
    """A commission rule defines the way to calculate the reconversion
    commission amount for digital currencies."""

    _name = "commission.rule"

    name = fields.Char("Name")
    active = fields.Boolean(default=True)
    wallet_domain = fields.Char("Wallet Domain")

    calculation_rule = fields.Selection(
        [
            ("fix", "Fix amount"),
            ("percentage", "Percentage"),
        ],
        string="Calculation Rule",
    )

    calculation_value = fields.Float("Value")

    def calculate_commission_amount(self, debit_amount):
        self.ensure_one()
        if self.calculation_rule == "fix":
            return self.calculation_value
        elif self.calculation_rule == "percentage":
            return debit_amount * self.calculation_value / 100
