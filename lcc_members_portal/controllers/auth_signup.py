# -*- coding: utf-8 -*-
import logging

from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request


class AuthSignupHome(AuthSignupHome):
    def get_auth_signup_qcontext(self):
        qcontext = super(AuthSignupHome, self).get_auth_signup_qcontext()
        qcontext["companies"] = request.env["res.company"].sudo().search([])
        qcontext["specific_user_account"] = request.website.specific_user_account
        return qcontext

    def do_signup(self, qcontext):
        if qcontext.get("firstname") or qcontext.get("company_id"):
            """Shared helper that creates a res.partner out of a token"""
            # New fields added in the values
            values = {
                key: qcontext.get(key)
                for key in ("login", "name", "password", "firstname", "company_id")
            }
            if qcontext.get("company_id"):
                values["company_ids"] = [(6, 0, [qcontext.get("company_id")])]
            if not values:
                raise UserError(_("The form was not properly filled in."))
            if values.get("password") != qcontext.get("confirm_password"):
                raise UserError(_("Passwords do not match; please retype them."))
            supported_langs = [
                lang["code"]
                for lang in request.env["res.lang"].sudo().search_read([], ["code"])
            ]
            if request.lang in supported_langs:
                values["lang"] = request.lang
            self._signup_with_values(qcontext.get("token"), values)
            request.env.cr.commit()
        else:
            super(AuthSignupHome, self).do_signup(qcontext)
