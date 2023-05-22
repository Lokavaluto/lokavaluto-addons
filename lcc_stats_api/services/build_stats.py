from typing_extensions import TypedDict


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


def build_currency_stats_from_invoices(invoices) -> CurrencyStats:
    """
    Build stats about MLCC from invoices
    """
    print("received invoices", invoices)
    mlcc_to_eur = 0.00
    eur_to_mlcc = 0.00
    for invoice in invoices:
        print(
            f"looking at {invoice.number} with {invoice.amount_total} and type {invoice.type} and partner id {invoice.partner_id}"
        )
        if invoice.type == "out_invoice":
            eur_to_mlcc += invoice.amount_total
        else:
            mlcc_to_eur += invoice.amount_total

    return CurrencyStats(
        eur_to_mlcc=eur_to_mlcc,
        mlcc_to_eur=mlcc_to_eur,
        mlcc_circulating=eur_to_mlcc - mlcc_to_eur,
    )
