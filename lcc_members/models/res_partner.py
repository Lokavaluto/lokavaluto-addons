# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

PROFILE_FIELDS = [
    "name",
    "lastname",
    "firstname",
    "function",
    "phone",
    "mobile",
    "email",
    "website_url",
    "street",
    "street2",
    "city",
    "country_id",
    "zip",
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


class res_partner(models.Model):
    _inherit = "res.partner"

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
    partner_profile = fields.Many2one(
        "partner.profile",
        string=_("Partner profile"),
        required=False,
        translate=False,
        readonly=False,
    )
    is_main_profile = fields.Boolean(compute="_compute_profile_booleans")
    is_public_profile = fields.Boolean(compute="_compute_profile_booleans")
    is_position_profile = fields.Boolean(compute="_compute_profile_booleans")
    public_profile_id = fields.Many2one(
        "res.partner", compute="_compute_public_profile_id", string="Public profile"
    )
    odoo_user_id = fields.Many2one(
        "res.users", compute="_compute_odoo_user_id", string="Associated Odoo user"
    )

    edit_structure_main_profile = fields.Boolean(
        string=_("Can edit the structure's main profile")
    )
    edit_structure_public_profile = fields.Boolean(
        string=_("Can edit the structure's public profile")
    )

    want_newsletter_subscription = fields.Boolean(
        string=_("Want Newsletters Subscription")
    )
    accept_policy = fields.Boolean(
        string=_("Accept LCC Policy")
    )

    @api.onchange("partner_profile")
    def _compute_profile_booleans(self):
        self.is_main_profile = self.partner_profile.ref == "partner_profile_main"
        self.is_public_profile = self.partner_profile.ref == "partner_profile_public"
        self.is_position_profile = (
            self.partner_profile.ref == "partner_profile_position"
        )

    @api.onchange("partner_profile")
    def _compute_public_profile_id(self):
        for partner in self:
            partner.public_profile_id = self.env["res.partner"].search(
                [
                    ("contact_id", "=", partner.id),
                    ("partner_profile.ref", "=", "partner_profile_public"),
                ],
                limit=1,
            )

    @api.onchange("user_ids")
    def _compute_odoo_user_id(self):
        for partner in self:
            partner.odoo_user_id = self.env["res.users"].search(
                [("partner_id", "=", partner.id)], limit=1
            )

    @api.model
    def create(self, vals):
        """When creating, if partner_profile is not defined by a previous process, the defaut value is Main"""
        modified_self = self._basecontact_check_context("create")
        if not vals.get("partner_profile") and not vals.get("contact_id"):
            profile = self.env.ref("lcc_members.partner_profile_main").read()[0]
            vals["partner_profile"] = profile["id"]
        res = super(res_partner, modified_self).create(vals)
        if (
            res.partner_profile.ref == "partner_profile_main"
            and not res.public_profile_id
        ):
            res.create_public_profile()
        return res

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
            and self.firstname != self.firstname.capitalize()
        ):
            self.firstname = self.firstname.capitalize()

    @api.model
    def search_position_partners(self, profile):
        if profile:
            position_partners = self.env["res.partner"].search(
                [("contact_id", "=", self.id), ("partner_profile", "=", profile)]
            )
        else:
            position_partners = self.env["res.partner"].search(
                [("contact_id", "=", self.id)]
            )
        return position_partners

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

    def create_public_profile(self):
        self.ensure_one()
        profile = self.env.ref("lcc_members.partner_profile_public").read()[0]
        values = {
            "type": "other",
            "contact_id": self.id,
            "partner_profile": profile["id"],
            "name": self.name,
            "lastname": self.lastname,
            "firstname": self.firstname,
            "function": self.function,
            "phone": self.phone,
            "mobile": self.mobile,
            "email": self.email,
            "website_url": self.website_url,
            "street": self.street,
            "street2": self.street2,
            "city": self.city,
            "country_id": self.country_id.id,
            "zip": self.zip,
            "website_description": self.website_description,
            "industry_id": self.industry_id.id,
            "detailed_activity": self.detailed_activity,
            "reasons_choosing_mlc": self.reasons_choosing_mlc,
            "itinerant": self.itinerant,
            "accept_coupons": self.accept_coupons,
            "accept_digital_currency": self.accept_digital_currency,
            "phone_pro": self.phone_pro,
            "opening_time": self.opening_time,
            "discount": self.discount,
            "is_company": 1,
        }
        self.create(values)


class PartnerImage(models.Model):
    _name = "partner.image"
    _description = "Partner Image"

    name = fields.Char("Name")
    image = fields.Binary("Image", attachment=True)
    partner_id = fields.Many2one("res.partner", "Related Partner", copy=True)
