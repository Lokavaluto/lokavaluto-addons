import json

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
                "engine": "comchain",
                "currency_unit_product_id": self.currency_A_unit_product.id,
            }
        )

        comchain_json_wallet_1 = json.dumps("{'wallet': 'data'}")
        self.wallet_1 = self.ResPartnerBackend.create(
            {
                "name": "comchain:1f2s34gf6sd7gq846f8fs4qv684fq3f85",
                "active": True,
                "alt_currency_id": self.currency_A.id,
                "partner_id": self.partner_roger.id,
                "comchain_id": "1f2s34gf6sd7gq846f8fs4qv684fq3f85",
                "comchain_wallet": comchain_json_wallet_1,
                "comchain_status": "pending",
                "comchain_type": 0,
                "comchain_credit_min": 0,
                "comchain_credit_max": 0,
                "comchain_message_key": "smgfsgfds3g45f3q54435f13qg",
            }
        )

    def test_activate(self):
        self.wallet_1.activate(1, -500, 10000)

        result = self.wallet_1.comchain_status == "active"
        self.assertTrue(result)

        result = self.wallet_1.comchain_type == "1"
        self.assertTrue(result)

        result = self.wallet_1.comchain_credit_min == -500
        self.assertTrue(result)

        result = self.wallet_1.comchain_credit_max == 10000
        self.assertTrue(result)

    def test_get_wallet_json_data(self):
        json_data = self.wallet_1.get_wallet_json_data()

        expected_result = {
            "type": "comchain:Currency A",
            "accounts": [
                {
                    "wallet": "{'wallet': 'data'}",
                    "message_key": "smgfsgfds3g45f3q54435f13qg",
                    "active": False,  # XXXssai: I don't understand why it is not active...
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
