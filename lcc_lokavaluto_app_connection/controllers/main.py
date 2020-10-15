from odoo import http, models, fields, api
from odoo.http import Response, request

import json

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


    @http.route('/web/get_application_elements',methods=['POST'], type='json', csrf=False, auth="public")
    def get_app_pro_contacts_on_area(self, **kwargs):
        data = []
        all_partner = request.env['res.partner']
        bounding_box = kwargs.get("bounding_box", {})
        partners = all_partner.search(all_partner._get_mobile_app_pro_domain(**bounding_box))
        for partner in partners:
            data.append({
                "autocompleteLabel": partner._get_autocompleteLabel(), 
                "city":partner.city, 
                "phones": [partner.phone, partner.mobile],
                "adherent": partner._is_partner_adherent(),
                #TODO "mainICC":,
                #TODO "keywords":[],
                "name": partner.name,
                "addresse":{
                    #TODO "id":,
                    "street1":partner.street,
                    "street2":partner.street2,
                    "latitude":partner.partner_latitude,
                    "longitude":partner.partner_longitude,
                    "zipCity":{
                        #TODO "id":,
                        "zipCode":partner.zip,
                        "city":partner.city,
                        "name": partner.zip + partner.city
                    },
                },
                "excerpt": partner.website_short_description,
                "description": partner.website_description,
                "image": partner.image,
                #TODO firstLogin: true,
                "url": partner.website_url, 
                "id": partner.id,
                #TODO "username": "Pr0177",
                "email": partner.email
                #TODO "lastLogin": null,
                #TODO "roles": ["ROLE_PRO", "ROLE_USER"],
                #TODO "enabled": false      
            })  
        return Response(json.dumps(data),content_type='application/json;charset=utf-8',status=200)