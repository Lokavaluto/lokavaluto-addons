import json
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse

import requests
from requests.auth import HTTPBasicAuth
from werkzeug.exceptions import NotFound

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AlternativeCurrency(models.Model):
    """An alternative currency is a currency managed by Odoo on a external financial backend.
    Each currency can have its own parameters and its wallets.
    This inheritance adds fields and methods to support Cyclos engine.
    """

    _inherit = "res.alt.currency"

    engine = fields.Selection(
        selection_add=[("cyclos", "Cyclos")],
        ondelete={"cyclos": "cascade"},
    )

    cyclos_server_url = fields.Char(string="Url for cyclos server", tracking=True)
    cyclos_client_token = fields.Char(
        string="Client token auth for cyclos server", tracking=True
    )

    cyclos_server_login = fields.Char(string="Login for cyclos server", tracking=True)

    cyclos_server_password = fields.Char(
        string="Password for cyclos server", tracking=True
    )

    cyclos_debit_wallet_partner = fields.Many2one(
        "res.partner",
        string="Cyclos Debit Wallet Partner",
        tracking=True,
    )

    cyclos_date_last_reconversion_check = fields.Datetime(
        "Last reconversion date on Cyclos",
    )

    def get_currency_json_data(self):
        """Return normalized currency's data."""
        res = super().get_currency_json_data()
        if self.engine != "cyclos":
            return res

        res["type"] = "{}:{}".format(
            "cyclos",
            self.get_cyclos_server_domain(),
        )
        return res

    def get_cyclos_server_domain(self):
        self.ensure_one()
        url = self.cyclos_server_url
        if not url:
            msg = "Cyclos URL in Odoo configuration is empty"
            raise NotFound(msg)
        parsed_uri = urlparse(url)
        if not parsed_uri or not parsed_uri.netloc:
            msg = f"Cyclos URL {url!r} in Odoo configuration is not a valid url"
            raise ValueError(
                msg,
            )
        if not re.search(
            r"^[a-z0-9-]+(\.[a-z0-9-]+)*(:[0-9]+)?$",
            parsed_uri.netloc.lower(),
        ):
            msg = f"domain {parsed_uri.netloc!r} in Odoo URL {url!r} configuration is not valid"
            raise ValueError(
                msg,
            )
        return parsed_uri.netloc

    def cyclos_rest_call(
        self,
        method,
        entrypoint,
        data=None,
        api_login=False,
        api_password=False,
    ):
        if data is None:
            data = {}
        self.ensure_one()
        headers = {"Content-type": "application/json", "Accept": "text/plain"}
        requests.packages.urllib3.disable_warnings()
        if not api_login:
            api_login = self.cyclos_server_login
        if not api_password:
            api_password = self.cyclos_server_password
        api_url = f"{self.cyclos_server_url}{entrypoint}"
        res = requests.request(
            method.lower(),
            api_url,
            auth=HTTPBasicAuth(api_login, api_password),
            verify=False,
            data=json.dumps(data),
            headers=headers,
        )
        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                msg = f"404 when trying to reach cyclos on {api_url}"
                raise Exception(msg)
            try:
                e.response.json()
                _logger.debug(e.response.json())
            except ValueError as e:
                _logger.debug(e.response.text)
                msg = f"Non-json output from cyclos on {api_url}"
                raise Exception(msg)

            if e.response.status_code == 422:
                msg = self.build_cyclos_error_message(e)
                if msg != "":
                    msg = "Cyclos serveur complained about:\n{}".format("\n".join(msg))
                    raise ValueError(
                        msg,
                        e.response,
                    )
            raise
        return res

    def build_cyclos_error_message(self, e):
        json_error = e.response.json()
        msg = ""
        if json_error.get("code") == "validation":
            if json_error.get("propertyErrors"):
                error = json_error.get("propertyErrors")
            elif json_error.get("generalErrors"):
                error = json_error.get("generalErrors")

            if isinstance(error, list):
                msg = ["  - %s" % v for v in error]
            elif isinstance(error, dict):
                msg = ["  - %s: %s" % (k, ", ".join(v)) for k, v in error.items()]
            else:
                msg = repr(error)
        return msg

    def _retrieve_last_debit_transactions(self, start=None, end=None):
        """Retrieve the last debit transactions from the Cyclos backend.

        A list of transactions (dictionary) is expected, with the
        following data:

        - sender: the Odoo name of the wallet concerned by the debit request,
        - amount: the amount debited from the wallet,
        - transaction_id: the transaction ID in the digital currency backend
        - transaction_date: the timestamp of the transaction.

        """

        self.ensure_one()
        yield from super()._retrieve_last_debit_transactions(start, end)

        if self.engine != "cyclos":
            return

        # Retrieve all the debit transactions since the last check
        # minus 1 min
        backend_ident = f"cyclos://{self.get_cyclos_server_domain()}"

        # we need dates on ISO8601 format "1970-01-01T00:00:00.000",
        # then encoded to be in an URL
        if start is not None:
            if not isinstance(start, str):
                raise ValueError("Start date must be a string in ISO8601 format")
            start_date = start
        else:
            if self.cyclos_date_last_reconversion_check:
                start_date = (
                    self.cyclos_date_last_reconversion_check - timedelta(minutes=1)
                ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            else:
                start_date = "1970-01-01T00:00:00.000"
        encoded_start_date = quote(start_date, safe="")

        if end is not None:
            if not isinstance(end, str):
                raise ValueError("End date must be a string in ISO8601 format")
            encoded_end_date = quote(end, safe="")
            period_range = (
                f"datePeriod={encoded_start_date}&datePeriod={encoded_end_date}"
            )
            _logger.info(
                f"Start reconversion check on Cyclos from {start_date} to {end}"
            )
        else:
            period_range = f"datePeriod={encoded_start_date}"
            _logger.info(
                f"Start reconversion check on Cyclos from {start_date} to now"
            )

        # Set all the search criteria in the REST request entrypoint
        entrypoint = (
            f"/transactions?{period_range}&orderBy=dateAsc&toAccountTypes=debit"
        )

        # Get the transactions from Cyclos
        response = self.cyclos_rest_call("GET", entrypoint)
        transactions = json.loads(response.text)

        _logger.info(
            f"{len(transactions)} transactions found from Cyclos."
        )
        for tx in transactions:
            date_tx = datetime.utcfromtimestamp(
                datetime.fromisoformat(tx["date"]).timestamp(),
            )
            if ("{:0.2f}".format(float(tx["amount"]))) != tx["amount"]:
                msg = "Could not convert amount {!r} to float reliably".format(
                    tx["amount"],
                )
                raise ValueError(
                    msg,
                )
            yield {
                "sender": "cyclos:{}".format(tx["from"]["user"]["id"]),
                "amount": float(tx["amount"]),
                "transaction_id": tx["id"],
                "backend_ident": backend_ident,
                "transaction_date": date_tx,
            }
            self.cyclos_date_last_reconversion_check = date_tx
            self.env.cr.commit()

    def _safe_wallet_partners(self):
        return [
            *super()._safe_wallet_partners(),
            self.cyclos_debit_wallet_partner,
        ]
