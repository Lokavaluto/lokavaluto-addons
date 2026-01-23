from odoo.addons.component.tests.common import TransactionComponentCase
from ..tools import transform_backend_keys_in_currency_uris


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
