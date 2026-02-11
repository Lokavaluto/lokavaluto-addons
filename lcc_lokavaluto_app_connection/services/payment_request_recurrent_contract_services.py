from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component
from odoo.exceptions import ValidationError
from ..tools import (
    transform_backend_keys_in_currency_uris,
    transform_wallet_backend_keys_in_wallet_uris,
    transform_wallet_uris_in_wallet_backend_keys,
)


class PaymentRecurrentContractService(Component):
    _inherit = "base.rest.service"
    _name = "payment.request.recurrent.contract.service"
    _usage = "payment_request_recurrent_contract"
    _collection = "lokavaluto.private.services"
    _description = """
        Payment Request Recurrent Contract Services
        Access to the payment request recurrent contract services is only allowed to authenticated users.
        If you are not authenticated go to <a href='/web/login'>Login</a>
    """

    @restapi.method(
        [(["/create-payment-request-recurrent-contract"], "POST")],
        input_param=Datamodel("create.payment.request.recurrent.contracts.params"),
    )
    def create_payment_request_recurrent_contract(self, params) -> list:
        PaymentRequestRecurrentContract = self.env["payment.request.recurrent.contract"]
        Wallet = self.env["res.partner.backend"]

        currency_uri = transform_backend_keys_in_currency_uris([params.currency_uri])[0]

        currency_id = self.env["res.alt.currency"].search([("uri", "=", currency_uri)])
        if not currency_id:
            raise ValidationError("Currency not found")
        if len(currency_id) > 1:
            raise ValidationError("Multiple currencies found for the given URI")

        creator_wallet_uri = transform_wallet_backend_keys_in_wallet_uris(
            [params.creator_wallet_uri], currency_id.ident
        )[0]
        creator_wallet_id = Wallet.search([("uri", "=", creator_wallet_uri)])
        if not creator_wallet_id:
            raise ValidationError("Creator wallet not found")
        if len(creator_wallet_id) > 1:
            raise ValidationError("Multiple creator wallets found")

        created_ids = []
        for idx, contract in enumerate(params.contracts):
            sender_wallet_uri = transform_wallet_backend_keys_in_wallet_uris(
                [contract["sender_wallet_uri"]], currency_id.ident
            )[0]
            receiver_wallet_uri = transform_wallet_backend_keys_in_wallet_uris(
                [contract["receiver_wallet_uri"]], currency_id.ident
            )[0]

            sender_wallet_id = Wallet.search([("uri", "=", sender_wallet_uri)])
            receiver_wallet_id = Wallet.search([("uri", "=", receiver_wallet_uri)])

            if not sender_wallet_id:
                raise ValidationError(
                    f"Row {idx + 1}: Sender wallet not found ({contract['sender_wallet_uri']})"
                )
            if len(sender_wallet_id) > 1:
                raise ValidationError(f"Row {idx + 1}: Multiple sender wallets found")
            if not receiver_wallet_id:
                raise ValidationError(
                    f"Row {idx + 1}: Receiver wallet not found ({contract['receiver_wallet_uri']})"
                )
            if len(receiver_wallet_id) > 1:
                raise ValidationError(f"Row {idx + 1}: Multiple receiver wallets found")

            payment_request_recurrent_contract = PaymentRequestRecurrentContract.sudo().create(
                {
                    "creator_wallet_id": creator_wallet_id.id,
                    "alt_currency_id": creator_wallet_id.alt_currency_id.id,
                    "sender_wallet_id": sender_wallet_id.id,
                    "receiver_wallet_id": receiver_wallet_id.id,
                    "amount": contract["amount"],
                    "message": contract.get("message"),
                    "date_start": contract["date_start"],
                    "date_end": contract.get("date_end"),
                    "recurring_rule_type": contract["recurring_rule_type"],
                    "recurring_interval": contract["recurring_interval"]
                }
            )
            payment_request_recurrent_contract.action_confirm()
            created_ids.append(payment_request_recurrent_contract.id)

        return created_ids

    @restapi.method(
        [(["/list-payment-request-recurrent-contracts"], "GET")],
        input_param=Datamodel("list.payment.request.recurrent.contracts.params"),
    )
    def list_payment_request_recurrent_contracts(self, params) -> list:
        """List payment request recurrent contracts for a wallet

        :param list_payment_request_recurrent_contracts_params: Datamodel containing the parameters to list payment request
        recurrent contracts
        :return: List of payment request recurrent contracts
        :rtype: list
        """
        PaymentRequestRecurrentContract = self.env["payment.request.recurrent.contract"]
        Wallet = self.env["res.partner.backend"]

        # Workaround to transform backend keys into URIs
        currency_uri = transform_backend_keys_in_currency_uris(
            [params.currency_uri]
        )[0]

        currency_id = self.env["res.alt.currency"].search([("uri", "=", currency_uri)])
        if not currency_id:
            raise ValidationError("Currency not found")
        if len(currency_id) > 1:
            raise ValidationError("Multiple currencies found for the given URI")
        wallet_uri = transform_wallet_backend_keys_in_wallet_uris(
            [params.wallet_uri],
            currency_id.ident,
        )[0]
        # End workaround

        wallet_id = Wallet.search([("uri", "=", wallet_uri)])

        if not wallet_id:
            raise ValidationError("Wallet not found")
        if len(wallet_id) > 1:
            raise ValidationError("Multiple wallets found for the given URI")

        domain = [("creator_wallet_id", "=", wallet_id.id)]
        if params.state:
            domain.append(("state", "in", params.state))

        payment_request_recurrent_contracts = PaymentRequestRecurrentContract.sudo().search(
            domain, order="create_date desc"
        )
        return [
            {
                "id": pr.id,
                "creator_wallet_uri": transform_wallet_uris_in_wallet_backend_keys(
                    [pr.creator_wallet_id.uri]
                )[0],
                "creator_name": pr.creator_wallet_id.partner_id.name,
                "sender_wallet_uri": transform_wallet_uris_in_wallet_backend_keys(
                    [pr.sender_wallet_id.uri]
                )[0],
                "sender_name": pr.sender_wallet_id.partner_id.name,
                "sender_partner_id": pr.sender_wallet_id.partner_id.id,
                "receiver_wallet_uri": transform_wallet_uris_in_wallet_backend_keys(
                    [pr.receiver_wallet_id.uri]
                )[0],
                "receiver_name": pr.receiver_wallet_id.partner_id.name,
                "receiver_partner_id": pr.receiver_wallet_id.partner_id.id,
                "amount": pr.amount,
                "message": pr.message,
                "date_start": pr.date_start.isoformat() if pr.date_start else None,
                "date_end": pr.date_end.isoformat() if pr.date_end else None,
                "recurring_rule_type": pr.recurring_rule_type,
                "recurring_interval": pr.recurring_interval,
                "state": pr.state,
                "recurring_next_date": pr.recurring_next_date.isoformat() if pr.recurring_next_date else None,
                "create_date": pr.create_date.timestamp(),
            }
            for pr in payment_request_recurrent_contracts
        ]

    @restapi.method(
        [(["/delete-payment-request-recurrent-contracts"], "DELETE")],
        input_param=Datamodel("delete.payment.request.recurrent.contracts.params"),
    )
    def delete_payment_request_recurrent_contracts(self, params) -> bool:
        """Delete payment request recurrent contracts

        :param delete_payment_request_recurrent_contracts_params: Datamodel containing the parameters to delete payment request
        recurrent contracts
        :return: True if the payment request recurrent contracts were deleted, False otherwise
        :rtype: bool
        """
        PaymentRequestRecurrentContract = self.env["payment.request.recurrent.contract"]
        Wallet = self.env["res.partner.backend"]

        # Workaround to transform backend keys into URIs
        currency_uri = transform_backend_keys_in_currency_uris(
            [params.currency_uri]
        )[0]

        currency_id = self.env["res.alt.currency"].search([("uri", "=", currency_uri)])
        if not currency_id:
            raise ValidationError("Currency not found")
        if len(currency_id) > 1:
            raise ValidationError("Multiple currencies found for the given URI")
        wallet_uri = transform_wallet_backend_keys_in_wallet_uris(
            [params.wallet_uri],
            currency_id.ident,
        )[0]
        # End workaround

        wallet_id = Wallet.search([("uri", "=", wallet_uri)])

        if not wallet_id:
            raise ValidationError("Wallet not found")
        if len(wallet_id) > 1:
            raise ValidationError("Multiple wallets found for the given URI")

        payment_request_recurrent_contracts = PaymentRequestRecurrentContract.sudo().search(
            [
                ("id", "in", params.payment_request_ids),
            ]
        )
        if any(payment_request_recurrent_contract.creator_wallet_id.id != wallet_id.id for payment_request_recurrent_contract in payment_request_recurrent_contracts):
            raise ValidationError("Some payment request recurrent contracts do not belong to the given wallet.")
        if len(payment_request_recurrent_contracts) != len(params.payment_request_ids):
            raise ValidationError("Some payment request recurrent contracts were not found")

        payment_request_recurrent_contracts.unlink()
        return True
