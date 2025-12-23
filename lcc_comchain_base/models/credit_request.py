import logging
from ..utils import check_transaction_content
from odoo import models

_logger = logging.getLogger(__name__)

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
