# -*- coding: utf-8 -*-
from odoo import http

class PartnerGogocartojs(http.Controller):
    @http.route('/partner_gogocartojs/partner_gogocartojs/', auth='public')
    def index(self, **kw):
        return "Hello, gogocartojs"

#     @http.route('/partner_gogocartojs/partner_gogocartojs/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('partner_gogocartojs.listing', {
#             'root': '/partner_gogocartojs/partner_gogocartojs',
#             'objects': http.request.env['partner_gogocartojs.partner_gogocartojs'].search([]),
#         })

#     @http.route('/partner_gogocartojs/partner_gogocartojs/objects/<model("partner_gogocartojs.partner_gogocartojs"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('partner_gogocartojs.object', {
#             'object': obj
#         })