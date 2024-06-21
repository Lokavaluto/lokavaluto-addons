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
        - tx_id: the transaction ID in the digital currency backend
        - tx_timestamp: the timestamp of the transaction
        """
        res = super(Company, self)._retrieve_last_debit_transactions()

        # Retrieve all the debit transactions from the newly created blocks
        company_id = self.env.user.company_id
        comchain_res = []
        try:
            # Get the ID of the last blockchain block built
            last_block_id = pyc3l.getBlockNumber()
            # Loop on all the blocks created since the last check
            _logger.info(
                "Start reconversion check on Comchain from block %s to block %s"
                % (company_id.last_block_checked_nb, last_block_id)
            )
            for block_nb in range(
                company_id.last_block_checked_nb + 1, last_block_id + 1
            ):
                _logger.info("Get Debit Transactions - read block %s" % block_nb)
                # Get the block transactions
                block_txs = pyc3l.BlockByNumber(block_nb).bc_txs
                for tx in block_txs:
                    if not tx.currency:
                        continue  # this transaction is not linked with a currency
                    if (
                        not tx.currency.name.lower()
                        == company_id.comchain_currency_name.lower()
                    ):
                        continue  # this transaction is about another smart contract
                    full_tx = tx.full_tx
                    if not full_tx.is_cc_transaction:
                        continue  # this transaction is not a digital currency transfer
                    if not full_tx.direction == 1:
                        continue  # this transaction is not a reconversion
                    _logger.info("Transaction %s retrieved" % tx.hash)
                    sender_address = full_tx.add2.lstrip("0x")
                    matched_wallet = self.env["res.partner.backend"].search(
                        [("comchain_id", "=", sender_address)]
                    )
                    if len(matched_wallet) == 0:
                        continue  # this transaction comes from a wallet not registered in current Odoo database
                    string_amount = str(full_tx.sent).zfill(2)
                    comchain_res.append(
                        {
                            "sender": "comchain:%s" % sender_address,
                            "amount": f"{string_amount[0:-2]}.{string_amount[-2:]}",
                            "tx_id": tx.hash,
                            # "tx_timestamp": datetime.fromtimestamp(
                            #     int(full_tx.receivedat["value"])
                            # ),
                            "tx_timestamp": full_tx.received_at.replace(tzinfo=None) if full_tx.received_at else None,
                        }
                    )

            company_id.last_block_checked_nb = last_block_id
        except Exception as e:
            # Erase comchain_res content to avoid filling function answer with incompletely filled data.
            comchain_res = []
            _logger.error(tools.format_last_exception())

        res = res + comchain_res
        return res
