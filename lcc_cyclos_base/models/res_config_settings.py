from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cyclos_server_url = fields.Char(
        related="company_id.cyclos_server_url",
        readonly=False,
        string="Url for cyclos serveur",
    )

    cyclos_server_login = fields.Char(
        related="company_id.cyclos_server_login",
        readonly=False,
        string="Login for cyclos server",
    )

    cyclos_server_password = fields.Char(
        related="company_id.cyclos_server_password",
        readonly=False,
        string="Password for cyclos server",
    )

    cyclos_date_last_reconversion_check = fields.Datetime(
        related="company_id.cyclos_date_last_reconversion_check",
        readonly=False,
        string="Last reconversion date on Cyclos",
    )
