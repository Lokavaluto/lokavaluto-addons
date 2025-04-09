from odoo import models, fields


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
