from odoo import api, fields, models


class CreateCyclosWallet(models.TransientModel):
    _name = "create.cyclos.wallet"
    _description = (
        "wizard to select the currency on which to create a new Cyclos wallet."
    )

    @api.model
    def _default_partner_id(self):
        return self.env["res.partner"].browse(self._context.get("active_ids"))

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        default=_default_partner_id,
    )
    alt_currency_id = fields.Many2one(
        "res.alt.currency",
        string="Currency",
        required=True,
        domain="[('active', '=', True), ('engine', '=', 'cyclos')]",
    )

    def create_cyclos_wallet(self) -> None:
        self.partner_id.cyclos_add_user(self.alt_currency_id)
