from odoo import models


# I had to add this AbstractModel to make my tests work
# But it's supposed to be created since the beginning of the use of Component
# cf https://dev.to/guewen/introduction-to-odoo-components-bn0
class LokavalutoPrivateServicesCollection(models.AbstractModel):
    _name = "lokavaluto.private.services"
    _inherit = "collection.base"
