import json
from unittest.mock import patch

from odoo.addons.component.tests.common import TransactionComponentCase

from ..models.credit_request import RPLCMNT_TX_UNDERPRICED,INSUFFICIENT_FUNDS


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
                "comchain_message_key": "bar",
            }
        )

    def _create_credit_request(self, wallet, amount=100, error_message=None):
        vals = {"wallet_id": wallet.id, "amount": amount}
        if error_message is not None:
            vals["error_message"] = error_message
        return self.env["credit.request"].create(vals)

    # ------------------------------------------------------------------
    # check_still_in_error
    # ------------------------------------------------------------------

    def test_check_still_in_error_1(self):
        """Test check_still_in_error when the transaction is still in error."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)
        credit_request = self._create_credit_request(wallet, amount=100)

        credit_request.transaction_data = "tx_hash_123"
        credit_request.state = "error"

        with patch(
            "odoo.addons.lcc_comchain_base.models.credit_request.check_transaction_content",
            return_value="Max retry reached to get transaction info (10 retries)",
        ):
            credit_request.check_still_in_error()
            self.assertEqual(credit_request.state, "error")

    def test_check_still_in_error_2(self):
        """Test check_still_in_error when the transaction is no longer in error."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)
        credit_request = self._create_credit_request(wallet, amount=100)

        credit_request.transaction_data = "tx_hash_123"
        credit_request.state = "error"

        with patch(
            "odoo.addons.lcc_comchain_base.models.credit_request.check_transaction_content",
            return_value=False,
        ):
            credit_request.check_still_in_error()
            self.assertEqual(credit_request.state, "done")

    def test_check_still_in_error_3(self):
        """Test check_still_in_error when there is no transaction_data."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)
        credit_request = self._create_credit_request(wallet, amount=100)

        credit_request.state = "error"

        credit_request.check_still_in_error()
        self.assertEqual(credit_request.state, "error")

    # ------------------------------------------------------------------
    # _new_credit_attempt_allowed
    # ------------------------------------------------------------------

    def test_new_credit_attempt_allowed_state_not_error(self):
        """_new_credit_attempt_allowed returns False when state is not 'error'."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)
        credit_request = self._create_credit_request(
            wallet, amount=100, error_message=RPLCMNT_TX_UNDERPRICED
        )

        # State is "open" by default
        self.assertFalse(credit_request._new_credit_attempt_allowed())

        # Passing through valid transitions: open -> pending -> done
        credit_request.state = "pending"
        self.assertFalse(credit_request._new_credit_attempt_allowed())

        credit_request.state = "done"
        self.assertFalse(credit_request._new_credit_attempt_allowed())

    def test_new_credit_attempt_allowed_no_error_message(self):
        """_new_credit_attempt_allowed returns False when error_message is falsy."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)
        credit_request = self._create_credit_request(wallet, amount=100)

        credit_request.state = "error"
        # error_message defaults to False — the method should return False
        self.assertFalse(credit_request._new_credit_attempt_allowed())

    def test_new_credit_attempt_allowed_known_error_message(self):
        """_new_credit_attempt_allowed returns True for the known error message."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)
        credit_request = self._create_credit_request(wallet, amount=100)
        credit_request.state = "error"

        credit_request.error_message = RPLCMNT_TX_UNDERPRICED
        self.assertTrue(credit_request._new_credit_attempt_allowed())

        credit_request.error_message = INSUFFICIENT_FUNDS
        self.assertTrue(credit_request._new_credit_attempt_allowed())

    def test_new_credit_attempt_allowed_other_error_message(self):
        """_new_credit_attempt_allowed returns False for any other error message."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet = self._create_res_partner_backend(partner, currency)
        credit_request = self._create_credit_request(
            wallet, amount=100, error_message="Some other error"
        )

        credit_request.state = "error"
        self.assertFalse(credit_request._new_credit_attempt_allowed())
