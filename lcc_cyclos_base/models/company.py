import json
import re
import requests
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse, quote
from werkzeug.exceptions import NotFound
from odoo import models, fields

import logging

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = "res.company"

    cyclos_server_url = fields.Char(string="Url for cyclos server")
    cyclos_client_token = fields.Char(string="Client token auth for cyclos server")

    cyclos_server_login = fields.Char(string="Login for cyclos server")

    cyclos_server_password = fields.Char(string="Password for cyclos server")

    cyclos_debit_wallet_partner = fields.Many2one(
        "res.partner", string="Cyclos Debit Wallet Partner"
    )

    cyclos_date_last_reconversion_check = fields.Datetime(
        "Last reconversion date on Cyclos"
    )

    def get_cyclos_server_domain(self):
        self.ensure_one()
        url = self.cyclos_server_url
        if not url:
            raise NotFound("Cyclos URL in Odoo configuration is empty")
        parsed_uri = urlparse(url)
        if not parsed_uri or not parsed_uri.netloc:
            raise ValueError(
                "Cyclos URL %r in Odoo configuration is not a valid url" % url
            )
        if not re.search(
            "^[a-z0-9-]+(\.[a-z0-9-]+)*(:[0-9]+)?$", parsed_uri.netloc.lower()
        ):
            raise ValueError(
                "domain %r in Odoo URL %r configuration is not valid"
                % (parsed_uri.netloc, url)
            )
        return parsed_uri.netloc

    def cyclos_rest_call(
        self, method, entrypoint, data={}, api_login=False, api_password=False
    ):
        self.ensure_one()
        headers = {"Content-type": "application/json", "Accept": "text/plain"}
        requests.packages.urllib3.disable_warnings()
        if not api_login:
            api_login = self.cyclos_server_login
        if not api_password:
            api_password = self.cyclos_server_password
        api_url = "%s%s" % (self.cyclos_server_url, entrypoint)
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
                raise Exception("404 when trying to reach cyclos on %s" % api_url)
            try:
                json_output = e.response.json()
                _logger.debug(e.response.json())
            except ValueError as e:
                _logger.debug(e.response.text)
                raise Exception("Non-json output from cyclos on %s" % api_url)

            if e.response.status_code == 422:
                msg = self.build_cyclos_error_message(e)
                if msg != "":
                    raise ValueError(
                        "Cyclos serveur complained about:\n%s" % "\n".join(msg),
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

    def _retrieve_last_debit_transactions(self):
        """A list of transactions (dictionnary) is expected, with the following data:
        - sender: the Odoo name of the wallet concerned by the debit request,
        - amount: the amount debited from the wallet,
        - transaction_id: the transaction ID in the digital currency backend
        - transaction_date: the timestamp of the transaction
        """
        yield from super(Company, self)._retrieve_last_debit_transactions()

        # Retrieve all the debit transactions since the last check minus 1 min
        company_id = self.env.user.company_id

        backend_ident = "cyclos://%s" % company_id.get_cyclos_server_domain()

        # we need a date on ISO8601 format "1970-01-01T00:00:00.000", then encoded to be in an URL
        if not company_id.cyclos_date_last_reconversion_check:
            date = "1970-01-01T00:00:00.000"
        else:
            date = (
                company_id.cyclos_date_last_reconversion_check - timedelta(minutes=1)
            ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        encoded_date = quote(date, safe="")

        # Set all the search criteria in the REST request entrypoint
        entrypoint = (
            "/transactions?datePeriod=%s&orderBy=dateAsc&toAccountTypes=debit"
            % encoded_date
        )

        # Get the transactions from Cyclos
        response = company_id.cyclos_rest_call("GET", entrypoint)
        transactions = json.loads(response.text)
        for tx in transactions:
            date_tx = datetime.utcfromtimestamp(
                datetime.fromisoformat(tx["date"]).timestamp()
            )
            if ("%0.2f" % (float(tx["amount"]))) != tx["amount"]:
                raise ValueError(
                    "Could not convert amount %r to float reliably" % tx["amount"]
                )
            yield {
                "sender": "cyclos:%s" % tx["from"]["user"]["id"],
                "amount": float(tx["amount"]),
                "transaction_id": tx["id"],
                "backend_ident": backend_ident,
                "transaction_date": date_tx,
            }
            company_id.cyclos_date_last_reconversion_check = date_tx
            self.env.cr.commit()

    def _safe_wallet_partners(self):
        return super(Company, self)._safe_wallet_partners() + [
            self.cyclos_debit_wallet_partner
        ]
