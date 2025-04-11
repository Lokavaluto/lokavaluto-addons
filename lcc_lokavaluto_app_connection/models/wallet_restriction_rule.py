from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class WalletRestrictionRule(models.Model):
    """A wallet restriction rule defines if a sender wallet is restricted to some recipients' wallet."""

    _name = "wallet.restriction.rule"
    _description = "Define restrictions between senders and recipients wallets"
    _order = "sequence"

    name = fields.Char("Name")
    active = fields.Boolean(default=True)
    sequence = fields.Integer()
    sender_wallet_domain = fields.Char("Sender Wallet Domain")
    recipient_wallet_domain = fields.Char("Recipient Wallet Domain")

    recipients_matched_by_rule = fields.Many2many(
        "res.partner.backend",
        string="Recipients Matched By The Rule",
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
        return recipient in self.recipients_matched_by_rule
