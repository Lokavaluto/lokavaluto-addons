# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

PUBLIC_PROFILE_FIELDS = [
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
    "is_company",
]

POSITION_PROFILE_FIELDS = [
    "lastname",
    "firstname",
    "phone",
    "email",
    "function",
    "team_id",
    "is_company",
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
    is_main_profile = fields.Boolean(compute="_compute_profile_booleans", store=True)
    is_public_profile = fields.Boolean(compute="_compute_profile_booleans", store=True)
    is_position_profile = fields.Boolean(
        compute="_compute_profile_booleans", store=True
    )
    has_position = fields.Boolean(compute="_compute_profile_booleans", store=True)

    public_profile_id = fields.Many2one(
        "res.partner", compute="_compute_public_profile_id", string="Public profile"
    )
    odoo_user_id = fields.Many2one(
        "res.users", compute="_compute_odoo_user_id", string="Associated Odoo user"
    )

    edit_structure_main_profile = fields.Boolean(
        string=_("Manage structure's main profile")
    )
    edit_structure_public_profile = fields.Boolean(
        string=_("Manage structure's public profile")
    )
    can_edit_main_profile_ids = fields.Many2many(
        "res.partner",
        relation="res_partner_main_profile_rel",
        column1="partner_id",
        column2="profile_id",
        store=True,
        compute="_compute_can_edit",
        string="Can edit main profile",
    )
    can_edit_public_profile_ids = fields.Many2many(
        "res.partner",
        relation="res_partner_public_profile_rel",
        column1="partner_id",
        column2="profile_id",
        store=True,
        compute="_compute_can_edit",
        string="Can edit public profile",
    )
    want_newsletter_subscription = fields.Boolean(
        string=_("Want Newsletters Subscription")
    )
    accept_policy = fields.Boolean(string=_("Accept LCC Policy"))

    other_contact_ids = fields.One2many(
        domain=[("partner_profile.ref", "=", "partner_profile_position")]
    )

    @api.depends(
        "other_contact_ids",
        "other_contact_ids.edit_structure_main_profile",
        "other_contact_ids.edit_structure_public_profile",
    )
    def _compute_can_edit(self):
        for partner in self:
            partner.can_edit_main_profile_ids = partner.child_ids.filtered(
                "edit_structure_main_profile"
            ).mapped("contact_id")
            partner.can_edit_public_profile_ids = partner.child_ids.filtered(
                "edit_structure_public_profile"
            ).mapped("contact_id")

    @api.depends("partner_profile", "other_contact_ids")
    def _compute_profile_booleans(self):
        for partner in self:
            partner.is_main_profile = (
                partner.partner_profile.ref == "partner_profile_main"
            )
            partner.is_public_profile = (
                partner.partner_profile.ref == "partner_profile_public"
            )
            partner.is_position_profile = (
                partner.partner_profile.ref == "partner_profile_position"
            )
            partner.has_position = len(partner.other_contact_ids) > 0

    @api.depends("partner_profile")
    def _compute_public_profile_id(self):
        for partner in self:
            partner.public_profile_id = self.env["res.partner"].search(
                [
                    ("contact_id", "=", partner.id),
                    ("partner_profile.ref", "=", "partner_profile_public"),
                ],
                limit=1,
            )

    @api.depends("user_ids")
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
        if res.partner_profile.ref == "partner_profile_public":
            # Public profile can't be customer or supplier. Only main or position profiles can
            res.customer = False
            res.supplier = False
        return res

    @api.onchange("type")
    def _onchange_type(self):
        self.contact_type = "standalone"
        self.partner_profile = False
        if self.type == "contact" and self.parent_id != False:
            # A contact with parent_id is partner_profile=Position, and contact_type=attached
            position_profile = self.env.ref("lcc_members.partner_profile_position")
            self.contact_type = "attached"
            self.partner_profile = position_profile.id

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

    def _get_field_value(self, fname):
        field = self._fields[fname]
        if field.type == "many2one":
            return self[fname].id
        elif field.type == "one2many":
            return None
        elif field.type == "many2many":
            return [(6, 0, self[fname].ids)]
        else:
            return self[fname]

    @api.multi
    def create_public_profile(self):
        profile = self.env.ref("lcc_members.partner_profile_public").read()[0]
        for partner in self:
            partner._compute_public_profile_id()
            if not partner.public_profile_id:
                values = {
                    "type": "other",
                    "contact_id": partner.id,
                    "partner_profile": profile["id"],
                }
                for field_name in PUBLIC_PROFILE_FIELDS:
                    values[field_name] = partner._get_field_value(field_name)
                partner.create(values)
                partner._compute_public_profile_id()

    @api.model
    def _cron_generate_missing_public_profiles(self):
        partners = self.search(
            [("is_main_profile", "=", True), ("public_profile_id", "=", False)]
        )
        for partner in partners:
            partner.create_public_profile()

    @api.model
    def _cron_migration_lcc_members_v2_v3(self):
        cycle = 0
        # Company migration
        partners = self.search(
            [
                ("is_company", "=", True),
                ("active", "=", True),
            ]
        )
        for partner in partners:
            cycle += 1
            _logger.debug("Cycle #%s" % cycle)
            profile = self.env.ref("lcc_members.partner_profile_main").read()[0]
            partner.partner_profile = profile["id"]
            partner.create_public_profile()

        # Person migration
        partners = self.search(
            [
                ("is_company", "=", False),
                ("active", "=", True),
            ]
        )
        for partner in partners:
            cycle += 1
            _logger.debug("Cycle #%s" % cycle)
            if partner.parent_id == False:
                profile = self.env.ref("lcc_members.partner_profile_main").read()[0]
                partner.partner_profile = profile["id"]
                partner.create_public_profile()
            else:
                existing_main_partner = self.env["res.partner"].search(
                    [
                        ("active", "=", True),
                        ("is_company", "=", False),
                        ("name", "=", partner.name),
                        ("partner_profile.ref", "=", "partner_profile_main"),
                    ],
                    limit=1,
                )
                if len(existing_main_partner) > 0:
                    partner.contact_id = existing_main_partner[0].id
                    profile = self.env.ref(
                        "lcc_members.partner_profile_position"
                    ).read()[0]
                    partner.partner_profile = profile["id"]
                else:
                    profile = self.env.ref("lcc_members.partner_profile_main").read()[0]
                    partner.partner_profile = profile["id"]
                    partner.create_public_profile()
                    # create Position partner
                    profile = self.env.ref(
                        "lcc_members.partner_profile_position"
                    ).read()[0]
                    values = {
                        "type": "other",
                        "contact_id": partner.id,
                        "parent_id": partner.parent_id.id,
                        "company_id": partner.company_id.id,
                        "partner_profile": profile["id"],
                    }
                    for field_name in POSITION_PROFILE_FIELDS:
                        values[field_name] = partner._get_field_value(field_name)
                    partner.create(values)
                    # remove Position data from main profile
                    partner.function = ""
                    partner.phone_pro = ""
                    partner.parent_id = None


class PartnerImage(models.Model):
    _name = "partner.image"
    _description = "Partner Image"

    name = fields.Char("Name")
    image = fields.Binary("Image", attachment=True)
    partner_id = fields.Many2one("res.partner", "Related Partner", copy=True)
