# -*- coding: utf-8 -*-
import logging

from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request


class AuthSignupHome(AuthSignupHome):
    def do_signup(self, qcontext):
        if qcontext.get("firstname"):
            """Shared helper that creates a res.partner out of a token"""
            # The only change compared to the parent function is the addition of the keys of the new field
            values = {
                key: qcontext.get(key)
                for key in ("login", "name", "password", "firstname")
            }
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
