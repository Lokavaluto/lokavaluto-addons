import calendar
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
    topup_reconcile_grace_seconds = fields.Integer(
        "Topup reconcile grace (seconds)",
        default=600,
        help="Delay before reconciling a pending topup whose send outcome "
        "could not be confirmed. Within this delay the transaction is "
        "assumed to still be pending on the backend.",
    )
    topup_max_send_attempts = fields.Integer(
        "Topup max send attempts",
        default=3,
        help="Maximum number of automatic send attempts. Beyond that, an "
        "unconfirmed topup is flagged as uncertain for manual review.",
    )

    @api.depends("engine", "ident")
    def _compute_currency_uri(self):
        for cur in self:
            cur.uri = "%s://%s" % (cur.engine, cur.ident)

    def _search_active_wallets(self, domain=None):
        """Search active wallets on this currency with optional extra domain.

        Always filters on ``alt_currency_id``, ``active=True``,
        and ``status='active'``.
        """
        self.ensure_one()
        base_domain = [
            ("alt_currency_id", "=", self.id),
            ("active", "=", True),
            ("status", "=", "active"),
        ]
        if domain:
            base_domain += domain
        return self.env["res.partner.backend"].search(base_domain)

    def _safe_wallet_partners(self):
        return []

    def _supports_topup_reconciliation(self):
        """Return whether this backend can look up past topups.

        The base implementation returns ``False``. Financial backend add-ons
        that expose their transaction history must override this and
        :meth:`_find_topup_transactions`.

        Returns:
            bool: ``True`` when backend reconciliation is available.
        """
        self.ensure_one()
        return False

    def _find_topup_transactions(self, wallet, amount, since_ts=None):
        """Return past topup transfers matching a wallet and an amount.

        Must be overridden by financial backend add-ons that support
        reconciliation. Each match is a dict with at least a ``hash`` key
        (the transaction identifier) and optionally a ``time`` key (unix
        timestamp).

        Args:
            wallet: ``res.partner.backend`` record the topup was sent to.
            amount (float): expected topup amount.
            since_ts (int|None): ignore transfers older than this unix
                timestamp.

        Returns:
            list[dict] | None: matching transfers, or ``None`` when the
            backend does not support transaction lookup.
        """
        self.ensure_one()
        return None

    def _cron_reconcile_credit_requests(self):
        """Reconcile uncertain credit requests for every active currency."""
        for currency in self.search([("active", "=", True)]):
            currency._reconcile_pending_credit_requests()

    def _reconcile_pending_credit_requests(self):
        """Reconcile pending credit requests whose send outcome is uncertain.

        Requests are grouped by ``(wallet, amount)``. Backend transfers are
        matched to the oldest attempts first (FIFO). An unmatched request is
        retried while it stays within the allowed number of attempts, and is
        otherwise flagged as uncertain for manual review. Requests that were
        never attempted are credited directly.
        """
        self.ensure_one()
        # Nothing to do if the backend cannot list its past transfers.
        if not self._supports_topup_reconciliation():
            return

        # Only `pending` requests are uncertain: `error` and `done` already
        # have a known outcome, `open` was never paid.
        CreditRequest = self.env["credit.request"]
        pending = CreditRequest.search(
            [
                ("alt_currency_id", "=", self.id),
                ("state", "=", "pending"),
            ]
        )
        if not pending:
            return

        # Read the per-currency policy once for the whole run.
        grace = self.topup_reconcile_grace_seconds
        max_attempts = self.topup_max_send_attempts
        now = fields.Datetime.now()

        # Requests without `send_started_at` were never sent: no transfer can
        # exist on the backend, so they can be credited directly without
        # ambiguity.
        never_attempted = pending.filtered(lambda r: not r.send_started_at)
        for request in never_attempted:
            self._safe_credit_attempt(request)

        # The remaining requests may or may not have been sent. Group them by
        # `(wallet, amount)` so the transaction lookup is done once per group
        # and the matching transfers can be distributed across the attempts.
        groups = {}
        for request in pending - never_attempted:
            key = (request.wallet_id.id, request.amount)
            groups[key] = groups.get(key, CreditRequest) | request

        for (wallet_id, amount), requests in groups.items():
            wallet = self.env["res.partner.backend"].browse(wallet_id)
            # Oldest attempt first: it is the most likely to have been sent.
            requests = requests.sorted(lambda r: r.send_started_at)
            # Look for transfers sent after the oldest attempt in the group.
            since_ts = calendar.timegm(
                min(requests.mapped("send_started_at")).timetuple()
            )
            matches = self._find_topup_transactions(
                wallet, amount, since_ts=since_ts
            )
            # `None` means the backend does not support the lookup: never
            # guess, flag everything for manual review instead.
            if matches is None:
                for request in requests:
                    request._mark_uncertain()
                continue
            # Match transfers to attempts in chronological (FIFO) order.
            matches = sorted(matches, key=lambda match: match.get("time") or 0)
            for request in requests:
                if matches:
                    # A transfer exists for this attempt: confirm it.
                    request._apply_transaction_success(matches.pop(0)["hash"])
                    continue
                # No transfer left for this attempt. Wait while the transfer
                # may still be mining; otherwise retry if an attempt remains,
                # or flag as uncertain once attempts are exhausted.
                age = (now - request.send_started_at).total_seconds()
                if age <= grace:
                    continue
                if request.send_attempt_count < max_attempts:
                    self._safe_credit_attempt(request)
                else:
                    request._mark_uncertain()
            # Leftover transfers mean more backend topups than pending
            # requests: the wallet may have been credited more than once.
            if matches:
                _logger.warning(
                    "More backend topups than pending requests for wallet %s "
                    "(amount %s, currency %s): possible duplicate credit.",
                    wallet_id,
                    amount,
                    self.name,
                )

    def _safe_credit_attempt(self, request):
        """Run one credit attempt, isolating its failure from the run.

        Args:
            request: ``credit.request`` record to credit.
        """
        try:
            request.sudo()._run_credit_attempt()
        except Exception:
            self.env.cr.rollback()
            _logger.exception(
                "Credit attempt failed for credit request %s", request.id
            )

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

    def _cron_import_new_digital_currency_debit_requests(
        self, currency_uri=None, start=None, end=None
    ) -> None:
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
