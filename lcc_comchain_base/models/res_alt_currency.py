import logging

from pyc3l import Pyc3l

from odoo import api, fields, models
from odoo.exceptions import AccessDenied


pyc3l = Pyc3l()
_logger = logging.getLogger(__name__)


class AlternativeCurrency(models.Model):
    """An alternative currency is a currency managed by Odoo on a external financial backend.
    Each currency can have its own parameters and its wallets.
    This inheritance adds fields and methods to support Comchain technology.
    """

    _inherit = "res.alt.currency"

    @api.model
    def _default_messages(self):
        return "Top-up from " + str(self.name)

    engine = fields.Selection(
        selection_add=[("comchain", "Comchain")],
        ondelete={"comchain": "cascade"},
    )
    safe_wallet_partner_id = fields.Many2one(
        "res.partner", string="Safe Wallet Partner", tracking=True
    )
    odoo_wallet_partner_id = fields.Many2one(
        "res.partner", string="Odoo Wallet Partner", tracking=True
    )
    message_from = fields.Char("Message from", default=_default_messages, tracking=True)
    message_to = fields.Char("Message to", default=_default_messages, tracking=True)

    last_block_checked_nb = fields.Integer("Last Block Checked Nb")

    def _retrieve_last_debit_transactions(self, start=None, end=None):
        """A list of transactions (dictionnary) is expected, with the following data:
        - sender: the Odoo name of the wallet concerned by the debit request,
        - amount: the amount debited from the wallet,
        - transaction_id: the transaction ID in the digital currency backend
        - transaction_date: the timestamp of the transaction.
        """
        self.ensure_one()
        yield from super()._retrieve_last_debit_transactions(start, end)

        if self.engine != "comchain":
            return

        # Retrieve all the debit transactions from the newly created blocks
        backend_ident = f"comchain://{self.ident}"

        if start is not None:
            if not isinstance(start, int) or start < 0:
                raise ValueError("Start block ID must be a positive integer")
            start_block_id = start
        else:
            start_block_id = self.last_block_checked_nb + 1

        if end is not None:
            if not isinstance(end, int) or end < 0:
                raise ValueError("End block ID must be a positive integer")
            end_block_id = end
        else:
            end_block_id = pyc3l.getBlockNumber()
            if start is None:
                if start_block_id == end_block_id + 1:
                    _logger.info(
                        "No new block to check on Comchain "
                        "(last checked: %s, current: %s)",
                        self.last_block_checked_nb,
                        end_block_id,
                    )
                    return

        if end_block_id < start_block_id:
            raise ValueError(
                f"Inconsistent block range, first ID is greater than last one "
                f"({start_block_id} > {end_block_id})"
            )

        # Loop on all the blocks range
        _logger.info(
            f"Start reconversion check on Comchain from block {start_block_id} "
            f"to block {end_block_id}"
        )
        for block_nb in range(start_block_id, end_block_id + 1):
            _logger.info("Get Debit Transactions - read block %s" % block_nb)
            nb_txs = 0

            # Get the block transactions
            block_txs = pyc3l.BlockByNumber(block_nb).bc_txs
            for tx in block_txs:
                if not getattr(tx, "currency", None):
                    continue  # this transaction is not linked with a currency
                if tx.currency.name.lower() != self.ident.lower():
                    continue  # this transaction is about another smart contract
                full_tx = tx.full_tx
                if not full_tx.is_cc_transaction:
                    continue  # this transaction is not a digital currency transfer
                if full_tx.status != 0:
                    _logger.info(
                        f"Transaction {tx.hash} is ignored because status is not 0",
                    )
                    continue  # this transaction has been refused by the smart contract
                if (
                    full_tx.addr_to.removeprefix("0x")
                    != self.safe_wallet_partner_id.lcc_backend_ids[0].comchain_id
                ):
                    _logger.info(
                        f"Transaction {tx.hash} is ignored because is not towards the Safe Wallet",
                    )
                    continue
                _logger.info(f"Transaction {tx.hash} retrieved")
                sender_address = full_tx.addr_from.removeprefix("0x")
                ## full_tx.sent will probably need to be a string at some point
                ## to account for the full capacity of u256 bytes. Let's assume
                ## they'll be this long.
                string_amount = str(full_tx.sent).zfill(3)
                decimal_part = string_amount[0:-2]
                if int(decimal_part) >= 2**46:
                    msg = "Sent amount overflows double precision limits"
                    raise ValueError(msg)
                yield {
                    "sender": f"comchain:{sender_address}",
                    "amount": float(f"{string_amount[0:-2]}.{string_amount[-2:]}"),
                    "transaction_id": tx.hash,
                    "backend_ident": backend_ident,
                    "transaction_date": full_tx.received_at or None,
                }
                self.env.cr.commit()
                nb_txs += 1

            if block_nb > self.last_block_checked_nb:
                self.last_block_checked_nb = block_nb

            _logger.info(
                f"{nb_txs} transactions found in Comchain block {block_nb}."
            )
            self.env.cr.commit()

    def _safe_wallet_partners(self):
        return [*super()._safe_wallet_partners(), self.safe_wallet_partner_id]

    def _cron_auto_gas_filling(self, currency_uri=None):
        """Fill the Odoo wallet with Gas by sending a 0 unit transaction.

        This cron will use the Odoo Wallet to send himself transactions regularly.

        After each transaction, the Odoo Wallet will be refilled with Gas by Comchain,\
        allowing it to trigger TransactionOnBehalf requests without the risk of running\
        out.
        """
        if currency_uri is None:
            currencies = self.search([("active", "=", True)])
        else:
            if not isinstance(currency_uri, str):
                raise ValueError("currency_uri must be a string.")
            currencies = self.search([("uri", "=", currency_uri)])
            if len(currencies) == 0:
                raise ValueError(
                    f"No currency found for uri {currency_uri}.",
                )

        for alt_currency in currencies:
            if alt_currency.engine != "comchain":
                continue

            # Get Odoo wallets
            odoo_wallet_1 = alt_currency.odoo_wallet_partner_id.lcc_backend_ids[0]
            message = "Gas filling transaction."

            # Send 0 unit transaction to himself to generate gas.
            odoo_wallet_1.send_nant_transaction(odoo_wallet_1, 0.00, message)

    def _cron_check_credit_requests_in_error(self):
        """Check credit requests in error.

        Sometimes Comchain credit requests are in error because the transaction
        could not be verified at the time of processing, due to block mining delay.

        This cron will check all credit requests in error to ensure they are still
        in error.

        It does not reprocess the credit requests, that remain a manual operation.
        """
        currencies = self.search([("active", "=", True), ("engine", "=", "comchain")])
        for alt_currency in currencies:
            alt_currency._check_credit_requests_in_error()

    def _check_credit_requests_in_error(self) -> None:
        """Check all credit requests in error for this currency."""
        self.ensure_one()
        _logger.info(
            f"Start checking credit requests in error for alt currency {self.name}.",
        )
        credit_requests = self.env["credit.request"].search(
            [
                ("alt_currency_id", "=", self.id),
                ("state", "=", "error"),
            ]
        )
        for credit_request in credit_requests:
            credit_request.check_still_in_error()
        _logger.info(
                f"Check of credit requests in error for alt currency {self.name} finished.",
        )
