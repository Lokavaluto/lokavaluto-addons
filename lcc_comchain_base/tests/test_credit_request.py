import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.component.tests.common import TransactionComponentCase

from ..models.credit_request import INSUFFICIENT_FUNDS, RPLCMNT_TX_UNDERPRICED
from ..models.res_alt_currency import pyc3l


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


class TestFindTopupTransactions(TransactionCase):
    """Test the on-chain lookup used to reconcile uncertain topups."""

    def setUp(self):
        super().setUp()
        currency_product = self.env.ref(
            "lcc_lokavaluto_app_connection.product_product_numeric_lcc"
        ).sudo()
        self.currency = self.env["res.alt.currency"].create(
            {
                "name": "CC Reconcile",
                "ident": "ccreconcile",
                "active": True,
                "engine": "comchain",
                "currency_unit_product_id": currency_product.id,
            }
        )
        odoo_partner = self.env["res.partner"].create({"name": "Odoo Wallet"})
        self.env["res.partner.backend"].create(
            {
                "name": "comchain:FROM",
                "ident": "FROM",
                "comchain_id": "FROM",
                "alt_currency_id": self.currency.id,
                "partner_id": odoo_partner.id,
            }
        )
        self.currency.odoo_wallet_partner_id = odoo_partner.id
        target_partner = self.env["res.partner"].create({"name": "Target"})
        self.wallet = self.env["res.partner.backend"].create(
            {
                "name": "comchain:TO",
                "ident": "TO",
                "comchain_id": "TO",
                "alt_currency_id": self.currency.id,
                "partner_id": target_partner.id,
            }
        )

    def _raw_tx(self, **overrides):
        """Build a raw transaction as returned by the comchain tx list API."""
        raw = {
            "hash": "0xabc",
            "sent": 1000,
            "time": 5000,
            "status": 0,
            "currency": self.currency.ident,
            "type": "Transfer",
            "addr_from": "0xFROM",
            "addr_to": "0xTO",
        }
        raw.update(overrides)
        return raw

    def _patch_chain(self, raw_txs):
        """Mock the comchain transaction list of the Odoo wallet."""
        patcher = patch.object(
            pyc3l,
            "getAccountTransactions",
            lambda address, count=10, offset=0: raw_txs if offset == 0 else [],
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_matching_transfer_is_returned(self):
        """A transfer to the wallet with the right amount matches."""
        self._patch_chain([self._raw_tx()])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [{"hash": "0xabc", "time": 5000}])

    def test_different_amount_is_ignored(self):
        """A transfer with a different amount does not match."""
        self._patch_chain([self._raw_tx(sent=2000)])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_transfer_older_than_since_is_ignored(self):
        """A transfer older than `since_ts` stops the lookup."""
        self._patch_chain([self._raw_tx(time=500)])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_transfer_to_another_wallet_is_ignored(self):
        """A transfer to another recipient does not match."""
        self._patch_chain([self._raw_tx(addr_to="0xOTHER")])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_transfer_from_another_wallet_is_ignored(self):
        """A transfer from another sender does not match."""
        self._patch_chain([self._raw_tx(addr_from="0xOTHER")])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_transfer_of_another_currency_is_ignored(self):
        """A transfer of another currency does not match."""
        self._patch_chain([self._raw_tx(currency="othercoin")])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_transfer_of_another_type_is_ignored(self):
        """A non-transfer operation does not match."""
        self._patch_chain([self._raw_tx(type="Pledge")])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])

    def test_unconfirmed_transfer_is_ignored(self):
        """A transfer with a non-zero status does not match."""
        self._patch_chain([self._raw_tx(status=1)])
        result = self.currency._find_topup_transactions(
            self.wallet, 10.0, since_ts=1000
        )
        self.assertEqual(result, [])
