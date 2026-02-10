from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo.tests.common import TransactionCase


class TestPaymentRequestRecurrentContract(TransactionCase):
    def setUp(self):
        super().setUp()

        self.ResPartner = self.env["res.partner"]
        self.ResPartnerBackend = self.env["res.partner.backend"]
        self.ResAltCurrency = self.env["res.alt.currency"]
        self.PaymentRequest = self.env["payment.request"]
        self.RecurrentContract = self.env["payment.request.recurrent.contract"]


    def _create_res_partner(self, name="John Doe"):
        return self.ResPartner.create({"name": name})

    def _create_alt_currency(self, ident="currency", safe_wallet_partner_id=None):
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
                "ident": ident
            }
        )
        # Create base data
        self.currency = self.env["res.alt.currency"].create({
            "name": "Test Currency",
            "ident": "test_currency",
            "active": True,
            "engine": "foo",
        })

        self.partner_sender = self.ResPartner.create({"name": "Sender Partner"})
        self.partner_receiver = self.ResPartner.create({"name": "Receiver Partner"})

        self.wallet_sender = self.ResPartnerBackend.create({
            "name": "foo:sender_wallet",
            "alt_currency_id": self.currency.id,
            "partner_id": self.partner_sender.id,
            "ident": "sender_001",
        })
        self.wallet_receiver = self.ResPartnerBackend.create({
            "name": "foo:receiver_wallet",
            "alt_currency_id": self.currency.id,
            "partner_id": self.partner_receiver.id,
            "ident": "receiver_001",
        })

    def _create_contract(
        self,
        creator_wallet,
        sender_wallet,
        receiver_wallet,
        amount=1,
        message="",
        date_start=date.today(),
        date_end=None,
        recurring_interval="1",
        recurring_rule_type="weekly",
    ):
        """Helper to create a recurrent contract with default values."""
        vals = {
            "alt_currency_id": creator_wallet.alt_currency_id.id,
            "amount": amount,
            "creator_wallet_id": creator_wallet.id,
            "sender_wallet_id": sender_wallet.id,
            "receiver_wallet_id": receiver_wallet.id,
            "date_start": date_start,
            "date_end": date_end,
            "recurring_rule_type": recurring_rule_type,
            "recurring_interval": recurring_interval,
            "message": message,
        }
        return self.RecurrentContract.create(vals)

    # -------------------------------------------------------------------------
    # Test: Contract Creation
    # -------------------------------------------------------------------------

    def test_contract_creation_generates_sequence_name(self):
        """Contract creation should auto-generate a PRC/XXXXX reference."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(wallet_1, wallet_2, wallet_1)
        self.assertTrue(contract.name.startswith("PRC/"))
        self.assertNotEqual(contract.name, "New")

    def test_contract_creation_initializes_recurring_next_date(self):
        """Contract creation should initialize recurring_next_date from date_start."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        start_date = date.today() + timedelta(days=5)
        contract = self._create_contract(wallet_1, wallet_2, wallet_1, date_start=start_date)
        self.assertEqual(contract.recurring_next_date, start_date)

    def test_contract_creation_default_state_is_draft(self):
        """Contract should be created in draft state by default."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(wallet_1, wallet_2, wallet_1)
        self.assertEqual(contract.state, "draft")

    # -------------------------------------------------------------------------
    # Test: State Transitions
    # -------------------------------------------------------------------------

    def test_action_confirm_sets_state_to_open(self):
        """action_confirm() should set the contract state to 'open'."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(wallet_1, wallet_2, wallet_1)
        contract.action_confirm()
        self.assertEqual(contract.state, "open")

    def test_action_confirm_initializes_recurring_next_date_if_missing(self):
        """action_confirm() should set recurring_next_date if not already set."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(wallet_1, wallet_2, wallet_1)
        contract.recurring_next_date = False

        contract.action_confirm()
        self.assertTrue(contract.recurring_next_date)
        self.assertEqual(contract.recurring_next_date, contract.date_start)

    def test_action_close_sets_state_to_closed(self):
        """action_close() should set the contract state to 'closed'."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(wallet_1, wallet_2, wallet_1)
        contract.action_close()
        self.assertEqual(contract.state, "closed")

    def test_action_draft_resets_state_to_draft(self):
        """action_draft() should reset the contract state to 'draft'."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(wallet_1, wallet_2, wallet_1)
        contract.action_confirm()
        contract.action_draft()
        self.assertEqual(contract.state, "draft")

    # -------------------------------------------------------------------------
    # Test: Recurring Interval Delta Calculation
    # -------------------------------------------------------------------------

    def test_get_recurring_interval_delta_daily(self):
        """_get_recurring_interval_delta() should return correct delta for daily."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            recurring_rule_type="daily",
            recurring_interval=3,
        )
        delta = contract._get_recurring_interval_delta()
        self.assertEqual(delta, relativedelta(days=3))

    def test_get_recurring_interval_delta_weekly(self):
        """_get_recurring_interval_delta() should return correct delta for weekly."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            recurring_rule_type="weekly",
            recurring_interval=2,
        )
        delta = contract._get_recurring_interval_delta()
        self.assertEqual(delta, relativedelta(weeks=2))

    def test_get_recurring_interval_delta_monthly(self):
        """_get_recurring_interval_delta() should return correct delta for monthly."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            recurring_rule_type="monthly",
            recurring_interval=1,
        )
        delta = contract._get_recurring_interval_delta()
        self.assertEqual(delta, relativedelta(months=1))

    def test_get_recurring_interval_delta_yearly(self):
        """_get_recurring_interval_delta() should return correct delta for yearly."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            recurring_rule_type="yearly",
            recurring_interval=1,
        )
        delta = contract._get_recurring_interval_delta()
        self.assertEqual(delta, relativedelta(years=1))

    # -------------------------------------------------------------------------
    # Test: Payment Request Values Preparation
    # -------------------------------------------------------------------------

    def test_prepare_payment_request_values(self):
        """_prepare_payment_request_values() should return correct values dict."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            amount=250.0,
            message="Monthly subscription",
        )
        values = contract._prepare_payment_request_values()

        self.assertEqual(values["alt_currency_id"], currency.id)
        self.assertEqual(values["amount"], 250.0)
        self.assertEqual(values["creator_wallet_id"], wallet_1.id)
        self.assertEqual(values["sender_wallet_id"], wallet_2.id)
        self.assertEqual(values["receiver_wallet_id"], wallet_1.id)
        self.assertEqual(values["message"], "Monthly subscription")
        self.assertEqual(values["recurrent_contract_id"], contract.id)

    # -------------------------------------------------------------------------
    # Test: Payment Request Creation
    # -------------------------------------------------------------------------

    def test_create_payment_request_creates_record(self):
        """_create_payment_request() should create a payment.request record."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(wallet_1, wallet_2, wallet_1)
        contract.action_confirm()

        initial_count = self.PaymentRequest.search_count([])
        payment_request = contract._create_payment_request()
        final_count = self.PaymentRequest.search_count([])

        self.assertEqual(final_count, initial_count + 1)
        self.assertEqual(payment_request.recurrent_contract_id, contract)
        self.assertEqual(payment_request.amount, contract.amount)
        self.assertEqual(payment_request.state, "open")

    def test_create_payment_request_updates_recurring_next_date(self):
        """_create_payment_request() should advance recurring_next_date."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        start_date = date.today()
        contract = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            date_start=start_date,
            recurring_rule_type="monthly",
            recurring_interval=1,
        )
        contract.action_confirm()

        self.assertEqual(contract.recurring_next_date, start_date)
        contract._create_payment_request()
        self.assertEqual(
            contract.recurring_next_date,
            start_date + relativedelta(months=1),
        )

    def test_create_payment_request_closes_contract_when_end_date_reached(self):
        """_create_payment_request() should close contract when end date is passed."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        start_date = date.today()
        # End date is less than one interval away
        end_date = start_date + timedelta(days=15)
        contract = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            date_start=start_date,
            date_end=end_date,
            recurring_rule_type="monthly",
            recurring_interval=1,
        )
        contract.action_confirm()

        # Creating payment request should advance next_date past end_date
        contract._create_payment_request()

        # Next date would be start_date + 1 month, which is > end_date
        self.assertEqual(contract.state, "closed")


    # -------------------------------------------------------------------------
    # Test: Cron Job
    # -------------------------------------------------------------------------

    def test_cron_creates_payment_requests_for_due_contracts(self):
        """Cron should create payment requests for contracts with due next_date."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")

        # Contract with next_date = today (should be processed)
        contract_due = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            date_start=date.today(),
            recurring_rule_type="monthly",
        )
        contract_due.action_confirm()

        # Contract with next_date in the future (should NOT be processed)
        contract_future = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            date_start=date.today() + timedelta(days=10),
            recurring_rule_type="monthly",
        )
        contract_future.action_confirm()

        initial_count = self.PaymentRequest.search_count([])
        self.RecurrentContract._cron_recurring_create_payment_requests()
        final_count = self.PaymentRequest.search_count([])

        # Only one payment request should be created (for contract_due)
        self.assertEqual(final_count, initial_count + 1)
        self.assertEqual(contract_due.payment_request_count, 1)
        self.assertEqual(contract_future.payment_request_count, 0)

    def test_cron_ignores_draft_contracts(self):
        """Cron should not process contracts in draft state."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            date_start=date.today()
        )

        initial_count = self.PaymentRequest.search_count([])
        self.RecurrentContract._cron_recurring_create_payment_requests()
        final_count = self.PaymentRequest.search_count([])

        self.assertEqual(final_count, initial_count)
        self.assertEqual(contract.payment_request_count, 0)

    def test_cron_ignores_closed_contracts(self):
        """Cron should not process contracts in closed state."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            date_start=date.today()
        )
        contract.action_close()

        initial_count = self.PaymentRequest.search_count([])
        self.RecurrentContract._cron_recurring_create_payment_requests()
        final_count = self.PaymentRequest.search_count([])

        self.assertEqual(final_count, initial_count)
        self.assertEqual(contract.payment_request_count, 0)

    def test_cron_ignores_contracts_past_end_date(self):
        """Cron should not process contracts whose end_date has passed."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        yesterday = date.today() - timedelta(days=1)
        contract = self._create_contract(
            wallet_1,
            wallet_2,
            wallet_1,
            date_start=yesterday - timedelta(days=30),
            date_end=yesterday,
        )
        contract.action_confirm()

        initial_count = self.PaymentRequest.search_count([])
        self.RecurrentContract._cron_recurring_create_payment_requests()
        final_count = self.PaymentRequest.search_count([])

        self.assertEqual(final_count, initial_count)

    def test_cron_processes_multiple_due_contracts(self):
        """Cron should process all due contracts in a single run."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")

        # Create 3 contracts all due today
        contracts = []
        for i in range(3):
            contract = self._create_contract(
                wallet_1,
                wallet_2,
                wallet_1,
                date_start=date.today(),
                amount=100.0 * (i + 1),
            )
            contract.action_confirm()
            contracts.append(contract)

        initial_count = self.PaymentRequest.search_count([])
        self.RecurrentContract._cron_recurring_create_payment_requests()
        final_count = self.PaymentRequest.search_count([])

        self.assertEqual(final_count, initial_count + 3)
        for contract in contracts:
            self.assertEqual(contract.payment_request_count, 1)

    # -------------------------------------------------------------------------
    # Test: Payment Request Count
    # -------------------------------------------------------------------------

    def test_payment_request_count_computed_correctly(self):
        """payment_request_count should reflect the number of linked requests."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(wallet_1, wallet_2, wallet_1)
        contract.action_confirm()
        self.assertEqual(contract.payment_request_count, 0)

        contract._create_payment_request()
        self.assertEqual(contract.payment_request_count, 1)

        contract._create_payment_request()
        self.assertEqual(contract.payment_request_count, 2)

        contract._create_payment_request()
        self.assertEqual(contract.payment_request_count, 3)

    # -------------------------------------------------------------------------
    # Test: Action View Payment Requests
    # -------------------------------------------------------------------------

    def test_action_view_payment_requests_returns_action(self):
        """action_view_payment_requests() should return a window action."""
        currency = self._create_alt_currency()
        partner = self._create_res_partner()
        wallet_1 = self._create_res_partner_backend(partner, currency, ident="12345")
        wallet_2 = self._create_res_partner_backend(partner, currency, ident="67890")
        contract = self._create_contract(wallet_1, wallet_2, wallet_1)
        contract.action_confirm()
        contract._create_payment_request()

        action = contract.action_view_payment_requests()

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "payment.request")
        self.assertIn(("recurrent_contract_id", "=", contract.id), action["domain"])
