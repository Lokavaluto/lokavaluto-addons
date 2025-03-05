from odoo.addons.component.tests.common import TransactionComponentCase


class TestResAltCurrency(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]

        self.currency_A_unit_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.currency_A = self.ResAltCurrency.create(
            {
                "name": "Currency A",
                "active": True,
                "engine": "foo",
                "currency_unit_product_id": self.currency_A_unit_product.id,
            }
        )
