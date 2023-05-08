import logging

from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class PublicStatsMlccService(Component):
    _inherit = "base.rest.service"
    _name = "public_stats.service"
    _usage = "mlcc"
    _collection = "lokavaluto.public.stats.services"
    _description = """
        MLCC Public Stats Services
        Get public statistics about a local currency 
    """

    # The following method are 'public' and can be called from the controller.

    @restapi.method(
        [(["/get", "/"], "GET")],
        input_param=Datamodel("stats.filter"),
    )
    def get(self, stats_filter):
        """
        Get MLCC public stats.
        """

        domain = [
            ("state", "=", "paid"),
            ("type", "in", ["out_invoice", "in_invoice"]),
            ("has_numeric_lcc_products", "=", True),
        ]
        invoices = self.env["account.invoice"].search(domain)
        mlcc_to_eur = 0.00
        eur_to_mlcc = 0.00
        for invoice in invoices:
            print(
                f"looking at {invoice.number} with {invoice.amount_total} and type {invoice.type}"
            )
            if invoice.type == "out_invoice":
                eur_to_mlcc += invoice.amount_total
            else:
                mlcc_to_eur += invoice.amount_total

        domain_partners = [
            # ("accept_digital_currency", "=", True),
            ("membership_state", "!=", "none"),
        ]
        partners = self.env["res.partner"].search(domain_partners)
        for p in partners:
            print(f"partner {p.name} {p.is_company} {p.membership_state}")
        individuals = len([p for p in partners if p.is_company == False])
        companies = len(partners) - individuals
        return {
            "eur_to_mlcc": eur_to_mlcc,
            "mlcc_to_eur": mlcc_to_eur,
            "mlcc_circulated": eur_to_mlcc - mlcc_to_eur,
            "nb_individuals": individuals,
            "nb_companies": companies,
        }
