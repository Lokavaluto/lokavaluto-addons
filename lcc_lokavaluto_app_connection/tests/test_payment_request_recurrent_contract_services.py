from datetime import date, timedelta

from odoo.addons.component.tests.common import TransactionComponentCase
from odoo.exceptions import ValidationError

from ..datamodel.payment_request_recurrent_contract_info import (
    CreatePaymentRequestRecurrentContractsParam,
    ListPaymentRequestRecurrentContractsParams,
    DeletePaymentRequestRecurrentContractsParams,
)
from ..tools import transform_wallet_uris_in_wallet_backend_keys


class TestPaymentRequestRecurrentContractServices(TransactionComponentCase):
    def setUp(self):
        super().setUp()

        self.ResCompany = self.env["res.company"]
        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]
        self.RecurrentContract = self.env["payment.request.recurrent.contract"]
        self.Services = self.env["lokavaluto.private.services"]

    def _create_company(self, name="Acme Corp"):
        return self.ResCompany.create({"name": name})

    def _create_res_partner(self, name="John Doe"):
        return self.ResPartner.create({"name": name})

    def _create_res_user(self, login="jdoe", partner=None, company=None):
        return self.ResUsers.create({
            "login": login,
            "partner_id": partner.id,
            "company_id": company.id,
            "company_ids": [(6, 0, [company.id])],
        })

    def _create_alt_currency(self, ident="currency"):
        return self.ResAltCurrency.create(
            {
                "name": ident,
                "ident": ident,
                "active": True,
                "engine": "foo",
            }
        )

    def _create_res_partner_backend(self, partner, currency, ident="98765"):
        return self.ResPartnerBackend.create(
            {
                "name": f"foo:{ident}",
                "alt_currency_id": currency.id,
                "partner_id": partner.id,
                "ident": ident,
            }
        )

    def _create_recurrent_contract(
        self,
        creator_wallet,
        sender_wallet,
        receiver_wallet,
        amount,
        message,
        date_start,
        date_end=None,
        recurring_rule_type="monthly",
        recurring_interval=1,
    ):
        return self.RecurrentContract.create(
            {
                "creator_wallet_id": creator_wallet.id,
                "alt_currency_id": creator_wallet.alt_currency_id.id,
                "sender_wallet_id": sender_wallet.id,
                "receiver_wallet_id": receiver_wallet.id,
                "amount": amount,
                "message": message,
                "date_start": date_start,
                "date_end": date_end,
                "recurring_rule_type": recurring_rule_type,
                "recurring_interval": recurring_interval,
            }
        )

    # -------------------------------------------------------------------------
    # Test: Create Payment Request Recurrent Contract Service
    # -------------------------------------------------------------------------

    def test_create_recurrent_contract_service_1(self):
        """Test creating a recurrent contract via the service"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        collection = self.Services.with_user(user).browse(1)

        start_date = date.today()
        end_date = date.today() + timedelta(days=365)

        # Use service to create recurrent contract
        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = CreatePaymentRequestRecurrentContractsParam(
                currency_uri=currency.uri,
                creator_wallet_uri=wallet_1.uri,
                contracts=[
                    {
                        "sender_wallet_uri": wallet_2.uri,
                        "receiver_wallet_uri": wallet_1.uri,
                        "amount": 100.0,
                        "message": "Monthly subscription",
                        "date_start": start_date.isoformat(),
                        "date_end": end_date.isoformat(),
                        "recurring_rule_type": "monthly",
                        "recurring_interval": 1,
                    }
                ],
            )
            res = service.create_payment_request_recurrent_contract(params)

            self.assertTrue(res)
            self.assertEqual(len(res), 1)

            contract = self.RecurrentContract.browse(res[0])
            self.assertEqual(contract.creator_wallet_id.id, wallet_1.id)
            self.assertEqual(contract.sender_wallet_id.id, wallet_2.id)
            self.assertEqual(contract.receiver_wallet_id.id, wallet_1.id)
            self.assertEqual(contract.amount, 100.0)
            self.assertEqual(contract.message, "Monthly subscription")
            self.assertEqual(contract.recurring_rule_type, "monthly")
            self.assertEqual(contract.recurring_interval, 1)
            self.assertEqual(contract.state, "open")  # action_confirm is called

    def test_create_recurrent_contract_service_2(self):
        """Test creating multiple recurrent contracts in a single request"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        collection = self.Services.with_user(user).browse(1)

        start_date = date.today()

        # Use service to create multiple recurrent contracts
        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = CreatePaymentRequestRecurrentContractsParam(
                currency_uri=currency.uri,
                creator_wallet_uri=wallet_1.uri,
                contracts=[
                    {
                        "sender_wallet_uri": wallet_2.uri,
                        "receiver_wallet_uri": wallet_1.uri,
                        "amount": 50.0,
                        "message": "Weekly payment",
                        "date_start": start_date.isoformat(),
                        "recurring_rule_type": "weekly",
                        "recurring_interval": 1,
                    },
                    {
                        "sender_wallet_uri": wallet_1.uri,
                        "receiver_wallet_uri": wallet_2.uri,
                        "amount": 200.0,
                        "message": "Yearly fee",
                        "date_start": start_date.isoformat(),
                        "recurring_rule_type": "yearly",
                        "recurring_interval": 1,
                    },
                ],
            )
            res = service.create_payment_request_recurrent_contract(params)

            self.assertEqual(len(res), 2)

            contract_1 = self.RecurrentContract.browse(res[0])
            self.assertEqual(contract_1.amount, 50.0)
            self.assertEqual(contract_1.recurring_rule_type, "weekly")

            contract_2 = self.RecurrentContract.browse(res[1])
            self.assertEqual(contract_2.amount, 200.0)
            self.assertEqual(contract_2.recurring_rule_type, "yearly")

    def test_create_recurrent_contract_service_invalid_currency(self):
        """Test creating a recurrent contract with invalid currency fails"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        collection = self.Services.with_user(user).browse(1)

        start_date = date.today()

        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = CreatePaymentRequestRecurrentContractsParam(
                currency_uri="invalid:currency",
                creator_wallet_uri=wallet_1.uri,
                contracts=[
                    {
                        "sender_wallet_uri": wallet_2.uri,
                        "receiver_wallet_uri": wallet_1.uri,
                        "amount": 100.0,
                        "date_start": start_date.isoformat(),
                        "recurring_rule_type": "monthly",
                        "recurring_interval": 1,
                    }
                ],
            )
            with self.assertRaises(ValidationError) as context:
                service.create_payment_request_recurrent_contract(params)
            self.assertIn("Currency not found", str(context.exception))

    def test_create_recurrent_contract_service_invalid_creator_wallet(self):
        """Test creating a recurrent contract with invalid creator wallet fails"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        collection = self.Services.with_user(user).browse(1)

        start_date = date.today()

        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = CreatePaymentRequestRecurrentContractsParam(
                currency_uri=currency.uri,
                creator_wallet_uri="invalid:wallet",
                contracts=[
                    {
                        "sender_wallet_uri": wallet_2.uri,
                        "receiver_wallet_uri": wallet_1.uri,
                        "amount": 100.0,
                        "date_start": start_date.isoformat(),
                        "recurring_rule_type": "monthly",
                        "recurring_interval": 1,
                    }
                ],
            )
            with self.assertRaises(ValidationError) as context:
                service.create_payment_request_recurrent_contract(params)
            self.assertIn("Creator wallet not found", str(context.exception))

    def test_create_recurrent_contract_service_invalid_sender_wallet(self):
        """Test creating a recurrent contract with invalid sender wallet fails"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        collection = self.Services.with_user(user).browse(1)

        start_date = date.today()

        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = CreatePaymentRequestRecurrentContractsParam(
                currency_uri=currency.uri,
                creator_wallet_uri=wallet_1.uri,
                contracts=[
                    {
                        "sender_wallet_uri": "invalid:sender",
                        "receiver_wallet_uri": wallet_1.uri,
                        "amount": 100.0,
                        "date_start": start_date.isoformat(),
                        "recurring_rule_type": "monthly",
                        "recurring_interval": 1,
                    }
                ],
            )
            with self.assertRaises(ValidationError) as context:
                service.create_payment_request_recurrent_contract(params)
            self.assertIn("Sender wallet not found", str(context.exception))

    # -------------------------------------------------------------------------
    # Test: List Payment Request Recurrent Contracts Service
    # -------------------------------------------------------------------------

    def test_list_recurrent_contracts_service_1(self):
        """Test listing recurrent contracts for a wallet"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        wallet_3 = self._create_res_partner_backend(partner, currency, ident="54321")

        start_date = date.today()

        # Create contracts for wallet_1
        contract_1 = self._create_recurrent_contract(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=75.0,
            message="First Contract",
            date_start=start_date,
        )
        contract_1.action_confirm()

        contract_2 = self._create_recurrent_contract(
            creator_wallet=wallet_1,
            sender_wallet=wallet_1,
            receiver_wallet=wallet_2,
            amount=125.0,
            message="Second Contract",
            date_start=start_date,
        )
        contract_2.action_confirm()

        # Create contract for different wallet (should not appear in results)
        contract_3 = self._create_recurrent_contract(
            creator_wallet=wallet_3,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_3,
            amount=200.0,
            message="Third Contract",
            date_start=start_date,
        )
        contract_3.action_confirm()

        collection = self.Services.with_user(user).browse(1)

        # Use service to list recurrent contracts for wallet_1
        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = ListPaymentRequestRecurrentContractsParams(
                currency_uri=currency.uri,
                wallet_uri=wallet_1.uri,
            )
            contracts = service.list_payment_request_recurrent_contracts(params)

            self.assertEqual(len(contracts), 2)

            # Verify contract IDs are in the results
            contract_ids = [c["id"] for c in contracts]
            self.assertIn(contract_1.id, contract_ids)
            self.assertIn(contract_2.id, contract_ids)
            self.assertNotIn(contract_3.id, contract_ids)

    def test_list_recurrent_contracts_service_with_state_filter(self):
        """Test listing recurrent contracts with state filter"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")

        start_date = date.today()

        # Create open contract
        contract_open = self._create_recurrent_contract(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=75.0,
            message="Open Contract",
            date_start=start_date,
        )
        contract_open.action_confirm()

        # Create closed contract
        contract_closed = self._create_recurrent_contract(
            creator_wallet=wallet_1,
            sender_wallet=wallet_1,
            receiver_wallet=wallet_2,
            amount=125.0,
            message="Closed Contract",
            date_start=start_date,
        )
        contract_closed.action_confirm()
        contract_closed.action_close()

        collection = self.Services.with_user(user).browse(1)

        # Use service to list only open contracts
        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = ListPaymentRequestRecurrentContractsParams(
                currency_uri=currency.uri,
                wallet_uri=wallet_1.uri,
                state=["open"],
            )
            contracts = service.list_payment_request_recurrent_contracts(params)

            self.assertEqual(len(contracts), 1)
            self.assertEqual(contracts[0]["id"], contract_open.id)
            self.assertEqual(contracts[0]["state"], "open")

    def test_list_recurrent_contracts_service_invalid_wallet(self):
        """Test listing recurrent contracts with invalid wallet fails"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        collection = self.Services.with_user(user).browse(1)

        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = ListPaymentRequestRecurrentContractsParams(
                currency_uri=currency.uri,
                wallet_uri="invalid:wallet",
            )
            with self.assertRaises(ValidationError) as context:
                service.list_payment_request_recurrent_contracts(params)
            self.assertIn("Wallet not found", str(context.exception))

    def test_list_recurrent_contracts_service_response_format(self):
        """Test that list response contains all expected fields"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")

        start_date = date.today()
        end_date = date.today() + timedelta(days=365)

        contract = self._create_recurrent_contract(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=99.99,
            message="Test message",
            date_start=start_date,
            date_end=end_date,
            recurring_rule_type="weekly",
            recurring_interval=2,
        )
        contract.action_confirm()

        collection = self.Services.with_user(user).browse(1)

        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = ListPaymentRequestRecurrentContractsParams(
                currency_uri=currency.uri,
                wallet_uri=wallet_1.uri,
            )
            contracts = service.list_payment_request_recurrent_contracts(params)

            self.assertEqual(len(contracts), 1)
            result = contracts[0]

            # Verify all expected fields are present
            self.assertEqual(result["id"], contract.id)
            self.assertEqual(result["amount"], 99.99)
            self.assertEqual(result["message"], "Test message")
            self.assertEqual(result["state"], "open")
            self.assertEqual(result["recurring_rule_type"], "weekly")
            self.assertEqual(result["recurring_interval"], 2)
            self.assertEqual(result["date_start"], start_date.isoformat())
            self.assertEqual(result["date_end"], end_date.isoformat())
            self.assertEqual(result["creator_name"], partner.name)
            self.assertEqual(result["sender_name"], partner.name)
            self.assertEqual(result["receiver_name"], partner.name)
            self.assertIn("creator_wallet_uri", result)
            self.assertIn("sender_wallet_uri", result)
            self.assertIn("receiver_wallet_uri", result)
            self.assertIn("sender_partner_id", result)
            self.assertIn("receiver_partner_id", result)
            self.assertIn("recurring_next_date", result)
            self.assertIn("create_date", result)

    # -------------------------------------------------------------------------
    # Test: Delete Payment Request Recurrent Contracts Service
    # -------------------------------------------------------------------------

    def test_delete_recurrent_contracts_service_1(self):
        """Test deleting recurrent contracts via the service"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")

        start_date = date.today()

        contract = self._create_recurrent_contract(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=100.0,
            message="Contract to delete",
            date_start=start_date,
        )
        contract_id = contract.id

        collection = self.Services.with_user(user).browse(1)

        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = DeletePaymentRequestRecurrentContractsParams(
                currency_uri=currency.uri,
                wallet_uri=wallet_1.uri,
                payment_request_ids=[contract_id],
            )
            res = service.delete_payment_request_recurrent_contracts(params)

            self.assertTrue(res)
            # Verify contract is deleted
            self.assertFalse(self.RecurrentContract.browse(contract_id).exists())

    def test_delete_recurrent_contracts_service_multiple(self):
        """Test deleting multiple recurrent contracts"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")

        start_date = date.today()

        contract_1 = self._create_recurrent_contract(
            creator_wallet=wallet_1,
            sender_wallet=wallet_2,
            receiver_wallet=wallet_1,
            amount=100.0,
            message="First to delete",
            date_start=start_date,
        )
        contract_2 = self._create_recurrent_contract(
            creator_wallet=wallet_1,
            sender_wallet=wallet_1,
            receiver_wallet=wallet_2,
            amount=200.0,
            message="Second to delete",
            date_start=start_date,
        )
        contract_ids = [contract_1.id, contract_2.id]

        collection = self.Services.with_user(user).browse(1)

        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = DeletePaymentRequestRecurrentContractsParams(
                currency_uri=currency.uri,
                wallet_uri=wallet_1.uri,
                payment_request_ids=contract_ids,
            )
            res = service.delete_payment_request_recurrent_contracts(params)

            self.assertTrue(res)
            # Verify both contracts are deleted
            for cid in contract_ids:
                self.assertFalse(self.RecurrentContract.browse(cid).exists())

    def test_delete_recurrent_contracts_service_wrong_wallet(self):
        """Test deleting contracts belonging to another wallet fails"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner_1 = self._create_res_partner(name="Partner 1")
        partner_2 = self._create_res_partner(name="Partner 2")
        user = self._create_res_user(partner=partner_1, company=company)
        wallet_1 = self._create_res_partner_backend(partner_1, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner_2, currency, ident="67890")

        start_date = date.today()

        # Contract created by wallet_2
        contract = self._create_recurrent_contract(
            creator_wallet=wallet_2,
            sender_wallet=wallet_1,
            receiver_wallet=wallet_2,
            amount=100.0,
            message="Contract of wallet_2",
            date_start=start_date,
        )

        collection = self.Services.with_user(user).browse(1)

        # Try to delete with wallet_1 (should fail)
        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = DeletePaymentRequestRecurrentContractsParams(
                currency_uri=currency.uri,
                wallet_uri=wallet_1.uri,
                payment_request_ids=[contract.id],
            )
            with self.assertRaises(ValidationError) as context:
                service.delete_payment_request_recurrent_contracts(params)
            self.assertIn(
                "Some payment request recurrent contracts do not belong to the given wallet",
                str(context.exception),
            )
            # Contract should still exist
            self.assertTrue(contract.exists())

    def test_delete_recurrent_contracts_service_not_found(self):
        """Test deleting non-existent contracts fails"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")

        collection = self.Services.with_user(user).browse(1)

        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = DeletePaymentRequestRecurrentContractsParams(
                currency_uri=currency.uri,
                wallet_uri=wallet_1.uri,
                payment_request_ids=[99999],  # Non-existent ID
            )
            with self.assertRaises(ValidationError) as context:
                service.delete_payment_request_recurrent_contracts(params)
            self.assertIn(
                "Some payment request recurrent contracts were not found",
                str(context.exception),
            )

    def test_delete_recurrent_contracts_service_invalid_wallet(self):
        """Test deleting with invalid wallet fails"""
        # Create data
        company = self._create_company()
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        user = self._create_res_user(partner=partner, company=company)
        collection = self.Services.with_user(user).browse(1)

        with collection.work_on("payment.request.recurrent.contract") as work:
            service = work.component(usage="payment_request_recurrent_contract")
            params = DeletePaymentRequestRecurrentContractsParams(
                currency_uri=currency.uri,
                wallet_uri="invalid:wallet",
                payment_request_ids=[1],
            )
            with self.assertRaises(ValidationError) as context:
                service.delete_payment_request_recurrent_contracts(params)
            self.assertIn("Wallet not found", str(context.exception))
