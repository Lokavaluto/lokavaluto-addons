from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class Company(models.Model):
    _inherit = "res.company"

    monujo_web_app_url = fields.Char(string="Monujo web app URL")
    monujo_android_app_url = fields.Char(string="Monujo Android app URL")
    monujo_ios_app_url = fields.Char(string="Monujo iOS app URL")
    activate_automatic_topup = fields.Boolean("Activate Automatic Topup")
    commission_product_id = fields.Many2one("product.product", string="Commission Product")


    def _cron_import_new_digital_currency_debit_requests(self):
        """Create the debit requests in Odoo for all the debit
        transactions performed since the last check."""

        # Extract last transactions received in the Safe Wallet
        transactions = self._retrieve_last_debit_transactions()

        # For each transaction received:
        # - retrieve the transaction id
        # - check if any debit request exists with this transaction id
        # - if yes, do nothing
        # - if no, create a new debit request
        for transaction in transactions:
            tx_id = transaction.get("tx_id", "")
            debit_requests = self.env["debit.request"].search([("transaction_id", "=", tx_id)])
            if len(debit_requests) > 0:
                _logger.info("Debit request already exists for transaction %s" % transaction.get("tx_id"))
                continue
            values = self._build_debit_request_values(transaction)
            if not values:
                continue
            request = self.env["debit.request"].create(values)
            _logger.info("Debit request created for wallet %s on transaction %s" % (request.wallet_id,transaction.get("tx_id")))


    def _retrieve_last_debit_transactions(self):
        """TO OVERIDE in digital currency backend dedicated add-ons
        A list of transactions (dictionnary) is expected, with the following data:
        - sender: the Odoo name of the wallet concerned by the debit request,
        - amount: the amount debited from the wallet,
        - tx_id: the transaction ID in the digital currency backend
        - tx_timestamp: the timestamp of the transaction
        """
        return []


    def _build_debit_request_values(self, transaction):
        wallet_ids = self.env["res.partner.backend"].search([("name", "=", transaction.get("sender"))])
        if len(wallet_ids) == 0:
            _logger.error("No wallet found for debit transaction %s, debit request creation CANCELLED" % transaction.get("tx_id"))
            return {}
        elif len(wallet_ids) > 1:
            _logger.error("Too many wallets found for debit transaction %s, debit request creation CANCELLED" % transaction.get("tx_id"))
            return {}
        values = {
            "active" : True,
            "wallet_id" : wallet_ids[0].id,
            "amount" : transaction.get("amount"),
            "transaction_id" : transaction.get("tx_id"),
            "transaction_timestamp": transaction.get("tx_timestamp"),
        }
        return values