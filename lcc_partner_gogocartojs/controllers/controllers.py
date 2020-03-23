from odoo import http

class PartnerGogocartojs(http.Controller):
    @http.route('/partner_gogocartojs/partner_gogocartojs/', auth='public')
    def index(self, **kw):
        return "Hello, gogocartojs"

#     @http.route('/lcc_partner_gogocartojs/lcc_partner_gogocartojs/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('lcc_partner_gogocartojs.listing', {
#             'root': '/lcc_partner_gogocartojs/lcc_partner_gogocartojs',
#             'objects': http.request.env['lcc_partner_gogocartojs.lcc_partner_gogocartojs'].search([]),
#         })

#     @http.route('/lcc_partner_gogocartojs/lcc_partner_gogocartojs/objects/<model("lcc_partner_gogocartojs.lcc_partner_gogocartojs"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lcc_partner_gogocartojs.object', {
#             'object': obj
#         })