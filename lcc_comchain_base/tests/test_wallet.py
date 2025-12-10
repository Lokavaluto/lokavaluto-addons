import json
from minimock import mock, Mock, restore
from odoo.addons.component.tests.common import TransactionComponentCase
from pyc3l import Pyc3l, Wallet


class TestResWallet(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]

        self.comchain_currency_unit_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()

    def _create_res_partner_backend(self, partner, currency, ident="98765"):
        return self.ResPartnerBackend.create(
            {
                "name": f"comchain:{ident}",
                "alt_currency_id": currency.id,
                "partner_id": partner.id,
                "comchain_id": ident,
                "comchain_wallet": json.dumps("foo"),
                "comchain_message_key": "bar"
            }
        )

    def _create_res_partner(self, name="John Doe"):
        return self.ResPartner.create({"name": name})

    def _create_alt_currency(self, ident="currency", safe_wallet_partner_id=None):
        return self.ResAltCurrency.create(
            {
                "name": ident,
                "ident": ident,
                "active": True,
                "engine": "comchain",
                "currency_unit_product_id": self.comchain_currency_unit_product.id,
            }
        )


    def test_create_and_activate_wallet(self):
        # Create data
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)

        # Wallet should be pending when created
        self.assertEqual(wallet.comchain_status, "pending")

        # Activate wallet
        wallet.activate(1, -500, 10000)
        self.assertEqual(wallet.comchain_status, "active")
        self.assertEqual(wallet.comchain_type, "1")
        self.assertEqual(wallet.comchain_credit_min, -500)
        self.assertEqual(wallet.comchain_credit_max, 10000)


    def test_get_wallet_json_data(self):
        # Create data
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)

        json_data = wallet.get_wallet_json_data()
        expected_result = {
            "type": "comchain:currency",
            "accounts": [
                {
                    "wallet": "foo",
                    "message_key": "bar",
                    "active": False,
                    "is_topup_allowed": True,
                }
            ],
            "min_credit_amount": getattr(
                self.comchain_currency_unit_product, "sale_min_qty", 0
            ),
            "max_credit_amount": getattr(
                self.comchain_currency_unit_product, "sale_max_qty", 0
            ),
        }
        self.assertEqual(json_data, expected_result)

    def test_get_wallet_balance(self):
        # Create data
        pyc3l = Pyc3l()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)

        # Mock the wallet data returned by Pyc3l
        mock_wallet = Mock("wallet", nantBalance=1)
        mock("Wallet.from_json", returns=mock_wallet)

        # Get wallet balance
        res = wallet.get_wallet_balance()

        self.assertEqual(res, {"success": True, "response": 1})
        restore()
