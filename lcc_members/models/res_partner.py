# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
from odoo.tools.translate import _


class res_partner(models.Model):
    _inherit = "res.partner"

    reasons_choosing_mlc = fields.Text(
        string=_("Why did I choose local currency"),
        required=False,
        translate=True,
        readonly=False
    )
    instagram = fields.Char(
        string=_("Instagram"),
        required=False,
        translate=False,
        readonly=False
    )
    phone_pro = fields.Char(
        string=_("Professional phone"),
        required=False,
        translate=False,
        readonly=False
    )
    member_comment = fields.Text(
        string=_("Member comment"),
        required=False,
        translate=False,
        readonly=False
    )
    member_type_id = fields.Many2one(
        string=_("Member's type"),
        required=False,
        translate=False,
        readonly=False
    )
    convention_signature_date = fields.Date(
        string=_("convention signature date"),
        required=False,
        translate=False,
        readonly=False
    )
    to_renew = fields.Boolean(
        string=_("To renew"),
        required=False,
        translate=False,
        readonly=False
    )
    legal_activity_code = fields.Char(
        string=_("legal activity code (ex. APE in France)"),
        required=False,
        translate=False,
        readonly=False
    )
    facebook_url = fields.Char(
        string=_("URl Facebook"),
        required=False,
        translate=False,
        readonly=False
    )
    keywords = fields.Text(
        string=_("keywords"),
        required=False,
        translate=True,
        readonly=False
    )
    twitter_url = fields.Char(
        string=_("Twitter"),
        required=False,
        translate=False,
        readonly=False
    )
    opening_time = fields.Text(
        string=_("Opening Time"),
        required=False,
        translate=True,
        readonly=False
    )
    itinerant = fields.Boolean(
        string=_("Itinerant"),
        required=False,
        translate=False,
        readonly=False
    )
    detailed_activity = fields.Char(
        string=_("Detailed activity"),
        required=False,
        translate=True,
        readonly=False
    )
    is_volunteer = fields.Boolean(
        string=_("Is volunteer"),
        required=False,
        translate=False,
        readonly=False
    )
    private_comment = fields.Text(
        string=_("Private comment"),
        required=False,
        translate=False,
        readonly=False
    )
    convention_specific_agreement = fields.Text(
        string=_("Convention specific agreement"),
        required=False,
        translate=False,
        readonly=False
    )
    currency_exchange_office = fields.Boolean(
        string=_("Currency exchange office"),
        required=False,
        translate=False,
        readonly=False
    )
