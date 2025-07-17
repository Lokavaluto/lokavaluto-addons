import logging
from datetime import datetime

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AlternativeCurrency(models.Model):
    """An alternative currency is a currency managed by Odoo on a external financial backend.
    Each currency can have its own parameters and its wallets.
    """

    _name = "res.alt.currency"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Alternative Currency"

    name = fields.Char("Name", tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    ident = fields.Char("Currency Ident", tracking=True)
    engine = fields.Selection(
        [("foo", "Value defined only for testing purposes")],
        string="Transaction Engine",
        required=True,
        tracking=True,
    )  # You can find real type values in lcc_comchain_base and lcc_cyclos_base,
    uri = fields.Char("Currency URI", compute="_compute_currency_uri", store=True, tracking=True)

    activate_automatic_topup = fields.Boolean("Activate Automatic Topup", tracking=True)
    currency_unit_product_id = fields.Many2one(
        "product.product",
        string="Currency Unit Product",
        tracking=True,
    )
    commission_product_id = fields.Many2one(
        "product.product",
        string="Commission Product",
        tracking=True,
    )

    @api.depends("engine", "ident")
    def _compute_currency_uri(self):
        for cur in self:
            cur.uri = "%s://%s" % (cur.engine, cur.ident)

    def _safe_wallet_partners(self):
        return []

    def get_currency_json_data(self):
        """Return normalized currency's data"""
        self.ensure_one()
        return {
            "type": "%s:%s" % (self.engine, self.ident),
            "accounts": [],
            "min_credit_amount": getattr(
                self.sudo().currency_unit_product_id, "sale_min_qty", 0
            ),
            "max_credit_amount": getattr(
                self.sudo().currency_unit_product_id, "sale_max_qty", 0
            ),
        }

    def _cron_import_new_digital_currency_debit_requests(self, currency_uri=None, start=None, end=None) -> None:
        if (start is not None or end is not None) and currency_uri is None:
            raise ValueError(
                "When start or end is set, currency_uri must be set too.",
            )
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
            _logger.info(
                f"Start sync debit request for alt currency {alt_currency.name}.",
            )
            alt_currency._sync_new_debit_requests(start, end)
            _logger.info(
                f"Sync of debit request for alt currency {alt_currency.name} finished.",
            )

    def _assert_transaction_valid(self, transaction) -> None:
        """Check if the transaction has all required fields."""
        for field in [
            "sender",
            "amount",
            "backend_ident",
            "transaction_id",
            "transaction_date",
        ]:
            if not transaction.get(field):
                msg = f"Transaction has no {field}"
                raise ValueError(msg)

    def _sync_new_debit_requests(self, start=None, end=None) -> None:
        """
        Create the debit requests in Odoo for all the debit
        transactions performed since the last check.
        """
        # For each transaction received for each alternative currency:
        # - retrieve the transaction id
        # - check if any debit request exists with this transaction id
        # - if yes, do nothing
        # - if no, create a new debit request
        self.ensure_one()
        for transaction in self._retrieve_last_debit_transactions(start, end):
            self._assert_transaction_valid(transaction)

            ## replace sender by wallet_id

            wallet_ids = self.env["res.partner.backend"].search(
                [("name", "=", transaction["sender"])],
            )
            if len(wallet_ids) == 0:
                _logger.warning(
                    "No wallet found for debit transaction %r (Sender requested: %r)"
                    % (transaction["transaction_id"], transaction["sender"])
                )
                continue
            if len(wallet_ids) > 1:
                raise ValueError(
                    "Too many wallets found for debit transaction %r (Sender requested: %r)"
                    % (transaction["transaction_id"], transaction["sender"])
                )
            transaction["wallet_id"] = wallet_ids[0].id
            del transaction["sender"]

            ## normalize date to UTC and remove timezone

            transaction["transaction_date"] = datetime.utcfromtimestamp(
                transaction["transaction_date"].timestamp(),
            )

            ## check if a debit request already exists for this transaction

            debit_requests = self.env["debit.request"].search(
                [("transaction_id", "=", transaction["transaction_id"])],
            )
            if len(debit_requests) > 0:
                if len(debit_requests) > 1:
                    msg = (
                        "Inconsistency in debit request database, "
                        "many debit_request exists for transaction id {}".format(
                            transaction["transaction_id"],
                        )
                    )
                    raise ValueError(
                        msg,
                    )
                ## is this debit request for the same transaction ?
                for field in ["wallet_id", "amount", "transaction_date"]:
                    debit_request_value = getattr(debit_requests[0], field)
                    if field.endswith("_id"):
                        debit_request_value = debit_request_value.id
                    if debit_request_value != transaction.get(field):
                        msg = (
                            "Debit request already exists with different values for transaction {}"
                            "(id:{} has different {} value ({}))".format(
                                transaction["transaction_id"],
                                debit_requests[0].id,
                                field,
                                debit_request_value,
                            )
                        )
                        raise ValueError(
                            msg,
                        )
                _logger.info(
                    "Debit request already exists for transaction {}, ignoring.".format(
                        transaction["transaction_id"],
                    ),
                )
                continue

            transaction["active"] = True

            request = self.env["debit.request"].create(transaction)

            _logger.info(
                "Debit request created for wallet {} on transaction {}".format(
                    request.wallet_id,
                    transaction["transaction_id"],
                ),
            )

    def _retrieve_last_debit_transactions(self, start=None, end=None):
        """TO OVERIDE in digital currency backend dedicated add-ons
        A list of transactions (dictionary) is expected, with the following data:
        - sender: the Odoo name of the wallet concerned by the debit request,
        - amount: the amount debited from the wallet,
        - tx_id: the transaction ID in the digital currency backend
        - tx_timestamp: the timestamp of the transaction.
        """
        yield from []
