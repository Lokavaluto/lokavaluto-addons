from datetime import datetime, timezone
from unittest.mock import patch

from odoo.addons.component.tests.common import TransactionComponentCase


class TestDebitSyncWalletLink(TransactionComponentCase):
    """Reconversion transactions are linked to the sender's wallet by URI.

    The wallet name is a free label (on imported wallets it is the
    holder's name), so it must play no part in the link.
    """

    def setUp(self):
        super().setUp()
        self.currency = self.env["res.alt.currency"].create(
            {"name": "Currency", "ident": "currency", "active": True, "engine": "foo"}
        )

    def _create_wallet(self, name, ident, active=True):
        partner = self.env["res.partner"].create({"name": name})
        return self.env["res.partner.backend"].create(
            {
                "name": name,
                "ident": ident,
                "active": active,
                "partner_id": partner.id,
                "alt_currency_id": self.currency.id,
            }
        )

    def _sync(self, wallet_uri, transaction_id="tx-1"):
        transaction = {
            "wallet_uri": wallet_uri,
            "amount": 1.0,
            "transaction_id": transaction_id,
            "backend_ident": self.currency.uri,
            "transaction_date": datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc),
        }
        with patch.object(
            type(self.currency),
            "_retrieve_last_debit_transactions",
            autospec=True,
            side_effect=lambda *args, **kwargs: iter([dict(transaction)]),
        ):
            self.currency._sync_new_debit_requests()
        return self.env["debit.request"].search(
            [("transaction_id", "=", transaction_id)]
        )

    def test_transaction_linked_to_wallet_with_matching_uri(self):
        wallet = self._create_wallet("Thibaut VACHER", "4036691651388677992")

        debit_requests = self._sync(wallet.uri)

        self.assertEqual(debit_requests.wallet_id, wallet)

    def test_transaction_ignored_when_wallet_is_archived(self):
        wallet = self._create_wallet("Archived holder", "1234", active=False)

        debit_requests = self._sync(wallet.uri)

        self.assertFalse(debit_requests)

    def test_transaction_ignored_when_no_wallet_matches_uri(self):
        self._create_wallet("cyclos:9999", "1234")

        debit_requests = self._sync(f"{self.currency.uri}/wallet/9999")

        self.assertFalse(debit_requests)

    def test_wallet_ident_set_at_creation_for_test_engine(self):
        partner = self.env["res.partner"].create({"name": "Holder"})

        wallet = self.env["res.partner.backend"].create(
            {
                "name": "foo:wallet",
                "partner_id": partner.id,
                "alt_currency_id": self.currency.id,
            }
        )

        self.assertEqual(wallet.ident, str(wallet.id))
        self.assertEqual(wallet.uri, f"{self.currency.uri}/wallet/{wallet.id}")
