from odoo.addons.base_rest import restapi
from odoo.addons.base_rest_datamodel.restapi import Datamodel
from odoo.addons.component.core import Component
from odoo.exceptions import ValidationError
from ..tools import (
    transform_backend_keys_in_currency_uris,
    transform_wallet_backend_keys_in_wallet_uris,
    transform_wallet_uris_in_wallet_backend_keys,
)


class PartnerService(Component):
    _inherit = "base.rest.service"
    _name = "payment.request.service"
    _usage = "payment_request"
    _collection = "lokavaluto.private.services"
    _description = """
        Payment Request Services
        Access to the payment request services is only allowed to authenticated users.
        If you are not authenticated go to <a href='/web/login'>Login</a>
    """

    @restapi.method(
        [(["/create-payment-request"], "POST")],
        input_param=Datamodel("create.payment.request.params"),
    )
    def create_payment_request(self, params) -> list:
        PaymentRequest = self.env["payment.request"]
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
        for idx, req in enumerate(params.requests):
            sender_wallet_uri = transform_wallet_backend_keys_in_wallet_uris(
                [req["sender_wallet_uri"]], currency_id.ident
            )[0]
            receiver_wallet_uri = transform_wallet_backend_keys_in_wallet_uris(
                [req["receiver_wallet_uri"]], currency_id.ident
            )[0]

            sender_wallet_id = Wallet.search([("uri", "=", sender_wallet_uri)])
            receiver_wallet_id = Wallet.search([("uri", "=", receiver_wallet_uri)])

            if not sender_wallet_id:
                raise ValidationError(
                    f"Row {idx + 1}: Sender wallet not found ({req['sender_wallet_uri']})"
                )
            if len(sender_wallet_id) > 1:
                raise ValidationError(f"Row {idx + 1}: Multiple sender wallets found")
            if not receiver_wallet_id:
                raise ValidationError(
                    f"Row {idx + 1}: Receiver wallet not found ({req['receiver_wallet_uri']})"
                )
            if len(receiver_wallet_id) > 1:
                raise ValidationError(f"Row {idx + 1}: Multiple receiver wallets found")

            payment_request = PaymentRequest.sudo().create(
                {
                    "creator_wallet_id": creator_wallet_id.id,
                    "alt_currency_id": creator_wallet_id.alt_currency_id.id,
                    "sender_wallet_id": sender_wallet_id.id,
                    "receiver_wallet_id": receiver_wallet_id.id,
                    "amount": req["amount"],
                    "message": req.get("message"),
                }
            )
            created_ids.append(payment_request.id)

        return created_ids

    @restapi.method(
        [(["/list-payment-requests"], "GET")],
        input_param=Datamodel("list.payment.requests.params"),
    )
    def list_payment_requests(self, list_payment_requests_params) -> list:
        """List payment requests for a wallet

        :param list_payment_requests_params: Datamodel containing the parameters to list payment requests
        :return: List of payment requests
        :rtype: list
        """
        PaymentRequest = self.env["payment.request"]
        Wallet = self.env["res.partner.backend"]

        # Workaround to transform backend keys into URIs
        currency_uri = transform_backend_keys_in_currency_uris(
            [list_payment_requests_params.currency_uri]
        )[0]

        currency_id = self.env["res.alt.currency"].search([("uri", "=", currency_uri)])
        if not currency_id:
            raise ValidationError("Currency not found")
        if len(currency_id) > 1:
            raise ValidationError("Multiple currencies found for the given URI")
        wallet_uri = transform_wallet_backend_keys_in_wallet_uris(
            [list_payment_requests_params.wallet_uri],
            currency_id.ident,
        )[0]
        # End workaround

        wallet_id = Wallet.search([("uri", "=", wallet_uri)])

        if not wallet_id:
            raise ValidationError("Wallet not found")
        if len(wallet_id) > 1:
            raise ValidationError("Multiple wallets found for the given URI")

        domain = [
            "|",
            ("receiver_wallet_id", "=", wallet_id.id),
            ("sender_wallet_id", "=", wallet_id.id),
        ]
        if list_payment_requests_params.state:
            domain.append(("state", "in", list_payment_requests_params.state))

        payment_requests = PaymentRequest.sudo().search(
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
                "state": pr.state,
                "create_date": pr.create_date.timestamp(),
            }
            for pr in payment_requests
        ]

    @restapi.method(
        [(["/update-payment-request"], "POST")],
        input_param=Datamodel("update.payment.request.params"),
    )
    def update_payment_request(self, update_payment_request_params) -> bool:
        """Update a payment request status

        :param update_payment_request_params: Datamodel containing the parameters to update a payment request
        :return: True if the payment request was updated successfully, False otherwise
        :rtype: bool
        """
        PaymentRequest = self.env["payment.request"]
        Wallet = self.env["res.partner.backend"]

        # Workaround to transform backend keys into URIs
        currency_uri = transform_backend_keys_in_currency_uris(
            [update_payment_request_params.currency_uri]
        )[0]
        currency_id = self.env["res.alt.currency"].search([("uri", "=", currency_uri)])
        if not currency_id:
            raise ValidationError("Currency not found")
        if len(currency_id) > 1:
            raise ValidationError("Multiple currencies found for the given URI")
        wallet_uri = transform_wallet_backend_keys_in_wallet_uris(
            [update_payment_request_params.wallet_uri], currency_id.ident
        )[0]
        # End workaround

        wallet_id = Wallet.search([("uri", "=", wallet_uri)])
        if not wallet_id:
            raise ValidationError("Wallet not found")
        if len(wallet_id) > 1:
            raise ValidationError("Multiple wallets found for the given URI")

        if wallet_id not in self.env.user.partner_id.lcc_backend_ids:
            raise ValidationError(
                "Only wallet owners can make the payment request update"
            )

        payment_request = PaymentRequest.sudo().browse(
            update_payment_request_params.payment_request_id
        )
        if not payment_request:
            raise ValidationError("Payment request not found")

        message_key = "message"
        if update_payment_request_params.status == "paid":
            if payment_request.sender_wallet_id != wallet_id:
                raise ValidationError(
                    "Only the sender wallet can mark the payment request as paid"
                )
            message_key = "tx_id"
        elif update_payment_request_params.status == "refused":
            if payment_request.sender_wallet_id != wallet_id:
                raise ValidationError(
                    "Only the sender wallet can refuse the payment request"
                )
            message_key = "refusal_reason"
        elif update_payment_request_params.status == "cancelled":
            if payment_request.creator_wallet_id != wallet_id:
                raise ValidationError(
                    "Only the creator wallet can cancel the payment request"
                )
        elif update_payment_request_params.status == "open":
            raise ValidationError("Cannot change the payment request status to open")

        # Update the payment request status
        payment_request.sudo().write(
            {
                "state": update_payment_request_params.status,
                message_key: update_payment_request_params.message,
            }
        )
        return True
