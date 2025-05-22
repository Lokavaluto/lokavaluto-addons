import requests
import json
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Inherits partner, define the fields for the FSS project"""

    _inherit = "res.partner"

    reference_tax_income = fields.Float(string="Reference tax income (€)")
    number_of_tax_shares = fields.Float(string="Number of tax shares")
    fss_quotient = fields.Float("FSS quotient (€)")
    initial_contribution_tranche = fields.Float(string="Initial contribution tranche (€)")
    number_of_increases = fields.Integer(string="Number of increases")
    reason_for_increases = fields.Char(string="Reason for the increases")
    number_of_decreases = fields.Integer(string="Number of decreases")
    reason_for_decreases = fields.Char(string="Reason for the decreases")
    contribution_reference_tranche = fields.Float(string="Contribution reference tranche (€)")
    number_of_allocation_units = fields.Float(string="Number of allocation units")
    allocation_amount = fields.Float(string="Allocation amount (€)")
    contribution_amount = fields.Float(string="Contribution amount (€)")
    contract_start_date = fields.Date(string="Contract start date")
    birth_year = fields.Integer(string="Birth Year")
    household_composition_adults = fields.Integer(string="Number of Adults (+18 years)")
    household_composition_children = fields.Integer(string="Number of children")
    household_child_allowance = fields.Selection(
        [
            ("no_dependent_children", "No dependent children"),
            (
                "shared_responsibility_household",
                "Shares responsibility within the household",
            ),
            (
                "shared_responsibility_alternate_custody",
                "Shares responsibility in alternate custody",
            ),
            ("sole_adult_responsible", "Sole adult responsible"),
            ("other", "Other"),
        ],
        string="Household Child Allowance",
    )
    household_child_allowance_other = fields.Char(
        string="Household Child Allowance Other, please precise"
    )
    name_of_allocation_beneficiary = fields.Char(
        string="Family an Given names of Allocation beneficiaries"
    )
    arrival_date_territory = fields.Date(string="Arrival year in the territory")
    monthly_household_food_budget = fields.Float(
        string="Monthly Household Food Budget (€)"
    )
    socio_professional_category = fields.Many2one(
        "hr.professional.category", string="Socio-Professional Category"
    )
    employer_id = fields.Many2one(
        "res.partner", string="Employer", domain="[('is_company','=',True)]"
    )
    food_system_worker = fields.Selection(
        [("yes", "Yes"), ("no", "No"), ("other", "Other")], string="Food System Worker"
    )
    food_system_worker_other = fields.Char(
        string="Food System Worker Other, please precise"
    )
    housing_status = fields.Selection(
        [
            ("owner_no_credit", "Owner without Credit"),
            ("owner_with_credit", "Owner with Credit"),
            ("tenant", "Tenant"),
            ("other", "Other"),
        ],
        string="Housing Status",
    )
    third_party_payer = fields.Many2one(
        "res.partner",
        string="Third Party Payer",
        domain="[('is_company','=',True)]",
    )

    ## ----  Fields for the points of sales (POS) res.partner type=company

    subscription_date = fields.Date(
        string="Subscription Date",
    )
    annual_sales = fields.Integer(
        string="Annual Sales (€)",
    )
    annual_sales_year = fields.Integer(
        string="Annual sales year",
    )
    contribution = fields.Float(
        string="Contribution of point of sales (€/month)",
    )
