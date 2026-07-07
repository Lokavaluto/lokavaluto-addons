import logging
import re
import time
from pyc3l import Pyc3l
from pyc3l.ApiHandling import APIError
from odoo.addons.lcc_lokavaluto_app_connection import tools

pyc3l = Pyc3l()
_logger = logging.getLogger(__name__)


def is_transaction_hash(value):
    """Checks if the response is a 0x 64digits hash"""
    return re.search("^0x[0-9a-f]{64,64}$", value, re.IGNORECASE)

def check_transaction_content(tx_hash, amount=0):
    """Check if the transaction data are the one expected or not.

    Return a message explaining the issue if there is an issue.
    Return False if no problem.
    """
    # Verify the Comchain transaction - res supposed to be the transaction hash
    if not is_transaction_hash(tx_hash):
        return f"Comchain transaction failed: response is not the expected hash: {tx_hash}"

    retry = 1
    retry_max = 10
    while True:
        tx_data = None
        transaction = pyc3l.Transaction(tx_hash)

        try:
            tx_data = transaction.data
        except APIError as e:
            _logger.error(tools.format_last_exception())
            if not e.args[0].startswith("API Call failed without message"):
                return f"Failure when trying to get transaction info: {e}"

        if tx_data is not None:
            received = tx_data.get("recieved")
            if received is None:
                _logger.warning(
                    f"Received incomplete transaction data. Missing 'recieved' field (retry {retry}/{retry_max})"
                )
            else:
                break

        if retry >= retry_max:
            return f"Max retry reached to get transaction info ({retry_max} retries)"

        retry += 1
        time.sleep(0.5)

    if received != round(amount * 100):
        return (
            f"Order sent, but checking transaction record returned as an unexepected "
            f"amount of {received} received."
        )

    return False
