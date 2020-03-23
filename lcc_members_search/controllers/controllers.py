# -*- coding: utf-8 -*-
from odoo import http


class LccMembersSearch(http.Controller):
   @http.route('/lcc_members_search/lcc_members_search/', auth='public')
   def index(self, **kw):
      return http.request.render('lcc_members_search.searchform', {
         'teachers': ["Diana Padilla", "Jody Caroll", "Lester Vaughn"],
      })

   @http.route('/lcc_members_search/lcc_members_search/search/', auth='public',website=True, csrf=False)
   def search(self, **kw):
      memberid    = kw['member_id']
      lastname  = kw['lastname']
      zipcode     = kw['zipcode']
      email       = kw['email']
      int_memberid = int(memberid)
      partners = http.request.env['res.partner'].search([]),
      partners_is_empty = True
      #if partners.count() <=0 partners_is_empty = True

      #results = self.env['res.partner'].search(['is_company', '=', True])
      #return "Search page,{} ".format(results)
      return http.request.render('lcc_members_search.listing', {
         'root': '/lcc_members_search/lcc_members_search',
         'partners': http.request.env['res.partner'].search([]),
         'partners_is_empty': partners_is_empty,
         'criterias',{'int_memberid',int_memberid,'lastname':lastname,'zipcode':zipcode,'email':email}
      })

   #@http.route('/lcc_members_search/lcc_members_search/objects/', auth='public')
   #def list(self, **kw):
   #   return http.request.render('lcc_members_search.listing', {
   #      'root': '/lcc_members_search/lcc_members_search',
   #      'objects': http.request.env['lcc_members_search.lcc_members_search'].search([]),
   #   })

#     @http.route('/lcc_members_search/lcc_members_search/objects/<model("lcc_members_search.lcc_members_search"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lcc_members_search.object', {
#             'object': obj
#         })
