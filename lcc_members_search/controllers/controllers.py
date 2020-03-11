# -*- coding: utf-8 -*-
# from odoo import http


# class LccMembersSearch(http.Controller):
#     @http.route('/lcc_members_search/lcc_members_search/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/lcc_members_search/lcc_members_search/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('lcc_members_search.listing', {
#             'root': '/lcc_members_search/lcc_members_search',
#             'objects': http.request.env['lcc_members_search.lcc_members_search'].search([]),
#         })

#     @http.route('/lcc_members_search/lcc_members_search/objects/<model("lcc_members_search.lcc_members_search"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lcc_members_search.object', {
#             'object': obj
#         })
