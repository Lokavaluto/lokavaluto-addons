# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomCustomerPortal(CustomerPortal):
    @route(["/my/account"], type="http", auth="user", website=True)
    def account(self, redirect=None, **post):
        response = super(CustomCustomerPortal, self).account(redirect, **post)
        if post and request.httprequest.method == "POST":
            error, error_message = self.details_form_validate(post)
            if not error:
                user = request.env.user
                if post["email"] != user.login:
                    user.login = post["email"]
                    return request.redirect("/web/session/logout")
        return response
