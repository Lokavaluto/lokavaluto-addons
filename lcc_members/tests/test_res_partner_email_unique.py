from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestResPartnerEmailUnique(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.email = "duplicate@example.com"

    def _create_individual(self, email):
        return self.Partner.create(
            {"firstname": "Jean", "lastname": "DUPONT", "email": email}
        )

    def _create_company(self, email):
        return self.Partner.create(
            {"name": "Dupont SARL", "is_company": True, "email": email}
        )

    def test_individual_then_individual_same_email(self):
        self._create_individual(self.email)
        with self.assertRaises(UserError):
            self._create_individual(self.email)

    def test_company_then_company_same_email(self):
        self._create_company(self.email)
        with self.assertRaises(UserError):
            self._create_company(self.email)

    def test_individual_then_company_same_email(self):
        self._create_individual(self.email)
        with self.assertRaises(UserError):
            self._create_company(self.email)

    def test_company_then_individual_same_email(self):
        self._create_company(self.email)
        with self.assertRaises(UserError):
            self._create_individual(self.email)

    def test_write_email_already_used_by_other_kind(self):
        self._create_company(self.email)
        individual = self._create_individual("other@example.com")
        with self.assertRaises(UserError):
            individual.write({"email": self.email})

    def test_same_email_different_case(self):
        self._create_individual("Duplicate@Example.com")
        with self.assertRaises(UserError):
            self._create_company("duplicate@example.COM")

    def test_write_email_different_case(self):
        self._create_individual(self.email)
        company = self._create_company("other@example.com")
        with self.assertRaises(UserError):
            company.write({"email": self.email.upper()})

    def test_underscore_is_not_a_wildcard(self):
        self._create_individual("jean_dupont@example.com")
        self._create_company("jeanxdupont@example.com")

    def test_different_invalid_emails_allowed(self):
        self._create_individual("not-an-email")
        self._create_company("another-invalid-email")

    def test_different_emails_allowed(self):
        self._create_individual(self.email)
        self._create_company("other@example.com")

    def _create_legacy_duplicates(self, email):
        """Duplicates created before the constraint existed, bypassing the ORM"""
        individual = self._create_individual("individual@example.com")
        company = self._create_company("company@example.com")
        partners = individual | company
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_partner SET email = %s, email_normalized = %s WHERE id IN %s",
            (email, email.lower(), tuple(partners.ids)),
        )
        self.env.invalidate_all()
        return individual, company

    def test_legacy_duplicate_can_rewrite_same_email(self):
        """Forms like portal "My account" always send the email, even unchanged.

        A partner already sharing its email with another one must still be able
        to save its other fields: the duplicate is not created by this write.
        """
        individual, _company = self._create_legacy_duplicates(self.email)
        individual.write({"email": self.email, "phone": "0601020304"})

    def test_legacy_duplicate_can_rewrite_email_with_other_case(self):
        individual, _company = self._create_legacy_duplicates(self.email)
        individual.write({"email": self.email.upper()})

    def test_legacy_duplicate_cannot_switch_to_another_used_email(self):
        self._create_individual("taken@example.com")
        individual, _company = self._create_legacy_duplicates(self.email)
        with self.assertRaises(UserError):
            individual.write({"email": "taken@example.com"})

    def test_multi_write_still_checks_changed_email(self):
        individual, company = self._create_legacy_duplicates(self.email)
        other = self._create_company("other@example.com")
        with self.assertRaises(UserError):
            (individual | other).write({"email": self.email})
