from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.exceptions import MissingError
from ..tools import (
    transform_backend_keys_in_currency_uris,
    transform_wallet_backend_keys_in_wallet_uris,
    transform_wallet_uris_in_wallet_backend_keys,
)

class TestResWallet(TransactionComponentCase):

    def test_transform_backend_keys_in_currency_uris(self):
        """Test the transformation of backend keys into currency URIs.

        Both old and new formats should be correctly transformed to the new URI format.
        """
        backend_keys = [
            "foo:currencyA", # Old format
            "foo://currencyB", # New format
        ]
        expected_uris = [
            "foo://currencyA",
            "foo://currencyB",
        ]
        result = transform_backend_keys_in_currency_uris(backend_keys)
        self.assertEqual(result, expected_uris)

    def test_transform_wallet_backend_keys_in_wallet_uris(self):
        """Test the transformation of wallet backend keys into wallet URIs.

        Both old and new formats should be correctly transformed to the new URI format.
        """
        wallet_backend_keys = [
            "foo:walletA", # Old format
            "foo://currencyA/wallet/walletB", # New format
        ]
        currency_ident = "currencyA"
        expected_wallet_uris = [
            "foo://currencyA/wallet/walletA",
            "foo://currencyA/wallet/walletB",
        ]
        result = transform_wallet_backend_keys_in_wallet_uris(wallet_backend_keys, currency_ident)
        self.assertEqual(result, expected_wallet_uris)

    def test_transform_wallet_backend_key_with_currency_suffix(self):
        """An old format key may name its currency after ``@``.

        Monujo identifies cyclos wallets as ``cyclos:<owner id>@<host>``:
        the suffix is the currency ident and lands in the URI authority.
        """
        result = transform_wallet_backend_keys_in_wallet_uris(
            ["cyclos:-123@cyclos.example.org:8080"], "cyclos.example.org:8080"
        )
        self.assertEqual(
            result, ["cyclos://cyclos.example.org:8080/wallet/-123"]
        )

    def test_transform_wallet_uri_in_backend_key_with_currency_suffix(self):
        """Engines whose key names its currency get it back after ``@``,
        so the key is the one Monujo uses for that wallet."""
        result = transform_wallet_uris_in_wallet_backend_keys(
            ["cyclos://cyclos.example.org:8080/wallet/-123"]
        )
        self.assertEqual(result, ["cyclos:-123@cyclos.example.org:8080"])

    def test_wallet_key_and_uri_round_trip(self):
        """Converting a key to a URI and back gives the same key."""
        for key, currency_ident in [
            ("cyclos:-123@cyclos.example.org", "cyclos.example.org"),
            ("foo:walletA", "currencyA"),
        ]:
            uri = transform_wallet_backend_keys_in_wallet_uris([key], currency_ident)
            self.assertEqual(transform_wallet_uris_in_wallet_backend_keys(uri), [key])

    def test_transform_wallet_backend_key_with_foreign_currency_suffix(self):
        """A key whose ``@`` suffix names another currency is rejected."""
        with self.assertRaises(MissingError):
            transform_wallet_backend_keys_in_wallet_uris(
                ["cyclos:-123@other.example.org"], "cyclos.example.org"
            )

    def test_transform_wallet_uris_in_wallet_backend_keys(self):
        """Test the transformation of wallet URIs into wallets backend keys."""
        wallet_uris = [
            "foo://currencyA/wallet/walletA",
            "foo://currencyA/wallet/walletB",
        ]
        expected_wallet_backend_keys = [
            "foo:walletA",
            "foo:walletB",
        ]
        result = transform_wallet_uris_in_wallet_backend_keys(wallet_uris)
        self.assertEqual(result, expected_wallet_backend_keys)
