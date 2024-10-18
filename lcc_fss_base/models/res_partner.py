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

    birth_year = fields.Integer(string="Birth Year")
    household_composition_adults = fields.Integer(string="Number of Adults (+18 years)")
    household_composition_teens = fields.Integer(string="Number of Teens (14-18 years)")
    household_composition_children = fields.Integer(
        string="Number of Children (-14 years)"
    )
    arrival_date_territory = fields.Date(string="Arrival Date in the territory")
    monthly_household_income = fields.Float(string="Monthly Household Income (€)")
    reference_tax_income = fields.Float(string="Reference tax income (€)")
    socio_professional_category = fields.Many2one(
        "hr.professional.category", string="Socio-Professional Category"
    )
    employer_id = fields.Many2one(
        "res.partner", string="Employer", domain="[('is_company','=',True)]"
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
