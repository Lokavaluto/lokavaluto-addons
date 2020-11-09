import json, logging

from odoo import http, models, fields, api
from odoo.http import Response, request

_logger = logging.getLogger(__name__)

class PartnerGogocartojs(http.Controller):

    @http.route('/web/get_gogocarto_elements',methods=['POST'], type='json', csrf=False, auth="public", website=True)
    def get_gogocarto_elements(self):
        data = self.__get_partner()
        return data
    
    @http.route('/web/get_http_gogocarto_elements',methods=['GET'], type='http', csrf=False, auth="public", website=True)
    def get_gogocarto_elements_http(self):
        data = self.__get_partner()
        return Response(json.dumps(data))

    def __get_partner(self):
        data = []
        all_partner = request.env['res.partner'].sudo()
        partners = all_partner.search(all_partner._get_gogocarto_domain())
        all_partner.debug_field_exported()
        for partner in partners:
            data.append(partner.gogocarto_serialization())
        return data

