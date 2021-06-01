from odoo import models, fields

import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'

    in_mobile_app = fields.Boolean('In the mobile map', default=False)

    app_exported_fields = []

    def _get_mobile_app_pro_domain(self, bounding_box):
        _logger.debug('############ %s' % bounding_box)
        return [('in_mobile_app', '=', True),
                ('is_company', '=', True),
                ('partner_longitude', '!=', float()),
                ('partner_latitude', '!=', float()),
                ('partner_longitude', '>', float(bounding_box.get('minLon', ''))),
                ('partner_longitude', '<', float(bounding_box.get('maxLon', ''))),
                ('partner_latitude', '>', float(bounding_box.get('minLat', ''))),
                ('partner_latitude', '<', float(bounding_box.get('maxLat', '')))]

    def in_mobile_app_button(self):
        """ Inverse the value of the field ``in_mobile_app``
            for the current instance. """
        self.in_mobile_app = not self.in_mobile_app
