from odoo import models


# Anchor for the public services collection so base_rest can
# discover its components (auth.service, config.service, …) at
# registry-init time. Mirrors lokavaluto_private_services_collection.
# Without this, the public services exist only as Component subclasses
# but are not registered into the URL routing map, and every public
# endpoint returns 404 in tests (the runtime works because dispatch
# resolves components lazily on the first request).
class LokavalutoPublicServicesCollection(models.AbstractModel):
    _name = "lokavaluto.public.services"
    _description = "Public services collection"
    _inherit = "collection.base"
