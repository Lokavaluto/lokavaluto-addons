import json
from unittest.mock import patch
from odoo.addons.component.tests.common import TransactionComponentCase

class TestCreditRequest(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]
        self.ResCreditRequest = self.env["credit.request"]

        self.comchain_currency_unit_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()

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

    def _create_res_partner(self, name="John Doe"):
        return self.ResPartner.create({"name": name})

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

    def _create_credit_request(self, wallet, amount=100):
        return self.env["credit.request"].create(
            {
                "wallet_id": wallet.id,
                "amount": amount,
            }
        )

    def test_check_still_in_error_1(self):
        """Test check_still_in_error method when credit request is still in error."""

        # Create data
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)
        credit_request = self._create_credit_request(wallet, amount=100)

        # Simulate credit request in error
        credit_request.transaction_data = "tx_hash_123"
        credit_request.state = "error"

        # Mock the check_transaction_content method
        with patch(
            "odoo.addons.lcc_comchain_base.models.credit_request.check_transaction_content",
            return_value="Max retry reached to get transaction info (10 retries)"
        ):
            # Check still in error
            credit_request.check_still_in_error()

            # Assert state is still error
            self.assertEqual(credit_request.state, "error")

    def test_check_still_in_error_2(self):
        """Test check_still_in_error method when credit request is no longer in error."""

        # Create data
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)
        credit_request = self._create_credit_request(wallet, amount=100)

        # Simulate credit request in error
        credit_request.transaction_data = "tx_hash_123"
        credit_request.state = "error"

        # Mock the check_transaction_content method
        with patch(
            "odoo.addons.lcc_comchain_base.models.credit_request.check_transaction_content",
            return_value=False
        ):
            # Check still in error
            credit_request.check_still_in_error()

            # Assert state is now done
            self.assertEqual(credit_request.state, "done")

    def test_check_still_in_error_3(self):
        """Test check_still_in_error method when credit request without transaction_data."""

        # Create data
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)
        credit_request = self._create_credit_request(wallet, amount=100)

        # Simulate credit request in error
        credit_request.state = "error"

        # Check still in error
        credit_request.check_still_in_error()

        # Assert state is still error
        self.assertEqual(credit_request.state, "error")
