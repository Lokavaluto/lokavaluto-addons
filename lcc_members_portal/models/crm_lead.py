from odoo import fields, models, api
from odoo.tools.translate import _


class Lead(models.Model):
    _inherit = "crm.lead"

    company_name = fields.Char(string=_("Company Name"))
    commercial_company_name = fields.Char(string=_("Commercial Company Name"))
    website_description = fields.Html(string=_("Website Description"), strip_style=True)
    company_email = fields.Char(string=_("Email"))
    industry_id = fields.Many2one("res.partner.industry", string=_("Main activity"))
    detailed_activity = fields.Char(string=_("Detailed activity"))
    reasons_choosing_mlc = fields.Text(string=_("Why did I choose local currency"))
    opening_time = fields.Text(string=_("Opening Time"))
    discount = fields.Html(string=_("Discount"))
    accept_digital_currency = fields.Boolean(string=_("Accept digital currency"))
    accept_coupons = fields.Boolean(string=_("Accept coupons"))
    itinerant = fields.Boolean(string=_("Itinerant"))
    function = fields.Char(string=_("Job Position"))
    phone_pro = fields.Char(string=_("Phone Pro"))
    want_newsletter_subscription = fields.Boolean(
        string=_("Want Newsletters Subscription")
    )
    accept_policy = fields.Boolean(string=_("Accept LCC Policy"))
    total_membership = fields.Float(string=_("Membership amount"))
    message_from_candidate = fields.Text(string=_("Message from the candidate"))
