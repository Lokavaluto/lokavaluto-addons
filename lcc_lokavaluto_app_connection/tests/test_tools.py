from odoo.addons.component.tests.common import TransactionComponentCase
from ..tools import transform_backend_keys_in_currency_uris,transform_wallet_backend_keys_in_wallet_uris


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
