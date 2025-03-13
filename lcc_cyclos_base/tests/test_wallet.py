from odoo.addons.component.tests.common import TransactionComponentCase


class TestResWallet(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]

        self.partner_roger = self.ResPartner.create({"name": "Roger"})
        self.currency_A_unit_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.currency_A = self.ResAltCurrency.create(
            {
                "name": "Currency A",
                "active": True,
                "engine": "cyclos",
                "currency_unit_product_id": self.currency_A_unit_product.id,
                "cyclos_server_url": "https://cyclos.dev3.lokavaluto.fr/api",
            }
        )

        self.wallet_1 = self.ResPartnerBackend.create(
            {
                "name": "cyclos:1f2s34gf6sd7gq846f8fs4qv684fq3f85",
                "active": True,
                "alt_currency_id": self.currency_A.id,
                "partner_id": self.partner_roger.id,
                "cyclos_id": "-1f2s34gf6sd7gq846f8fs4qv684fq3f85",
                "cyclos_create_response": "OK",
                "cyclos_status": "active",
            }
        )

    def test_get_wallet_json_data(self):
        json_data = self.wallet_1.get_wallet_json_data()

        expected_result = {
            "type": "cyclos:cyclos.dev3.lokavaluto.fr",
            "accounts": [
                {
                    "owner_id": "-1f2s34gf6sd7gq846f8fs4qv684fq3f85",
                    "url": self.currency_A.cyclos_server_url,
                    "active": True,
                    "is_topup_allowed": True,
                }
            ],
            "min_credit_amount": getattr(
                self.currency_A_unit_product, "sale_min_qty", 0
            ),
            "max_credit_amount": getattr(
                self.currency_A_unit_product, "sale_max_qty", 0
            ),
        }

        result = json_data == expected_result
        self.assertTrue(result)
