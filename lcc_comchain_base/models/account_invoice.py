from unicodedata import name
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    comchain_amount_credited = fields.Float(
        string="Comchain amount credited", track_visibility="always"
    )
    comchain_amount_to_credit = fields.Float(
        string="Comchain amount to credit", track_visibility="always"
    )

    @api.multi
    def action_invoice_paid(self):
        super(AccountInvoice, self).action_invoice_paid()
        categ = self.env.ref("lcc_comchain_base.product_category_comchain")
        for invoice in self:
            if (
                (invoice.type == "out_invoice")
                and (invoice.state == "paid")
                and invoice.has_numeric_lcc_products
            ):
                amount = sum(
                    self.invoice_line_ids.filtered(
                        lambda line: line.product_id.categ_id == categ
                    ).mapped("price_subtotal")
                )
                invoice.write(
                    {
                        "comchain_amount_to_credit": amount,
                    }
                )

    def _get_credit_requests(self, backend_keys):
        res = super(AccountInvoice, self)._get_credit_requests(backend_keys)
        invoice_s = self.env["account.invoice"].sudo()
        invoice_ids = invoice_s.search(
            [
                ("comchain_amount_to_credit", ">", 0),
                ("type", "=", "out_invoice"),
                ("state", "=", "paid"),
            ]
        )
        if invoice_ids:
            comchainCreditRequest = self.env.datamodels["comchain.credit.request"]
            for invoice in invoice_ids:
                backend_account = invoice.partner_id._comchain_backend()
                if len(backend_account) == 0:
                    raise Exception(
                        "No backend account found for user %r" % invoice.partner_id
                    )
                if len(backend_account) > 1:
                    raise NotImplementedError(
                        "More than one comchain backend account is not yet supported"
                    )
                comchain_response = comchainCreditRequest(
                    credit_id=invoice.id,
                    amount=invoice.comchain_amount_to_credit,
                    date="%s" % invoice.date_invoice,
                    name=invoice.partner_id.name,
                    monujo_backend=[
                        "comchain:%s" % self.env.user.company_id.comchain_currency_name,
                        backend_account.comchain_id,
                    ],
                )
                res.append(comchain_response)
        return res

    def _validate_credit_request(self, invoice_ids):
        res = super(AccountInvoice, self)._get_credit_requests(invoice_ids)
        invoice_s = self.env["account.invoice"].sudo()
        invoice_ids = invoice_s.search(
            [
                ("comchain_amount_to_credit", ">", 0),
                ("type", "=", "out_invoice"),
                ("id", "in", invoice_ids),
            ]
        )
        for invoice in invoice_ids:
            invoice.write(
                {
                    "comchain_amount_to_credit": 0,
                    "comchain_amount_credited": invoice.comchain_amount_to_credit,
                }
            )
        return res
