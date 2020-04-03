# -*- coding: utf-8 -*-
from odoo import http
#@RBO

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

      #init all variables here
      allisempty  = False
      partners_is_empty = False
      
      #test for field content
      if len(memberid)<=0 and len(lastname)<=0 and len(firstname)<=0 and len(zipcode)<=0 and len(email)<=0:
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
         #replace id field with ref one and memberid string variable
         searchfilter =[('id','=',int_memberid), 
                        '|',('lastname','ilike',lastname +'%'),
                           ('firstname','ilike',firstname +'%'),
                           ('email','=',email),
                           ('zip','=',zipcode)
                     ]
         partners = http.request.env['res.partner'].search(searchfilter)
         partnerscount = http.request.env['res.partner'].search_count(searchfilter)
         
         if partnerscount == 1:
            searchfilter =[('id','=',int_memberid), 
                           '|',('lastname','ilike',lastname +'%'),
                              ('firstname','ilike',firstname +'%'),
                              ('email','=',email),
                              ('zip','=',zipcode),
                              ('membership_state', 'in', ['invoiced','paid','free'])
                     ]
            
            member_found = True
            partners = http.request.env['res.partner'].search(searchfilter)
            partnerscount = http.request.env['res.partner'].search_count(searchfilter)
            return http.request.render('lcc_members_search.listing', {
               #'partners': partners,
               'partners_is_one': True,
               #'searchfilter': searchfilter,
               #'partnerscount':partnerscount,
               'member_found':member_found,
            })
         else:
            partners_is_emptyfull = True 
            return http.request.render('lcc_members_search.listing', {
               'partners': partners,
               'partners_is_emptyfull': partners_is_emptyfull
               #'searchfilter': searchfilter,
               #'partnerscount':partnerscount,
            })