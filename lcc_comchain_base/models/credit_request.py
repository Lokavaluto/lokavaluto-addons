import logging
from ..utils import check_transaction_content
from odoo import models

_logger = logging.getLogger(__name__)

RPLCMNT_TX_UNDERPRICED = "Failed transfer on behalf transaction: API Call failed with message: replacement transaction underpriced"

class CreditRequest(models.Model):

    _inherit = "credit.request"

    def check_still_in_error(self) -> None:
        """Check if this credit request is still in error."""
        self.ensure_one()
        if self.alt_currency_id.engine != "comchain":
            return

        if not self.transaction_data:
            _logger.warning(
                f"Credit request {self.id} has no transaction ID, cannot check it.",
            )
            return

        if check_transaction_content(self.transaction_data, self.amount):
            _logger.info(
                f"Credit request {self.id} is still in error.",
            )
            return

        # If we reach this point, the transaction is now valid
        self.state = "done"

    def _new_credit_attempt_allowed(self):
        """Define if a new credit attempt is allowed considering the error message"""
        self.ensure_one()
        if self.state != "error" or not self.error_message:
            return False

        # Replacement transaction underpriced: we know for sure that the
        # previous transaction attempt is lost.
        if self.error_message == RPLCMNT_TX_UNDERPRICED:
            return True

        return False

    def renew_credit_attempt(self):
        """Launch a new credit request to Comchain if known error message."""
        self.ensure_one()
        if self.alt_currency_id.engine != "comchain":
            return

        if self._new_credit_attempt_allowed():
            self.credit_wallet()
