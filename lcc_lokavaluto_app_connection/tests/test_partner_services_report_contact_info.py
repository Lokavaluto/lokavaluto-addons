from odoo.addons.component.tests.common import TransactionComponentCase


class TestPartnerServiceReportContactInfo(TransactionComponentCase):

    def setUp(self):
        super().setUp()

        self.ResUsers = self.env["res.users"]
        self.ResPartner = self.env["res.partner"]
        self.ResCompany = self.env["res.company"]
        self.Services = self.env["lokavaluto.private.services"]


    def test_report_contact_info(self):
        acme = self.ResCompany.create({"name": "Acme Corp"})

        john_rp = self.ResPartner.create({"name": "John Doe"})

        john_ru = self.ResUsers.create({
            "login": "jdoe",
            "partner_id": john_rp.id,
            "company_id": acme.id,
            "company_ids": [(6, 0, [acme.id])],
        })

        collection = self.Services.with_user(john_ru).browse(1)
        with collection.work_on("res.partner") as work:
            service = work.component(usage="partner")
            result = service.report_contact_info()
            self.assertEqual(result['user']['name'], "John Doe")
            self.assertEqual(result['issuer']['name'], "Acme Corp")
