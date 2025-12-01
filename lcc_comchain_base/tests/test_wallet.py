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

    def test_is_transaction_hash_ok(self):
        """ Test is_transaction_hash() for a valid transaction. """

        # Create data
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)

        # Launch check on a real transaction hash
        res = wallet.is_transaction_hash(
            "0x85f8dfd7e5eab0fe66145ffb0ef3435c75875943b4b589bb0ee6042b4efb1e2e"
        )
        self.assertTrue(res)

    def test_is_transaction_hash_ko(self):
        """ Test is_transaction_hash() for an invalid transaction. """

        # Create data
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)

        # Launch check on a wrong transaction hash
        res = wallet.is_transaction_hash(
            "LoremIpsum"
        )
        self.assertFalse(res)

    def test_check_transaction_content_ok(self):
        """ Test check_transaction_content() for a valid transaction. """

        # Create data
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)

        # Mock a transaction response content
        mock_tx = Mock("transaction", data={"recieved": 1000})
        mock("Pyc3l.Transaction", returns=mock_tx)

        # Check the transaction
        response = "0x85f8dfd7e5eab0fe66145ffb0ef3435c75875943b4b589bb0ee6042b4efb1e2e"
        res = wallet.check_transaction_content(response, 10.00)
        self.assertFalse(res)
        restore()

    def test_check_transaction_content_ko_wrong_amount(self):
        """ Test check_transaction_content() for a transaction with wrong amount. """

        # Create data
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)

        # Mock a transaction response content
        mock_tx = Mock("transaction", data={"recieved": 10})
        mock("Pyc3l.Transaction", returns=mock_tx)

        # Check the transaction
        response = "0x85f8dfd7e5eab0fe66145ffb0ef3435c75875943b4b589bb0ee6042b4efb1e2e"
        res = wallet.check_transaction_content(response, 10.00)
        self.assertEqual(
            res,
            "Order sent, but checking transaction record returned as an unexepected "
            "amount of 10 received."
        )
        restore()

    def test_check_transaction_content_ko_missing_recieved(self):
        """ Test check_transaction_content() for a transaction with missing field. """

        # Create data
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)

        # Mock a transaction response content
        mock_tx = Mock("transaction", data={"value": 10})
        mock("Pyc3l.Transaction", returns=mock_tx)

        # Check the transaction
        response = "0x85f8dfd7e5eab0fe66145ffb0ef3435c75875943b4b589bb0ee6042b4efb1e2e"
        res = wallet.check_transaction_content(response, 10.00)
        self.assertEqual(
            res,
            "Max retry reached to get transaction info (10 retries)"
        )
        restore()
