from odoo import models


# WARNING : I had to add this AbstractModel to instantiate the PartnerService in my tests
# cf https://dev.to/guewen/introduction-to-odoo-components-bn0
class LokavalutoPrivateServicesCollection(models.AbstractModel):
    _name = "lokavaluto.private.services"
    _inherit = "collection.base"
