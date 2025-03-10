from odoo import models, fields

import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = "res.company"

    monujo_web_app_url = fields.Char(string="Monujo web app URL")
    monujo_android_app_url = fields.Char(string="Monujo Android app URL")
    monujo_ios_app_url = fields.Char(string="Monujo iOS app URL")

    def _assert_transaction_valid(self, transaction):
        """Check if the transaction has all required fields"""
        for field in [
            "sender",
            "amount",
            "backend_ident",
            "transaction_id",
            "transaction_date",
        ]:
            if not transaction.get(field):
                raise ValueError("Transaction has no %s" % field)

    def _cron_import_new_digital_currency_debit_requests(self):
        """Create the debit requests in Odoo for all the debit
        transactions performed since the last check."""

        # For each transaction received:
        # - retrieve the transaction id
        # - check if any debit request exists with this transaction id
        # - if yes, do nothing
        # - if no, create a new debit request
        for transaction in self._retrieve_last_debit_transactions():
            self._assert_transaction_valid(transaction)

            ## replace sender by wallet_id

            wallet_ids = self.env["res.partner.backend"].search(
                [("name", "=", transaction["sender"])]
            )
            if len(wallet_ids) == 0:
                _logger.warning(
                    "No wallet found for debit transaction %s"
                    % transaction["transaction_id"]
                )
                continue
            elif len(wallet_ids) > 1:
                raise ValueError(
                    "Too many wallets found for debit transaction %s"
                    % transaction["transaction_id"]
                )
            transaction["wallet_id"] = wallet_ids[0].id
            del transaction["sender"]

            ## normalize date to UTC and remove timezone

            transaction["transaction_date"] = datetime.utcfromtimestamp(
                transaction["transaction_date"].timestamp()
            )

            ## check if a debit request already exists for this transaction

            debit_requests = self.env["debit.request"].search(
                [("transaction_id", "=", transaction["transaction_id"])]
            )
            if len(debit_requests) > 0:
                if len(debit_requests) > 1:
                    raise ValueError(
                        "Inconsistency in debit request database, "
                        "many debit_request exists for transaction id %s"
                        % transaction["transaction_id"]
                    )
                ## is this debit request for the same transaction ?
                for field in ["wallet_id", "amount", "transaction_date"]:
                    debit_request_value = getattr(debit_requests[0], field)
                    if field.endswith("_id"):
                        debit_request_value = debit_request_value.id
                    if debit_request_value != transaction.get(field):
                        raise ValueError(
                            "Debit request already exists with different values for transaction %s"
                            "(id:%s has different %s value (%s))"
                            % (
                                transaction["transaction_id"],
                                debit_requests[0].id,
                                field,
                                debit_request_value,
                            )
                        )
                _logger.info(
                    "Debit request already exists for transaction %s, ignoring."
                    % transaction["transaction_id"]
                )
                continue

            transaction["active"] = True

            request = self.env["debit.request"].create(transaction)

            _logger.info(
                "Debit request created for wallet %s on transaction %s"
                % (request.wallet_id, transaction["transaction_id"])
            )

    def _retrieve_last_debit_transactions(self):
        """TO OVERIDE in digital currency backend dedicated add-ons
        A list of transactions (dictionary) is expected, with the following data:
        - sender: the Odoo name of the wallet concerned by the debit request,
        - amount: the amount debited from the wallet,
        - tx_id: the transaction ID in the digital currency backend
        - tx_timestamp: the timestamp of the transaction
        """
        yield from []

    def _safe_wallet_partners(self):
        return []
