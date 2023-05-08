from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel


class StatsFilter(Datamodel):
    """
    Describes stats API query parameters
    """

    _name = "stats.filter"

    start_date = fields.Date(
        required=False,
        allow_none=True,
        description="date included, format YYYY-MM-DD",
    )
    end_date = fields.Date(
        required=False,
        allow_none=True,
        description="date included, format YYYY-MM-DD",
    )
