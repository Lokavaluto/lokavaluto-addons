from odoo.addons.base_rest.controllers import main


class LokavalutoPublicApiController(main.RestController):
    _root_path = "/lokavaluto_api/public/"
    _collection_name = "lokavaluto.public.services"
    _default_auth = "public"


class LokavalutoPrivateApiController(main.RestController):
    _root_path = "/lokavaluto_api/private/"
    _collection_name = "lokavaluto.private.services"
    _default_auth = "api_key"
