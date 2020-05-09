from odoo import http, _
from odoo.http import request


class LccMembersSearch(http.Controller):
    @http.route(
        "/lcc_members_search/",
        auth="public",
        website=True,
        type="http",
    )
    def index(self, **kw):
        return request.render("lcc_members_search.searchform", {})

    @http.route(
        "/lcc_members_search/search/",
        auth="public",
        website=True,
        csrf=False,
        type="http",
    )
    def search(self, **kw):
        memberid = kw["member_id"]
        lastname = kw["lastname"]
        firstname = kw["firstname"]
        zipcode = kw["zipcode"]
        email = kw["email"]

        # init all variables here
        allisempty = False
        partners_is_empty = False

        # test for field content
        if (
            len(memberid) <= 0
            and len(lastname) <= 0
            and len(firstname) <= 0
            and len(zipcode) <= 0
            and len(email) <= 0
        ):
            allisempty = True
            partners_is_emptyfull = False
            return request.render(
                "lcc_members_search.listing",
                {
                    "partners_is_emptyfull": partners_is_emptyfull,
                    "allisempty": allisempty
                },
            )
        else:
            # N°adhérent -> char , field -> ref
            # ref ou (codepostal et nom et prénom et email)
            # replace id field with ref one and memberid string variable
            searchfilter = [
                ("ref", "=", memberid),
                "|",
                ("lastname", "ilike", lastname + "%"),
                ("firstname", "ilike", firstname + "%"),
                ("zip", "=", zipcode),
                ("email","=",email)
                
            ]
            partners = http.request.env["res.partner"].sudo().search(searchfilter)
            partnerscount = http.request.env["res.partner"].sudo().search_count(searchfilter)

            if partnerscount == 1:
                searchfilter = [
                    ("ref", "=", memberid),
                    "|",
                    ("lastname", "ilike", lastname + "%"),
                    ("firstname", "ilike", firstname + "%"),
                    ("email", "=", email),
                    ("zip", "=", zipcode),
                    ("membership_state", "in", ["invoiced", "paid", "free"])
                ]

                member_found = True
                partners = http.request.env["res.partner"].sudo().search(searchfilter)
                partnerscount = http.request.env["res.partner"].sudo().search_count(searchfilter)
                return request.render(
                    "lcc_members_search.listing",
                    {
                        "member_found": member_found,
                        "filter": str(searchfilter),
                        "partners": str(partners),
                        "partnerscount" : partnerscount
                    },
                )
            else:
                partners_is_emptyfull = True
                return request.render(
                    "lcc_members_search.listing",
                    {
                        "filter": str(searchfilter),
                        "partners": str(partners),
                        "email":email,
                        "partners_is_emptyfull": partners_is_emptyfull,
                        "partnerscount" : partnerscount
                    },
                )
