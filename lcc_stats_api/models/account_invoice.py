# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import models, api
from typing_extensions import TypedDict

from ..datamodel.stats_filter import StatsFilter

_logger = logging.getLogger(__name__)


# Generic stats about currency
class CurrencyStats(TypedDict):
    eur_to_mlcc: float
    mlcc_to_eur: float
    mlcc_circulating: float


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def get_mlcc_stats(self, stats_filter: StatsFilter = None):
        # Look for paid invoices with LCC products
        domain_invoices = [
            ("state", "=", "paid"),
            ("type", "in", ["out_invoice", "in_invoice"]),
            ("has_numeric_lcc_products", "=", True),
        ]

        # Filter date if specified
        if stats_filter:
            if stats_filter.start_date:
                domain_invoices.append(("date_invoice", ">=", stats_filter.start_date))
            if stats_filter.end_date:
                domain_invoices.append(("date_invoice", "<=", stats_filter.end_date))

        invoices = self.search(domain_invoices)
        mlcc_to_eur = 0.00
        eur_to_mlcc = 0.00
        for invoice in invoices:
            if invoice.type == "out_invoice":
                eur_to_mlcc += invoice.amount_total
            else:
                mlcc_to_eur += invoice.amount_total

        return CurrencyStats(
            eur_to_mlcc=eur_to_mlcc,
            mlcc_to_eur=mlcc_to_eur,
            mlcc_circulating=eur_to_mlcc - mlcc_to_eur,
        )
