from minimock import mock, Mock, restore
from pyc3l import Pyc3l
from ..utils import is_transaction_hash, check_transaction_content

class TestUtils(TransactionComponentCase):
    def setUp(self):
        super().setUp()

    def test_is_transaction_hash_ok(self):
        """ Test is_transaction_hash() for a valid transaction. """

        res = is_transaction_hash(
            "0x85f8dfd7e5eab0fe66145ffb0ef3435c75875943b4b589bb0ee6042b4efb1e2e"
        )
        self.assertTrue(res)

    def test_is_transaction_hash_ko(self):
        """ Test is_transaction_hash() for an invalid transaction. """

        res = is_transaction_hash(
            "LoremIpsum"
        )
        self.assertFalse(res)

    def test_check_transaction_content_ok(self):
        """ Test check_transaction_content() for a valid transaction. """

        # Mock a transaction response content
        mock_tx = Mock("transaction", data={"recieved": 1000})
        mock("Pyc3l.Transaction", returns=mock_tx)

        # Check the transaction
        response = "0x85f8dfd7e5eab0fe66145ffb0ef3435c75875943b4b589bb0ee6042b4efb1e2e"
        res = check_transaction_content(response, 10.00)
        self.assertFalse(res)
        restore()

    def test_check_transaction_content_ko_wrong_amount(self):
        """ Test check_transaction_content() for a transaction with wrong amount. """

        # Mock a transaction response content
        mock_tx = Mock("transaction", data={"recieved": 10})
        mock("Pyc3l.Transaction", returns=mock_tx)

        # Check the transaction
        response = "0x85f8dfd7e5eab0fe66145ffb0ef3435c75875943b4b589bb0ee6042b4efb1e2e"
        res = check_transaction_content(response, 10.00)
        self.assertEqual(
            res,
            "Order sent, but checking transaction record returned as an unexepected "
            "amount of 10 received."
        )
        restore()

    def test_check_transaction_content_ko_missing_recieved(self):
        """ Test check_transaction_content() for a transaction with missing field. """

        # Mock a transaction response content
        mock_tx = Mock("transaction", data={"value": 10})
        mock("Pyc3l.Transaction", returns=mock_tx)

        # Check the transaction
        response = "0x85f8dfd7e5eab0fe66145ffb0ef3435c75875943b4b589bb0ee6042b4efb1e2e"
        res = check_transaction_content(response, 10.00)
        self.assertEqual(
            res,
            "Max retry reached to get transaction info (10 retries)"
        )
        restore()
