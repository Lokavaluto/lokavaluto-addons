# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.http import request


class CustomerBadge(models.AbstractModel):
    _name = 'report.lcc_members_qr.member_qr_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        dat = [request.env['res.partner'].browse(data['data'])]
        print(dat)
        return {
            'data': dat,
        }
