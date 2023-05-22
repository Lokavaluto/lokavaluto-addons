# -*- coding: utf-8 -*-

from marshmallow import fields

from odoo.addons.datamodel.core import Datamodel


class StatsFilter(Datamodel):
    _name = "stats.filter"

    value = fields.String(required=False, allow_none=True)
    start_sate = fields.Date(required=False, allow_none=True)
    end_sate = fields.Date(required=False, allow_none=True)
