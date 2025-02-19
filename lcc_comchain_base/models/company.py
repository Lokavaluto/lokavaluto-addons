import logging
from datetime import datetime
from odoo import models, fields, api
from odoo.addons.lcc_lokavaluto_app_connection import tools
from pyc3l import Pyc3l

pyc3l = Pyc3l()
_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = "res.company"

    @api.model
    def _default_messages(self):
        message = "Top-up from " + str(self.name)
        return message

    comchain_currency_name = fields.Char(string="Currency name")
    safe_wallet_partner_id = fields.Many2one(
        "res.partner", string="Safe Wallet Partner"
    )
    odoo_wallet_partner_id = fields.Many2one(
        "res.partner", string="Odoo Wallet Partner"
    )
    comchain_odoo_wallet_password = fields.Char(string="Odoo wallet password")
    message_from = fields.Char("Message from", default=_default_messages)
    message_to = fields.Char("Message to", default=_default_messages)

    last_block_checked_nb = fields.Integer("Last Block Checked Nb")

    def _retrieve_last_debit_transactions(self):
        """A list of transactions (dictionnary) is expected, with the following data:
        - sender: the Odoo name of the wallet concerned by the debit request,
        - amount: the amount debited from the wallet,
        - transaction_id: the transaction ID in the digital currency backend
        - transaction_date: the timestamp of the transaction
        """

        yield from super(Company, self)._retrieve_last_debit_transactions()

        # Retrieve all the debit transactions from the newly created blocks
        company_id = self.env.user.company_id

        comchain_res = []
        # Get the ID of the last blockchain block built
        last_block_id = pyc3l.getBlockNumber()
        # Loop on all the blocks created since the last check
        _logger.info(
            "Start reconversion check on Comchain from block %s to block %s"
            % (company_id.last_block_checked_nb, last_block_id)
        )
        if last_block_id < company_id.last_block_checked_nb:
            raise ValueError(
                "Inconsistent last processed block is greater than last block id."
            )
        for block_nb in range(company_id.last_block_checked_nb + 1, last_block_id + 1):
            _logger.info("Get Debit Transactions - read block %s" % block_nb)
            # Get the block transactions
            block_txs = pyc3l.BlockByNumber(block_nb).bc_txs
            for tx in block_txs:
                if not getattr(tx, "currency", None):
                    continue  # this transaction is not linked with a currency
                if (
                    not tx.currency.name.lower()
                    == company_id.comchain_currency_name.lower()
                ):
                    continue  # this transaction is about another smart contract
                full_tx = tx.full_tx
                if not full_tx.is_cc_transaction:
                    continue  # this transaction is not a digital currency transfer
                if not full_tx.status == 0:
                    _logger.info(
                        "Transaction %s is ignored because status is not 0" % tx.hash
                    )
                    continue  # this transaction has been refused by the smart contract
                if (
                    full_tx.addr_to.lstrip("0x")
                    != company_id.safe_wallet_partner_id.lcc_backend_ids[0].comchain_id
                ):
                    _logger.info(
                        "Transaction %s is ignored because is not towards the Safe Wallet"
                        % tx.hash
                    )
                    continue
                _logger.info("Transaction %s retrieved" % tx.hash)
                sender_address = full_tx.addr_from.lstrip("0x")
                ## full_tx.sent will probably need to be a string at some point
                ## to account for the full capacity of u256 bytes. Let's assume
                ## they'll be this long.
                string_amount = str(full_tx.sent).zfill(3)
                decimal_part = string_amount[0:-2]
                if int(decimal_part) >= 2**46:
                    raise ValueError("Sent amount overflows double precision limits")
                yield {
                    "sender": "comchain:%s" % sender_address,
                    "amount": float(f"{string_amount[0:-2]}.{string_amount[-2:]}"),
                    "transaction_id": tx.hash,
                    "transaction_date": full_tx.received_at
                    if full_tx.received_at
                    else None,
                }
                self.env.cr.commit()

            company_id.last_block_checked_nb = block_nb
            self.env.cr.commit()

    def _safe_wallet_partners(self):
        return super(Company, self)._safe_wallet_partners() + [
            self.safe_wallet_partner_id
        ]
