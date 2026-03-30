import json
from minimock import mock, Mock, restore
from unittest.mock import patch
from odoo.addons.component.tests.common import TransactionComponentCase
from pyc3l import Pyc3l, Wallet  # noqa: F401 -- Wallet needed by minimock namespace lookup


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
                "comchain_wallet_pwd": "strong_password",
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

        # Wallet status should be undefined when created
        self.assertFalse(wallet.comchain_status)

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
                    "status": False,
                    "comchain": {
                        "accountType": 0,
                        "status": False,
                        "lowLimit": 0,
                        "highLimit": 0,
                    },
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

    def test_send_nant_transaction(self):
        # Create data
        pyc3l = Pyc3l()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)

        # Create destination wallet
        dest_partner = self._create_res_partner("Destination")
        dest_wallet = self._create_res_partner_backend(dest_partner, currency, ident="12345")

        # Mock the wallet data and the transaction data returned by Pyc3l
        mock_wallet = Mock(
            "wallet",
            unlock=Mock("unlock"),
            transferNant=Mock("transferNant",returns="tx_hash_123")
        )
        mock("Wallet.from_json", returns=mock_wallet)

        # Mock the check_transaction_content method
        with patch(
            "odoo.addons.lcc_comchain_base.models.wallet.check_transaction_content", return_value=False
        ):
            # Send nant transaction
            res = wallet.send_nant_transaction(dest_wallet, 100)

            self.assertEqual(res, "tx_hash_123")

        restore()
