from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel


class StatsFilter(Datamodel):
    _name = "stats.filter"

    start_date = fields.Date(required=False, allow_none=True)
    end_date = fields.Date(required=False, allow_none=True)
