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
                "ident": "currencyA",
                "active": True,
                "engine": "foo",
                "currency_unit_product_id": self.currency_A_unit_product.id,
            }
        )

    def test_get_currency_json_data(self):
        json_data = self.currency_A.get_currency_json_data()

        expected_result = {
            "type": "foo:currencyA",
            "accounts": [],
            "min_credit_amount": getattr(
                self.currency_A_unit_product, "sale_min_qty", 0
            ),
            "max_credit_amount": getattr(
                self.currency_A_unit_product, "sale_max_qty", 0
            ),
        }

        result = json_data == expected_result
        self.assertTrue(result)
