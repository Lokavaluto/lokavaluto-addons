# -*- coding: utf-8 -*-
from odoo import http


class LccMembersSearch(http.Controller):
   @http.route('/lcc_members_search/lcc_members_search/', auth='public')
   def index(self, **kw):
      #return "Hello, world1"
      return http.request.render('lcc_members_search.index', {
         'teachers': ["Diana Padilla", "Jody Caroll", "Lester Vaughn"],
      })

   @http.route('/lcc_members_search/lcc_members_search/objects/', auth='public')
   def list(self, **kw):
      return http.request.render('lcc_members_search.listing', {
         'root': '/lcc_members_search/lcc_members_search',
         'objects': http.request.env['lcc_members_search.lcc_members_search'].search([]),
      })

   @http.route('/lcc_members_search/lcc_members_search/search/', auth='public',website=True, csrf=False)
   def search(self, **kw):
      memberid = kw['member_id']
      results = http.request.env['res.partner'].search([('id', '==', 1)])
      return "Search page,{} ".format(kw['member_id'])
      #return http.request.render('lcc_members_search.listing', {
      #   'root': '/lcc_members_search/lcc_members_search',
      #  'objects': http.request.env['lcc_members_search.lcc_members_search'].search([]),
      #})
      # retrieve the membre id to search 


#     @http.route('/lcc_members_search/lcc_members_search/objects/<model("lcc_members_search.lcc_members_search"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lcc_members_search.object', {
#             'object': obj
#         })
