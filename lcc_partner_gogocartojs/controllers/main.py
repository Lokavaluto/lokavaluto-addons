import json, logging

from odoo import http, models, fields, api
from odoo.http import Response, request

_logger = logging.getLogger(__name__)

class PartnerGogocartojs(http.Controller):


    @http.route('/web/get_gogocarto_elements',methods=['POST'], type='json', csrf=False, auth="public", website=True)
    def get_gogocarto_elements(self):
        data = []
        all_partner = request.env['res.partner'].sudo()
        partners = all_partner.search(all_partner._get_gogocarto_domain())
        for partner in partners:
            data.append(partner.app_serialization())
        return data

