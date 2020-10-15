from odoo import http, _
from odoo.http import request
from odoo.osv import expression

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
    # def constructTupleFilter(self, field,op,value,ilikeOp):
    #     if(len(value)>0): 
    #         emailtuple=[(field, op, value+ilikeOp)] 
    #     else: 
    #         emailtuple=[(field, "=", True)]

    def search(self, **kw):
        memberid = kw["member_id"]
        lastname = kw["lastname"]
        firstname = kw["firstname"]
        zipcode = kw["zipcode"]
        email = kw["email"]

        # init all variables here
        allisempty = False
        partners_is_emptyfull = False

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
            filterarray = []
            if(len(memberid)>=0):
                filterarray.append([("ref", "=", memberid)])
            else:
                if(len(email)>0): 
                    filterarray.append([("email", "=", email)])
                if(len(zipcode)>0): 
                    filterarray.append([("zip", "=", zipcode)])
                if(len(lastname)>0): 
                    filterarray.append([("lastname", "ilike", lastname + "%")])
                if(len(firstname)>0): 
                    filterarray.append([("firstname", "ilike", firstname + "%")])
           
            searchfilter = expression.AND(filterarray)   
            partners = http.request.env["res.partner"].search(searchfilter)
            partnerscount = http.request.env["res.partner"].search_count(searchfilter)
            
            #filterstr = searchfilter[0:len(searchfilter)]
            #print('filterstr : ' + ''.join(filterstr))
            #for a in searchfilter:
            #    filterstr = filterstr + a
            if partnerscount == 1:
                # searchfilter = [
                #     ("ref", "=", memberid),
                #     "|",
                #     ("lastname", "ilike", lastname + "%"),
                #     ("firstname", "ilike", firstname + "%"),
                #     ("email", "=", email),
                #     ("zip", "=", zipcode),
                #     ("membership_state", "in", ["invoiced", "paid", "free"])
                # ]
                filterarray.append([("membership_state", "in", ["invoiced", "paid", "free"])])
                searchfilter = expression.AND(filterarray)
                member_found = True
                partners = http.request.env["res.partner"].sudo().search(searchfilter)
                partnerscount = http.request.env["res.partner"].sudo().search_count(searchfilter)
                
                #filterstr = searchfilter[0:len(searchfilter)]
                #for aTuple in searchfilter:
                #    filterstr = filterstr + "," + aTuple
                
                return request.render(
                    "lcc_members_search.listing",
                    {
                        "member_found": member_found,
                        #"filter": ''.joint(filterstr),
                        "partners": str(partners),
                        "partnerscount" : partnerscount
                    },
                )
            else:
                partners_is_emptyfull = True
                return request.render(
                    "lcc_members_search.listing",
                    {
                        #"filter": ''.join(filterstr),
                        "partners": str(partners),
                        "email":email,
                        "partners_is_emptyfull": partners_is_emptyfull,
                        "partnerscount" : partnerscount
                    },
                )
