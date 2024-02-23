from odoo.addons.base_rest.controllers import main


class LokavalutoStatsPublicApiController(main.RestController):
    _root_path = "/lokavaluto_api/public/stats/"
    _collection_name = "lokavaluto.public.stats.services"
    _default_auth = "public"


class LokavalutoStatsPrivateApiController(main.RestController):
    _root_path = "/lokavaluto_api/private/stats/"
    _collection_name = "lokavaluto.private.stats.services"
    _default_auth = "api_key"
