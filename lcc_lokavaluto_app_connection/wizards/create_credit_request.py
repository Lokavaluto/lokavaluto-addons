from odoo import api, fields, models


class CreateCreditRequest(models.TransientModel):
    _name = "create.credit.request"
    _description = "create Credit Request"

    @api.model
    def _default_wallet_id(self):
        return self.env["res.partner.backend"].browse(self._context.get("active_ids"))

    amount = fields.Float("Amount", required=True)
    wallet_id = fields.Many2one(
        "res.partner.backend",
        string="Wallet",
        required=True,
        default=_default_wallet_id,
    )

    @api.multi
    def create_credit_request(self):
        values = {
            "wallet_id": self.wallet_id.id,
            "amount": self.amount,
        }
        credit_request_id = self.env["credit.request"].create(values)
        view = self.env.ref("lcc_lokavaluto_app_connection.credit_request_view_form")
        return {
            "name": "Credit request created",
            "view_type": "form",
            "view_mode": "form",
            "view_id": view.id,
            "res_model": "credit.request",
            "type": "ir.actions.act_window",
            "res_id": credit_request_id.id,
            "context": self.env.context,
        }
