import json, logging

from odoo import api, fields, http, models
from odoo.http import Response, request



_logger = logging.getLogger(__name__)

class MobileApplicationJson(http.Controller):

    @http.route('/web/get_application_taxonomy',methods=['POST'], type='json', csrf=False, auth="public")
    def get_app_map_taxonomy(self, **kwargs):
        data = []
        categories = request.env['res.partner.industry'].search([('in_gogocarto','=',True)])
        for category in categories:
            data.append({
                "id": category.id,
                "name": category.name,
                "color": category.color,
                # "later":
                # "icon": category.icon  --> field icon to create in model category
            })
        return Response(json.dumps(data),content_type='application/json;charset=utf-8',status=200)


    @http.route('/web/get_application_elements',methods=['POST'], type='json', csrf=False, auth="public", website=True)
    def get_app_pro_contacts_on_area(self, **kwargs):
        data = []
        #TODO : remove .sudo()
        all_partner = request.env['res.partner'].sudo()
        bounding_box = request.jsonrequest['bounding_box']
        partners = all_partner.search(all_partner._get_mobile_app_pro_domain(**bounding_box))
        for partner in partners:
            data.append(partner.app_serialization())
        return data
