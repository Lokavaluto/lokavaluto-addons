import json, logging

from odoo import http, models, fields, api
from odoo.http import Response, request

_logger = logging.getLogger(__name__)

class PartnerGogocartojs(http.Controller):


    @http.route('/web/get_gogocarto_elements',methods=['POST'], type='json', csrf=False, auth="public", website=True)
    def get_gogocarto_element(self):
        data = []
        all_partner = request.env['res.partner'].sudo()
        partners = all_partner.search(all_partner._get_gogocarto_domain())
        for partner in partners:
            data.append({
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "website": partner.website,
                "phone": partner.phone,
                "mobile": partner.mobile,
                "street1":partner.street,
                "street2":partner.street2,
                "zipCode":partner.zip,
                "city":partner.city,
                "latitude":partner.partner_latitude,
                "longitude":partner.partner_longitude,
                "local_group":partner.team_id.name
                "date_convention_signature": partner.convention_signature_date,
                "description": partner.detailled_activity,
                "details": partner.member_comment
            })
        return json.dumps(data)

