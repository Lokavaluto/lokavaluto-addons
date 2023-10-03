from bdb import set_trace
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class Lead(models.Model):
    _inherit = "crm.lead"

    _MAIN_PROFILE_FIELDS = [
        "website_description",
        "street",
        "street2",
        "city",
        "zip",
        "country_id",
        "team_id",
        "phone",
        "company_email",
        "website",
        "industry_id",
        "detailed_activity",
        "reasons_choosing_mlc",
        "opening_time",
        "discount",
        "itinerant",
        "accept_digital_currency",
        "accept_coupons",
        "want_newsletter_subscription",
        "accept_policy",
    ]

    _POSITION_PROFILE_FIELDS = [
        "function",
        "street",
        "street2",
        "city",
        "zip",
        "country_id",
        "email_pro",
        "phone_pro",
    ]

    lead_type = fields.Selection(
        [
            ("misc", "Miscellenaous"),
            ("membership_web_application", "Membership Web Application"),
            ("affiliation_request", "Affiliation Request"),
            ("renewal_request", "Renewal Request"),
        ],
        string="Lead Type",
        required=True,
        readonly=True,
        copy=False,
        default="misc",
    )

    company_name = fields.Char(string=_("Company Name"))
    commercial_company_name = fields.Char(string=_("Commercial Company Name"))
    business_name = fields.Char(string=_("Business Name"))
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
    email_pro = fields.Char(string=_("Email Pro"))
    function = fields.Char(string=_("Job Position"))
    phone_pro = fields.Char(string=_("Phone Pro"))
    want_newsletter_subscription = fields.Boolean(
        string=_("Want Newsletters Subscription")
    )
    accept_policy = fields.Boolean(string=_("Accept LCC Policy"))
    edit_structure_profiles = fields.Boolean(
        string=_("Manage the structure's profiles")
    )
    total_membership = fields.Float(string=_("Membership amount"))
    message_from_candidate = fields.Text(string=_("Message from the candidate"))
    membership_product_id = fields.Many2one(
        "product.template",
        string=_("Membership product"),
        domain=[("membership", "=", True), ("type", "=", "service")],
    )
    invoice_url = fields.Char(string=_("Invoice link"))
    from_website = fields.Boolean(default=False)
    application_accepted = fields.Boolean(default=False)
    application_refused = fields.Boolean(default=False)
    affiliated_company = fields.Many2one(
        "res.partner",
        string="Affiliated organization",
        domain=[
            ("is_company", "=", True),
            ("is_main_profile", "=", True),
        ],
    )
    affiliation_accepted = fields.Boolean(default=False)
    affiliation_refused = fields.Boolean(default=False)
    renewal_accepted = fields.Boolean(default=False)
    renewal_refused = fields.Boolean(default=False)

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

    def _get_values_main_partner(self):
        values = {
            "name": self.company_name,
            "business_name": self.business_name,
            "is_company": True,
            "partner_profile": self.env["partner.profile"]
            .search([("ref", "=", "partner_profile_main")], limit=1)
            .id,
            "type": "contact",
        }
        for field_name in self._MAIN_PROFILE_FIELDS:
            values[field_name] = self._get_field_value(field_name)
        values.update({"email": values.pop("company_email", "")})
        return values

    def _get_values_other_contact(self, main_partner):
        values = {
            "name": self.contact_name,
            "is_company": False,
            "type": "other",
            "parent_id": main_partner.id,
        }
        for field_name in self._POSITION_PROFILE_FIELDS:
            values[field_name] = self._get_field_value(field_name)
        values.update({"phone": values.pop("phone_pro", "")})
        values.update({"email": values.pop("email_pro", "")})
        return values

    def _get_values_position_partner(self, main_partner):
        values = {
            "name": self.contact_name,
            "is_company": False,
            "contact_id": self.partner_id.id,
            "parent_id": main_partner.id,
            "partner_profile": self.env["partner.profile"]
            .search([("ref", "=", "partner_profile_position")], limit=1)
            .id,
            "type": "contact",
            "edit_structure_profiles": True,
        }
        for field_name in self._POSITION_PROFILE_FIELDS:
            values[field_name] = self._get_field_value(field_name)
        values.update({"phone": values.pop("phone_pro", "")})
        values.update({"email": values.pop("email_pro", "")})
        return values

    def _get_sale_order_values(self, partner):
        values = {
            "partner_id": partner.id,
            "team_id": self.team_id.id,
            "company_id": partner.company_id.id,
        }
        return values

    def _get_membership_values(self, sale_order):
        values = {
            "member_product_id": self.membership_product_id.id,
            "total_membership": self.total_membership,
            "order_id": sale_order.id,
        }
        return values

    def _create_organization_so_and_invoice(self, partner):
        values = self._get_sale_order_values(partner)
        sale_order = self.env["sale.order"].create(values)
        values = self._get_membership_values(sale_order)
        sale_order.sudo().create_membership(values)
        sale_order.sudo().action_confirm()
        invoice_id = sale_order.sudo().action_invoice_create()[0]
        invoice = self.env["account.invoice"].browse(invoice_id)
        invoice.action_invoice_open()
        self.invoice_url = invoice.get_portal_url()

    @api.multi
    def action_validate_organization_application(self):
        if not self.membership_product_id:
            raise UserError(
                "A membership product must be chosen to complete the registration."
            )

        # Organization's main partner creation
        values = self._get_values_main_partner()
        main_partner = self.env["res.partner"].create(values)
        # Organization's public profile is automaticcaly created

        if self.from_website:
            # Organization created from website, we create only an "other" contact
            values = self._get_values_other_contact(main_partner)
            self.env["res.partner"].create(values)
        else:
            # Organization's contact's position partner creation
            values = self._get_values_position_partner(main_partner)
            self.env["res.partner"].create(values)

        # Create sale order and invoice to finalize the registration process
        self._create_organization_so_and_invoice(main_partner)

        self.application_accepted = True

        # Redirect to the main profile
        view = self.env.ref("base.view_partner_form")
        return {
            "name": "Partners created",
            "view_type": "form",
            "view_mode": "form",
            "view_id": view.id,
            "res_model": "res.partner",
            "type": "ir.actions.act_window",
            "res_id": main_partner.id,
            "context": self.env.context,
        }

    @api.multi
    def action_refuse_organization_application(self):
        self.application_refused = True
        return

    def _get_renewal_values_main_partner(self):
        values = {
            "name": self.company_name,
            "business_name": self.business_name,
        }
        for field_name in self._MAIN_PROFILE_FIELDS:
            values[field_name] = self._get_field_value(field_name)
        company_email = values.pop("company_email", "")
        if company_email and self.partner_id.email != company_email:
            values.update({"email": company_email})
        return values

    @api.multi
    def action_validate_renewal_request(self):
        if not self.membership_product_id:
            raise UserError(
                "A membership product must be chosen to complete the registration."
            )

        # Organization's main partner update
        values = self._get_renewal_values_main_partner()
        self.partner_id.write(values)

        # Create sale order and invoice to finalize the registration process
        self._create_organization_so_and_invoice(self.partner_id)

        self.renewal_accepted = True
        return

    @api.multi
    def action_refuse_renewal_request(self):
        self.renewal_refused = True
        return

    @api.multi
    def action_validate_affiliation_request(self):
        if self.affiliated_company:
            # Organization's contact's position partner creation
            values = self._get_values_position_partner(self.affiliated_company)
            position_partner = self.env["res.partner"].create(values)

            self.affiliation_accepted = True

            # Redirect to the position partner
            view = self.env.ref("base.view_partner_form")
            return {
                "name": "Partners created",
                "view_type": "form",
                "view_mode": "form",
                "view_id": view.id,
                "res_model": "res.partner",
                "type": "ir.actions.act_window",
                "res_id": position_partner.id,
                "context": self.env.context,
            }
        else:
            raise UserError(
                _(
                    "You must indicate an Affiliated Organization in order to link it to the user.\n\nIf the organization doesn't exist in Odoo, please refuse the affiliation request\n and ask the user to make its organization apply for membership."
                )
            )

    @api.multi
    def action_refuse_affiliation_request(self):
        self.affiliation_refused = True
        return
