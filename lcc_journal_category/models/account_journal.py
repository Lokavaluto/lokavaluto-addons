from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    category = fields.Selection(
        [
            ("asso", "compta fonctionnement asso"),
            ("coupon", "compta coupon/billets MLC"),
            ("num", "compta MLC numérique"),
        ],
        string="Catégorie",
        required=True,
        default="asso",
    )
