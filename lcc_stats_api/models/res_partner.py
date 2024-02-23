# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, api
from typing_extensions import TypedDict

_logger = logging.getLogger(__name__)


# Stats about partners participating to local currency
class PartnersStats(TypedDict):
    nb_individuals: int
    nb_companies: int


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def get_mlcc_stats(self):
        # Search active members only
        # Consider invoiced partners as active members
        domain_partners = [
            (
                "membership_state",
                "in",
                ["invoiced", "paid", "free"],
            ),
            ("is_main_profile", "=", True),
            ("active", "=", True),
        ]

        partners = self.search(domain_partners)

        individuals = len([p for p in partners if not p.is_company])
        companies = len(partners) - individuals

        return PartnersStats(nb_individuals=individuals, nb_companies=companies)
