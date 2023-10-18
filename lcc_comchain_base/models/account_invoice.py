from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)



class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    comchain_amount_credited = fields.Float(
        string="Comchain amount credited", track_visibility="always", store=True
    )
    comchain_amount_to_credit = fields.Float(
        string="Comchain amount to credit", track_visibility="always", store=True
    )
    comchain_transaction_number = fields.Char('Comchain Transaction Number', track_visibility="always", store=True)

    @api.multi
    def action_invoice_paid(self):
        super(AccountInvoice, self).action_invoice_paid()
        categ = self.env.ref("lcc_comchain_base.product_category_comchain")
        for invoice in self:
            if (
                (invoice.type != "out_invoice")
                or (invoice.state != "paid")
                or not invoice.has_numeric_lcc_products
            ):
                # This invoice is not concerned by the top up process
                continue

            if invoice.comchain_amount_to_credit == 0 and invoice.comchain_amount_credited != 0:
                # Comchain top up already performed
                continue

            if invoice.comchain_amount_to_credit == 0 and invoice.comchain_amount_credited == 0:
                # No Comchain top up performed so far, check if it is needed
                amount = sum(
                    self.invoice_line_ids.filtered(
                        lambda line: line.product_id.categ_id == categ
                    ).mapped("price_subtotal")
                )
                if amount == 0:
                    # Nothing to top up
                    continue
                invoice.write(
                    {
                        "comchain_amount_to_credit": amount,
                    }
                )

            company = self.company_id
            if not company.activate_automatic_topup:
                # The top up must be validated by an comchain admin
                continue

            # Start top up process
            res = invoice.partner_id.action_comchain_credit_account(amount)

            # Transaction validated
            invoice.write(
                {
                    "comchain_amount_to_credit": 0,
                    "comchain_amount_credited": amount,
                    "comchain_transaction_number": res
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
            for invoice in invoice_ids:
                backend_account = invoice.partner_id.get_wallet("comchain")
                res.append(
                    {
                        "credit_id": invoice.id,
                        "amount": invoice.comchain_amount_to_credit,
                        "date": int(invoice.create_date.timestamp()),
                        "name": invoice.partner_id.name,
                        "monujo_backend": [
                            "comchain:%s"
                            % self.env.user.company_id.comchain_currency_name,
                            backend_account.comchain_id,
                        ],
                    }
                )
        return res

    def _get_pending_credit_requests(self, backend_keys):
        res = super(AccountInvoice, self)._get_pending_credit_requests(backend_keys)
        if all(not backend_key.startswith("comchain:") for backend_key in backend_keys):
            return []

        invoice_s = self.env["account.invoice"]
        invoice_ids = invoice_s.search(
            [
                ("partner_id", "=", self.env.user.partner_id.id),
                ("comchain_amount_to_credit", ">", 0),
                ("type", "=", "out_invoice"),
                ("state", "=", "paid"),
            ],
            order="date desc",
        )
        if invoice_ids:
            for invoice in invoice_ids:
                backend_account = invoice.partner_id.get_wallet("comchain")
                res.append(
                    {
                        "credit_id": invoice.id,
                        "amount": invoice.comchain_amount_to_credit,
                        "date": int(invoice.create_date.timestamp()),
                        "monujo_backend": [
                            "comchain:%s"
                            % self.env.user.company_id.comchain_currency_name,
                            backend_account.comchain_id,
                        ],
                        "paid": True,
                    }
                )
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
