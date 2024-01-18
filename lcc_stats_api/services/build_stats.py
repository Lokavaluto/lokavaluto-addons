from typing_extensions import TypedDict

from ..datamodel.stats_filter import StatsFilter


# Generic stats about currency
class CurrencyStats(TypedDict):
    eur_to_mlcc: float
    mlcc_to_eur: float
    mlcc_circulating: float


# Generic validator for an API returning currency stats
currency_stats_validator = {
    "eur_to_mlcc": {"type": "float", "required": True, "empty": False},
    "mlcc_to_eur": {"type": "float", "required": True, "empty": False},
    "mlcc_circulating": {"type": "float", "required": True, "empty": False},
}


def build_currency_stats_from_invoices(
    invoices_model, partner_id: int = None, stats_filter: StatsFilter = None
) -> CurrencyStats:
    """
    Build stats about MLCC from invoices
    """

    domain_invoices = [
        ("state", "=", "paid"),
        ("type", "in", ["out_invoice", "in_invoice"]),
        ("has_numeric_lcc_products", "=", True),
    ]
    if partner_id:
        domain_invoices.append(("partner_id", "=", partner_id))

    if stats_filter and stats_filter.start_date:
        domain_invoices.append(("date_invoice", ">=", stats_filter.start_date))

    if stats_filter and stats_filter.end_date:
        domain_invoices.append(("date_invoice", "<=", stats_filter.end_date))

    invoices = invoices_model.search(domain_invoices)
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
