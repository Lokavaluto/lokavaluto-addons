# -*- coding: utf-8 -*-
from odoo import http


class LccMembersSearch(http.Controller):
   @http.route('/lcc_members_search/lcc_members_search/', auth='public')
   def index(self, **kw):
      return http.request.render('lcc_members_search.searchform', {})

   @http.route('/lcc_members_search/lcc_members_search/search/', auth='public',website=True, csrf=False)
   def search(self, **kw):
      memberid    = kw['member_id']
      lastname    = kw['lastname']
      firstname   = kw['firstname']
      zipcode     = kw['zipcode']
      email       = kw['email']
      allisempty  = False
      partners_is_empty = False

      if len(memberid)<=0 and len(lastname)<=0 and len(firstname)<=0 and len(zipcode)<=0 and len(email)<=0:
         print('all empty')
         allisempty = True
         partners_is_emptyfull = False
         return http.request.render('lcc_members_search.listing', {
            'partners_is_emptyfull': partners_is_emptyfull,
            'allisempty':allisempty
         })
      else: 
         if len(memberid)>0: 
            int_memberid = int(memberid) 
         else:
            int_memberid = 0
         #N°adhérent -> char , field -> ref
         #ref ou (codepostal et nom et prénom et email)
         searchfilter =[('id','=',int_memberid), 
                        '|',('name','ilike',lastname +'%'),
                           ('email','=',email),
                           ('zip','=',zipcode)
                     ]
         partners = http.request.env['res.partner'].search(searchfilter)
         partnerscount = http.request.env['res.partner'].search_count(searchfilter)
         
         if partnerscount <= 1:
            searchfilter =[('id','=',int_memberid), 
                        '|',('name','ilike',lastname +'%'),
                           ('email','=',email),
                           ('zip','=',zipcode),
                           ('membership_state', 'in', ['invoiced','paid','free'])
                     ]
            member_found = True
            partners = http.request.env['res.partner'].search(searchfilter)
            partnerscount = http.request.env['res.partner'].search_count(searchfilter)
            return http.request.render('lcc_members_search.listing', {
               'root': '/lcc_members_search/lcc_members_search',
               'partners': partners,
               'partners_is_emptyfull': partners_is_emptyfull,
               'criterias': {'int_memberid':int_memberid,'lastname':lastname,'zipcode':zipcode,'email':email},
               'searchfilter': searchfilter,
               'partnerscount':partnerscount,
               'member_found':member_found,
               'allisempty':allisempty
            })
         else
            partners_is_emptyfull = True #si 
            return http.request.render('lcc_members_search.listing', {
               'root': '/lcc_members_search/lcc_members_search',
               'partners': partners,
               'partners_is_emptyfull': partners_is_emptyfull,
               'criterias': {'int_memberid':int_memberid,'lastname':lastname,'zipcode':zipcode,'email':email},
               'searchfilter': searchfilter,
               'partnerscount':partnerscount,
               'allisempty':allisempty
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
