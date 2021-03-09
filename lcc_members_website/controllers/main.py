import base64
import logging
import re
from datetime import datetime

from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)

# Only use for behavior, don't stock it
_TECHNICAL = ["view_from", "view_callback"]

# transient fields used to compute the address field
_EXTRA_FIELDS = []

# Allow in description
_BLACKLIST = [
    "id",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
    "user_id",
    "active",
]

_MEMBER_FORM_FIELD = [
    "email",
    "confirm_email",
    "firstname",
    "lastname",
    "member_product_id",
    "street",
    "city",
    "zip",
    "country_id",
    "team_id",
    "phone",
    "lang",
    "nb_parts",
    "total_membership",
    "error_msg",
]

_PARTNER_FORM_FIELD = [
    "email",
    "firstname",
    "lastname",
    "street",
    "city",
    "zip",
    "country_id",
    "team_id",
    "phone",
    "lang",
    "gender",
    "error_msg",
]

_COMPANY_FORM_FIELD = [
    "is_company",
    #"company_register_number",
    "company_name",
    "company_email",
    "confirm_email",
    "email",
    "firstname",
    "lastname",
    "member_product_id",
    "street",
    "city",
    "zip",
    "country_id",
    "team_id",
    "phone",
    "lang",
    "nb_parts",
    "total_membership",
    "error_msg",
    "company_type",
]


class WebsiteMembership(http.Controller):
    @http.route(
        ["/page/become_member", "/become_member"],
        type="http",
        auth="public",
        website=True,
    )
    def display_become_member_page(self, **kwargs):
        values = {}
        logged = False
        if request.env.user.login != "public":
            logged = True
            partner = request.env.user.partner_id
            if partner.is_company:
                return self.display_become_company_member_page()
        values = self.fill_values(values, False, logged, True)

        for field in _MEMBER_FORM_FIELD:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)

        values.update(kwargs=kwargs.items())
        #TODO add config default amount.
        values["total_membership"] = '25'
        return request.render("lcc_members_website.becomemember", values)

    @http.route(
        ["/page/become_company_member", "/become_company_member"],
        type="http",
        auth="public",
        website=True,
    )
    def display_become_company_member_page(self, **kwargs):
        values = {}
        logged = False

        if request.env.user.login != "public":
            logged = True
        values = self.fill_values(values, True, logged, True)

        for field in _COMPANY_FORM_FIELD:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        values.update(kwargs=kwargs.items())
        return request.render(
            "lcc_members_website.becomecompanymember", values
        )

    def preRenderThanks(self, values, kwargs):
        """ Allow to be overrided """
        return {"_values": values, "_kwargs": kwargs}

    def get_subscription_response(self, values, kwargs):
        values = self.preRenderThanks(values, kwargs)
        return request.render("lcc_members_website.member_thanks", values)

    def get_date_string(self, birthdate):
        if birthdate:
            return datetime.strftime(birthdate, "%d/%m/%Y")
        return False

    def get_values_from_user(self, values, is_company):
        # the subscriber is connected
        if request.env.user.login != "public":
            values["logged"] = "on"
            partner = request.env.user.partner_id

            #if partner.member or partner.old_member:
            #    values["already_member"] = "on"
            values["address"] = partner.street
            values["zip"] = partner.zip
            values["city"] = partner.city
            values["country_id"] = partner.country_id.id
            values["team_id"] = partner.team_id.id or ''
            _logger.debug("TEAM2: %s" %  partner.team_id.id)

            if is_company:
                # company values
                #values["company_register_number"] = partner.company_register_number
                values["company_name"] = partner.name
                values["company_email"] = partner.email
                #values["company_type"] = partner.legal_form
                # contact person values
                # representative = partner.get_representative()
                # values["firstname"] = representative.firstname
                # values["lastname"] = representative.lastname
                # values["gender"] = representative.gender
                # values["email"] = representative.email
                # values["contact_person_function"] = representative.function
                # values["lang"] = representative.lang
                # values["phone"] = representative.phone
            else:
                values["firstname"] = partner.firstname
                values["lastname"] = partner.lastname
                values["email"] = partner.email
                values["gender"] = partner.gender
                values["lang"] = partner.lang
                values["phone"] = partner.phone
        return values

    def fill_values(self, values, is_company, logged, load_from_user=False):
        partner_obj = request.env["res.partner"]
        _logger.debug("request.env: %s" % request.env)
        #member_type_obj = request.env["member_type"]
        company = request.website.company_id
        products = self.get_membership_products(is_company)

        if load_from_user:
            values = self.get_values_from_user(values, is_company)
        if is_company:
            values["is_company"] = "on"
        if logged:
            values["logged"] = "on"
        values["countries"] = self.get_countries()
        values["teams"] = self.get_teams()
        values["langs"] = self.get_langs()
        values["products"] = products
        fields_desc = partner_obj.sudo().fields_get(["member_type_id", "gender"])
        #values["member_types"] = [(o.id, o.name) for o in member_type_obj.sudo().search([])]
        values["genders"] = fields_desc["gender"]["selection"]
        values["company"] = company

        if not values.get("member_product_id"):
            if not values.get("member_product_id", False) and products:
                values["member_product_id"] = products[0].id
        if not values.get("country_id"):
            values["country_id"] = "75"
        if not values.get("team_id"):
            _logger.debug("TEAM2: %s" % request.env['crm.team'].sudo().search([], limit=1).id)
            values["team_id"] = request.env['crm.team'].sudo().search([], limit=1).id or ''
        if not values.get("activities_country_id"):
            values["activities_country_id"] = "75"
        if not values.get("lang"):
            values["lang"] = 'fr_FR'

        comp = request.env["res.company"]._company_default_get()
        #  values.update(
        #     {
        #         "display_data_policy": comp.display_data_policy_approval,
        #         "data_policy_required": comp.data_policy_approval_required,
        #         "data_policy_text": comp.data_policy_approval_text,
        #         "display_internal_rules": comp.display_internal_rules_approval,
        #         "internal_rules_required": comp.internal_rules_approval_required,
        #         "internal_rules_text": comp.internal_rules_approval_text,
        #     }
        # )
        return values

    def get_membership_products(self, is_company):
        product_obj = request.env["product.template"]
        products = product_obj.sudo().get_web_member_products(is_company)

        return products

    def get_countries(self):
        countries = request.env["res.country"].sudo().search([])

        return countries
    
    def get_teams(self):
        teams = request.env["crm.team"].sudo().search([])
        _logger.debug("TEAM2: %s" % teams)
        return teams

    def get_langs(self):
        langs = request.env["res.lang"].sudo().search([])
        return langs

    def get_selected_membership(self, kwargs):
        prod_obj = request.env["product.template"]
        product_id = kwargs.get("member_product_id")
        return prod_obj.sudo().browse(int(product_id)).product_variant_ids[0]

    def validation(  # noqa: C901 (method too complex)
        self, kwargs, logged, values, post_file
    ):
        user_obj = request.env["res.users"]
        partner_obj = request.env["res.partner"]

        redirect = "lcc_members_website.becomemember"

        email = kwargs.get("email")
        is_company = kwargs.get("is_company") == "on"

        if is_company:
            is_company = True
            redirect = "lcc_members_website.becomecompanymember"
            email = kwargs.get("company_email")
       
        if not logged and email:
            user = user_obj.sudo().search(["|", ("login", "=", email), ("partner_id.email", "=", email)])
            partner = partner_obj.sudo().search([("email", "=", email)], limit=1)

            if user:
                values = self.fill_values(values, is_company, logged)
                values.update(kwargs)
                values["error_msg"] = _(
                    "There is an existing account for this"
                    " mail address. Please login before "
                    "fill in the form"
                )

                return request.render(redirect, values)
            else:
                if partner:
                    values = self.fill_values(values, is_company, logged)
                    values.update(kwargs)
                    values["error_msg"] = _(
                        "There is an existing member for this"
                        " mail address. Please create an account and log in before "
                        "fill in the form"
                    )

                    return request.render(redirect, values)


                confirm_email = kwargs.get("confirm_email")
                if email != confirm_email:
                    values = self.fill_values(values, is_company, logged)
                    values.update(kwargs)
                    values["error_msg"] = _(
                        "The email and the confirmation "
                        "email doesn't match.Please check "
                        "the given mail addresses"
                    )
                    return request.render(redirect, values)

        # There's no issue with the email, so we can remember the confirmation email
        values["confirm_email"] = email
        company = request.website.company_id
        
        # LOKAVALUTO TODO check the subscription's amount
        if kwargs.get("total_membership") and float(kwargs.get("total_membership")) <=0:
            values = self.fill_values(values, is_company, logged)
            values["error_msg"] = _(
                "Total amount should be > 0"
            )
            return request.render(redirect, values)
        
        # total_amount = float(kwargs.get("total_membership"))
       
        return True

    @http.route(
        ["/subscription/get_member_product"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def get_member_product(self, member_product_id, **kw):
        product_template = request.env["product.template"]
        product = product_template.sudo().browse(int(member_product_id))
        return {
            product.id: {
                "list_price": product.list_price,
                "dynamic_price": product.dynamic_price,
            }
        }

    @http.route(
        ["/membership/subscribe_member"],
        type="http",
        auth="public",
        website=True,
    )
    def membership_subscription(self, **kwargs):
        attach_obj = request.env["ir.attachment"]
        partner_obj = request.env["res.partner"]
        partner_values = {}
        sale_order = request.website.sale_get_order(force_create=True)

        _logger.debug("KWARGS %s" % kwargs)
        logged = kwargs.get("logged") == "on"
        is_company = kwargs.get("is_company") == "on"
        values = {}
        # List of file to add to ir_attachment once we have the ID
        post_file = []
        # Info to add after the message
        post_description = []

        response = self.validation(kwargs, logged, values, post_file)
        if response is not True:
            _logger.debug("Reponse: %s" % response)
            return response

        lastname = kwargs.get("lastname").upper()
        firstname = kwargs.get("firstname").title()
        # IF PUBLIC USER
        if sale_order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            
            for field in _PARTNER_FORM_FIELD:
                if kwargs.get(field):
                    partner_values[field] = kwargs.pop(field)
           
            partner_values["name"] = firstname + " " + lastname
            partner_values["lastname"] = lastname
            partner_values["first"] = firstname

            partner_id = partner_obj.sudo().create(partner_values)
            sale_order.partner_id = partner_id
            sale_order.onchange_partner_id()
            # This is the *only* thing that the front end user will see/edit anyway when choosing billing address
            sale_order.partner_invoice_id = partner_id
            

        
       
        for field_name, field_value in kwargs.items():
            if hasattr(field_value, "filename"):
                post_file.append(field_value)
            elif field_name in _EXTRA_FIELDS and field_name not in _BLACKLIST:
                values[field_name] = field_value
            # allow to add some free fields or blacklisted field like ID
            elif field_name not in _TECHNICAL:
                post_description.append(
                    "{}: {}".format(field_name, field_value)
                )

      

        
        
        already_member = False
        if logged:
            partner = request.env.user.partner_id
            values["partner_id"] = partner.id
            already_member = partner.membership_state not in ['none', 'cancelled']
        elif kwargs.get("already_member") == "on":
            already_member = True

        values["already_member"] = already_member
        values["is_company"] = is_company

        if kwargs.get("data_policy_approved", "off") == "on":
            values["data_policy_approved"] = True

        if kwargs.get("internal_rules_approved", "off") == "on":
            values["internal_rules_approved"] = True

        values["name"] = firstname + " " + lastname
        values["lastname"] = lastname
        values["firstname"] = firstname
        values["source"] = "website"
        values["total_membership"] = float(kwargs.get("total_membership"))

        values["member_product_id"] = self.get_selected_membership(kwargs).id

        values["street"] = kwargs.get("street", "")

        values["order_id"] = sale_order.id
        if is_company:
            #if kwargs.get("company_register_number", is_company):
            #    values["company_register_number"] = re.sub(
            #        "[^0-9a-zA-Z]+", "", kwargs.get("company_register_number")
            #    )
            sale_order.sudo().create_comp_membership(values)
        else:
            sale_order.sudo().create_membership(values)

        if sale_order:
            for field_value in post_file:
                attachment_value = {
                    "name": field_value.filename,
                    "res_name": field_value.filename,
                    "res_model": "sale.order",
                    "res_id": subscription_id,
                    "datas": base64.encodestring(field_value.read()),
                    "datas_fname": field_value.filename,
                }
                attach_obj.sudo().create(attachment_value)
        
        
        return request.redirect("/shop/cart")

class CustomWebsiteSale(WebsiteSale):


    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True, sitemap=False)
    def confirm_order(self, **post):
        sale_order = request.website.sale_get_order(force_create=True)
        membership = any(sale_order.order_line.mapped('product_id.membership'))
        if not membership:
            res = super(CustomWebsiteSale, self).confirm_order(post)
            return res
        
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        order.onchange_partner_shipping_id()
        order.order_line._compute_tax_id()
        request.session['sale_last_order_id'] = order.id
        request.website.sale_get_order(update_pricelist=False)
        extra_step = request.website.viewref('website_sale.extra_info_option')
        if extra_step.active:
            return request.redirect("/shop/extra_info")

        return request.redirect("/shop/payment")