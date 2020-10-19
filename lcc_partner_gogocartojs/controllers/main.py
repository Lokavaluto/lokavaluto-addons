import json, logging

from odoo import http, models, fields, api
from odoo.http import Response, request

_logger = logging.getLogger(__name__)

class PartnerGogocartojs(http.Controller):


    @http.route('/web/get_gogocarto_elements',methods=['POST'], type='json', csrf=False, auth="public", website=True)
    def get_gogocarto_element(self):
        data = []
        partners = all_partner.search([])
        for partner in partners:
            data.append({
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "website": partner.website,
                "phone": partner.phone,
                "mobile": partner.mobile,
                "convention_signature": partner.convention_signature_date,
                "description": partner.detailled_activity,
                "details": partner.member_comment
            })
        # return Response(json.dumps(data),content_type='application/json;charset=utf-8',status=200)
        return json.dumps(data)

