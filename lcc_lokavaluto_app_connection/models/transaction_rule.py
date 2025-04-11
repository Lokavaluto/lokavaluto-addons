from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class TransactionRule(models.Model):
    """A transaction rule defines if a transaction is authorized."""

    _name = "transaction.rule"
    _description = "Define if a transaction is authorized."
    _order = "sequence"

    name = fields.Char("Name")
    active = fields.Boolean(default=True)
    sequence = fields.Integer()
    sender_wallet_domain = fields.Char("Sender Wallet Domain")
    recipient_wallet_domain = fields.Char("Recipient Wallet Domain")
    is_transaction_allowed = fields.Boolean("Is Transaction Allowed?")

    recipients_matched_by_rule = fields.Many2many(
        "res.partner.backend",
        string="Matched Recipients",
        compute="_compute_recipients_matched_by_rule",
        store=False
    )

    @api.depends("recipient_wallet_domain")
    def _compute_recipients_matched_by_rule(self):
        for rule in self:
            rule.recipients_matched_by_rule = self.env["res.partner.backend"].search(
                safe_eval(self.recipient_wallet_domain)
            )

    def recipient_is_allowed_by_rule(self, recipient):
        if (
                self.is_transaction_allowed
                and recipient in self.recipients_matched_by_rule
        ) or (
                not self.is_transaction_allowed
                and recipient not in self.recipients_matched_by_rule
        ):
            return True
        else:
            return False
