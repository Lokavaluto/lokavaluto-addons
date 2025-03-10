from odoo import api, fields, models


class AlternativeCurrency(models.Model):
    """An alternative currency is a currency managed by Odoo on a external financial backend.
    Each currency can have its own parameters and its wallets.
    """

    _name = "res.alt.currency"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Alternative Currency"

    name = fields.Char("Name", tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    ident = fields.Char("Currency Ident", tracking=True)
    engine = fields.Selection(
        [("foo", "Value defined only for testing purposes")],
        string="Transaction Engine",
        required=True,
        tracking=True,
    )  # You can find real type values in lcc_comchain_base and lcc_cyclos_base,
    uri = fields.Char("Currency URI", compute="_compute_currency_uri", tracking=True)

    activate_automatic_topup = fields.Boolean("Activate Automatic Topup", tracking=True)
    currency_unit_product_id = fields.Many2one(
        "product.product",
        string="Currency Unit Product",
        tracking=True,
    )
    commission_product_id = fields.Many2one(
        "product.product",
        string="Commission Product",
        tracking=True,
    )

    @api.depends("engine", "ident")
    def _compute_currency_uri(self):
        for cur in self:
            cur.uri = "%s://%s" % (cur.engine, cur.ident)

    def _safe_wallet_partners(self):
        return []
