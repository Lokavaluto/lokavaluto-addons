# -*- coding: utf-8 -*-

try:
    import qrcode
except ImportError:
    qrcode = None
try:
    import base64
except ImportError:
    base64 = None
from io import BytesIO

from odoo import models, fields, api,_
from odoo.exceptions import UserError


class ResPartnerBackend(models.Model):
    _inherit = "res.partner.backend"

    qr = fields.Binary(string="Wallet QR code", store=True, copy=False)

    @api.model
    def create(self, vals):
        res = super(ResPartnerBackend, self).create(vals)
        res.generate_qr()
        return res

    def _get_qr_content(self):
        self.ensure_one()
        content = {
            "rp": self.partner_id.id,
            "rpb": self.name,
        }
        return content

    def generate_qr(self):
        if qrcode and base64:
            for record in self:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=2,
                )
                qr_content = record._get_qr_content()

                qr.add_data(qr_content)
                qr.make(fit=True)

                img = qr.make_image()
                temp = BytesIO()
                img.save(temp, format="PNG")
                qr_image = base64.b64encode(temp.getvalue())
                record.write(
                    {
                        "qr": qr_image,
                    }
                )
        else:
            raise UserError(
                _(
                    "Necessary requirements are not satisfied - Need qrcode and base64 Python libraries"
                )
            )

    @api.model
    def _cron_generate_missing_qr(self):
        self.search([("qr", "=", False)]).generate_qr()
