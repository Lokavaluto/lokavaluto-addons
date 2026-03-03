from minimock import mock, Mock, restore
from pyc3l import Pyc3l
from odoo.addons.component.tests.common import TransactionComponentCase
import odoo  # noqa: F401 -- minimock namespace lookup


class TestResWallet(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResAltCurrency = self.env["res.alt.currency"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResPartner = self.env["res.partner"]

    def _create_res_partner_backend(self, partner, currency, ident="98765"):
        return self.ResPartnerBackend.create(
            {
                "name": f"comchain:{ident}",
                "alt_currency_id": currency.id,
                "partner_id": partner.id,
                "comchain_id": ident,
            }
        )

    def _create_res_partner(self, name="John Doe"):
        return self.ResPartner.create({"name": name})

    def _create_alt_currency(self, ident="currency"):
        return self.ResAltCurrency.create(
            {
                "name": ident,
                "ident": ident,
                "active": True,
                "engine": "comchain",
            }
        )

    def test_retrieve_last_debit_transactions_empty_tx_list(self):
        """Test that _retrieve_last_debit_transactions returns an
        empty list when no transactions are found.
        """

        pyc3l = Pyc3l()
        currency = self._create_alt_currency()
        # Mock the transaction data returned by Pyc3l
        mock("Pyc3l.BlockByNumber", returns=Mock("transactions", bc_txs=[]))

        # Mock database cursor commit to avoid SAVEPOINT errors
        mock("odoo.sql_db.Cursor.commit", returns=None)

        txs = list(currency._retrieve_last_debit_transactions(1, 1))

        self.assertEqual(len(txs), 0)
        restore()

    def test_retrieve_last_debit_transactions_with_txs(self):
        """Test that _retrieve_last_debit_transactions returns the
        expected transactions when some are found.
        """

        # Build test data
        pyc3l = Pyc3l()
        currency = self._create_alt_currency()
        partner = self._create_res_partner("John Doe")
        wallet = self._create_res_partner_backend(
            partner,
            currency,
            ident="123",
        )
        currency.safe_wallet_partner_id = partner.id

        # Mock the transaction data returned by Pyc3l
        mock_tx_1 = Mock(
            "tx1",
            hash = "0xTransactionHash1",
            full_tx = Mock(
                "full_tx",
                is_cc_transaction = True,
                status = 0,
                addr_to = "0x123",
                addr_from = "0x456",
                sent = 1
            )
        )
        mock_tx_1.currency.name="currency"
        mock(
            "Pyc3l.BlockByNumber",
            returns=Mock("transactions", bc_txs=[mock_tx_1]),
        )

        # Mock database cursor commit to avoid SAVEPOINT errors
        mock("odoo.sql_db.Cursor.commit", returns=None)

        txs = list(currency._retrieve_last_debit_transactions(1, 1))

        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]["sender"], "comchain:456")
        self.assertEqual(txs[0]["amount"], 0.01)
        self.assertEqual(txs[0]["transaction_id"], "0xTransactionHash1")
        restore()

    def test_retrieve_last_debit_transactions_commit(self):
        """Test postgres commits

        Check that _retrieve_last_debit_transactions launch postgres commits
        when expected.
        """

        # Build test data
        pyc3l = Pyc3l()
        currency = self._create_alt_currency()
        partner = self._create_res_partner("John Doe")
        wallet = self._create_res_partner_backend(
            partner,
            currency,
            ident="123",
        )
        currency.safe_wallet_partner_id = partner.id

        # Mock the transaction data returned by Pyc3l
        mock_tx_1 = Mock(
            "tx1",
            hash = "0xTransactionHash1",
            full_tx = Mock(
                "full_tx",
                is_cc_transaction = True,
                status = 0,
                addr_to = "0x123",
                addr_from = "0x456",
                sent = 1
            )
        )
        mock_tx_1.currency.name="currency"
        mock(
            "Pyc3l.BlockByNumber",
            returns=Mock("transactions", bc_txs=[mock_tx_1]),
        )

        # Mock database cursor commit to avoid SAVEPOINT errors
        nb_calls = {"count": 0}
        def mock_commit():
            nb_calls["count"] += 1
        mock("odoo.sql_db.Cursor.commit", returns_func=mock_commit)

        # Retrieve transactions
        txs = currency._retrieve_last_debit_transactions(1, 1)
        self.assertEqual(
            nb_calls["count"],
            0,
            "Commit should not be called before processing any transaction"
        )

        # Process the first transaction
        next(txs)
        self.assertEqual(
            nb_calls["count"],
            0,
            "Commit should not be called before processing the first transaction"
        )

        # There is only one transaction, so the next call should raise StopIteration
        with self.assertRaises(StopIteration):
            next(txs)
        self.assertEqual(
            nb_calls["count"],
            2,
            "Commit should be called after processing last transaction AND at the end of block loop",
        )
        restore()
