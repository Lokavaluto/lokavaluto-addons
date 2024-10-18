import logging

from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request
from odoo.exceptions import UserError


class AuthSignupHome(AuthSignupHome):
    def get_auth_signup_qcontext(self):
        qcontext = super(AuthSignupHome, self).get_auth_signup_qcontext()
        if request.params.get("firstname"):
            qcontext["firstname"] = request.params.get("firstname")
        if request.params.get("lastname"):
            qcontext["lastname"] = request.params.get("lastname")
        return qcontext

    def do_signup(self, qcontext):
        if qcontext.get("firstname") or qcontext.get("lastname"):
            """Shared helper that creates a res.partner out of a token"""
            # Addition of the keys of the new fields
            values = {
                key: qcontext.get(key)
                for key in ("login", "lastname", "password", "firstname")
            }
            # Name computation depending on the values
            if qcontext.get("firstname") and qcontext.get("lastname"):
                values["name"] = (
                    qcontext.get("firstname") + " " + qcontext.get("lastname")
                )
            elif qcontext.get("firstname"):
                values["name"] = qcontext.get("firstname")
            elif qcontext.get("lastname"):
                values["name"] = qcontext.get("lastname")
            # Next lines are the same than in parent function
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
