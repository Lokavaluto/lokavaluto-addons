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
                "ident": "currencyA",
                "active": True,
                "engine": "cyclos",
                "currency_unit_product_id": self.currency_A_unit_product.id,
                "cyclos_server_url": "https://cyclos.dev3.lokavaluto.fr/api",
            }
        )

    def test_create_wallet(self):
        cyclos_id = "1f2s34gf6sd7gq846f8fs4qv684fq3f85"

        # Create wallet
        wallet_1 = self.ResPartnerBackend.create(
            {
                "name": f"cyclos:{cyclos_id}",
                "active": True,
                "alt_currency_id": self.currency_A.id,
                "partner_id": self.partner_roger.id,
                "cyclos_id": f"-{cyclos_id}",
                "cyclos_create_response": "OK",
                "cyclos_status": "active",
            }
        )
        self.assertEqual(wallet_1.cyclos_status, "active")
        self.assertEqual(wallet_1.cyclos_id, f"-{cyclos_id}")


    def test_get_wallet_json_data(self):
        cyclos_id = "1f2s34gf6sd7gq846f8fs4qv684fq3f85"

        # Create wallet
        wallet_1 = self.ResPartnerBackend.create(
            {
                "name": f"cyclos:{cyclos_id}",
                "active": True,
                "alt_currency_id": self.currency_A.id,
                "partner_id": self.partner_roger.id,
                "cyclos_id": f"-{cyclos_id}",
                "cyclos_create_response": "OK",
                "cyclos_status": "active",
            }
        )
        json_data = wallet_1.get_wallet_json_data()

        expected_result = {
            "type": "cyclos:cyclos.dev3.lokavaluto.fr",
            "accounts": [
                {
                    "owner_id": f"-{cyclos_id}",
                    "url": self.currency_A.cyclos_server_url,
                    "active": True,
                    "is_topup_allowed": True, # Default value when no topup rules
                    "is_payment_request_allowed": False, # Default value when no payment request allowed rules
                }
            ],
            "min_credit_amount": getattr(
                self.currency_A_unit_product, "sale_min_qty", 0
            ),
            "max_credit_amount": getattr(
                self.currency_A_unit_product, "sale_max_qty", 0
            ),
        }

        self.assertEqual(json_data, expected_result)

    def _create_payment_request_allowed_rule(self):
        self.env["payment.request.allowed.rule"].create(
            {
                "name": "Allow all",
                "wallet_domain": "[]",
                "is_payment_request_allowed": True,
            }
        )

    def test_get_wallet_json_data_payment_request_allowed(self):
        """A payment.request.allowed.rule changes is_payment_request_allowed."""
        self._create_payment_request_allowed_rule()
        cyclos_id = "1f2s34gf6sd7gq846f8fs4qv684fq3f86"
        wallet = self.ResPartnerBackend.create(
            {
                "name": f"cyclos:{cyclos_id}",
                "active": True,
                "alt_currency_id": self.currency_A.id,
                "partner_id": self.partner_roger.id,
                "cyclos_id": f"-{cyclos_id}",
                "cyclos_create_response": "OK",
                "cyclos_status": "active",
            }
        )
        json_data = wallet.get_wallet_json_data()
        self.assertTrue(json_data["accounts"][0]["is_payment_request_allowed"])
