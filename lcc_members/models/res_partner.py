# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class res_partner(models.Model):
    _inherit = "res.partner"

    business_name = fields.Char(string=_("Business Name"))
    reasons_choosing_mlc = fields.Text(
        string=_("Why did I choose local currency"),
        required=False,
        translate=True,
        readonly=False,
    )
    phone_pro = fields.Char(
        string=_("Professional phone"), required=False, translate=False, readonly=False
    )
    member_comment = fields.Text(  ## TODO v4 : TO BE DELETED
        string=_("Member comment"), required=False, translate=False, readonly=False
    )
    member_type_id = fields.Many2one(
        "member.type",
        string=_("Member's type"),
        required=False,
        translate=False,
        readonly=False,
    )
    convention_signature_date = fields.Date(
        string=_("convention signature date"),
        required=False,
        translate=False,
        readonly=False,
    )
    to_renew = fields.Boolean(
        string=_("To renew"), required=False, translate=False, readonly=False
    )
    legal_activity_code = fields.Char(  ## TODO v4 : TO BE DELETED
        string=_("legal activity code (ex. APE in France)"),
        required=False,
        translate=False,
        readonly=False,
    )
    keywords = fields.Text(
        string=_("keywords"), required=False, translate=True, readonly=False
    )
    opening_time = fields.Text(
        string=_("Opening Time"), required=False, translate=True, readonly=False
    )
    itinerant = fields.Boolean(
        string=_("Itinerant"), required=False, translate=False, readonly=False
    )
    detailed_activity = fields.Char(
        string=_("Detailed activity"), required=False, translate=True, readonly=False
    )
    is_volunteer = fields.Boolean(
        string=_("Is volunteer"), required=False, translate=False, readonly=False
    )
    private_comment = fields.Text(  ## TODO v4 : TO BE DELETED
        string=_("Private comment"), required=False, translate=False, readonly=False
    )
    convention_specific_agreement = fields.Text(  ## TODO v4 : TO BE DELETED
        string=_("Convention specific agreement"),
        required=False,
        translate=False,
        readonly=False,
    )
    convention_agreement = fields.Binary(
        string=_("Convention agreement"),
        attachment=True,
        required=False,
    )
    currency_exchange_office = fields.Boolean(
        string=_("Currency exchange office"),
        required=False,
        translate=False,
        readonly=False,
    )
    discount = fields.Html(
        string="Discount",
        translate="True",
    )
    partner_image_ids = fields.One2many(  ## TODO v4 : TO BE DELETED
        "partner.image", "partner_id", string="Images"
    )
    accept_coupons = fields.Boolean(
        string=_("Accept coupons"), required=False, translate=False, readonly=False
    )
    accept_digital_currency = fields.Boolean(
        string=_("Accept digital currency"),
        required=False,
        translate=False,
        readonly=False,
    )
    public_name = fields.Char(compute="_compute_public_name", store=True)

    want_newsletter_subscription = fields.Boolean(
        string=_("Want Newsletters Subscription")
    )
    refuse_numeric_wallet_creation = fields.Boolean(
        string=_("Refuse the creation of a numeric wallet.")
    )
    accept_policy = fields.Boolean(string=_("Accept LCC Policy"))
    website_id = fields.Many2one(compute="_compute_website_id", store=True)

    def _compute_website_id(self):
        for partner in self:
            website = self.env["website"].search(
                [("company_id", "=", partner.company_id.id)], limit=1
            )
            partner.website_id = website.id

    @api.depends(
        "public_profile_id.display_name",
        "public_profile_id.is_company",
        "public_profile_id.business_name",
        "public_profile_id.name",
    )
    def _compute_public_name(self):
        for partner in self:
            partner.public_name = (
                partner.public_profile_id[
                    "business_name"
                    if partner.public_profile_id.is_company
                    else "display_name"
                ]
                or partner.public_profile_id.name
            )

    @api.constrains("email")
    def _check_email_unique(self):
        for rec in self.filtered("email"):
            if "," in rec.email:
                raise UserError(
                    _(
                        "Field contains multiple email addresses. This is "
                        "not supported."
                    )
                )
            if rec.is_main_profile:
                if self.search_count(
                    [
                        ("email", "=", rec.email),
                        ("id", "!=", rec.id),
                        ("is_main_profile", "=", True),
                        ("is_company", "=", rec.is_company),
                    ]
                ):
                    raise UserError(
                        _("Email '%s' is already in use.") % rec.email.strip()
                    )

    @api.onchange("firstname", "lastname", "is_company")
    def onchange_upper_name(self):
        if (
            (not self.is_company)
            and self.lastname
            and self.lastname != self.lastname.upper()
        ):
            self.lastname = self.lastname.upper()
        if (
            (not self.is_company)
            and self.firstname
            and self.firstname != self.capitalize_first_letter(self.firstname)
        ):
            self.firstname = self.capitalize_first_letter(self.firstname)

    def capitalize_first_letter(self, string):
        if not string:
            return string
        return string[0].upper() + string[1:]

    def _membership_state(self):
        res = super(res_partner, self)._membership_state()
        today = fields.Date.today()
        for partner in self:
            s = 4
            if partner.member_lines:
                for mline in partner.member_lines.sorted(key=lambda r: r.id):
                    if (mline.date_to) >= today and (mline.date_from) <= today:
                        if mline.account_invoice_line.invoice_id.partner_id == partner:
                            mstate = mline.account_invoice_line.invoice_id.state
                            if mstate == "paid":
                                inv = mline.account_invoice_line.invoice_id
                                if not inv.payment_move_line_ids:
                                    partner.free_member = 1
                                else:
                                    partner.free_member = 0

            if partner.free_member and s != 0:
                res[partner.id] = "free"

        return res

    def _get_public_profile_fields(self):
        fields = super(res_partner, self)._get_public_profile_fields()
        lcc_fields = [
            "business_name",
            "lastname",
            "firstname",
            "website_url",
            "team_id",
            "website_description",
            "industry_id",
            "detailed_activity",
            "reasons_choosing_mlc",
            "itinerant",
            "accept_coupons",
            "accept_digital_currency",
            "phone_pro",
            "opening_time",
            "discount",
        ]
        fields.extend(lcc_fields)
        return fields


class PartnerImage(models.Model):
    _name = "partner.image"
    _description = "Partner Image"

    name = fields.Char("Name")
    image = fields.Binary("Image", attachment=True)
    partner_id = fields.Many2one("res.partner", "Related Partner", copy=True)
