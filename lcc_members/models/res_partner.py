# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models, fields, api
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


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
        'member_type',
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
    
    discount = fields.Html(
        string="Discount",
        translate="True",
    )
    
    partner_image_ids = fields.One2many(
        'partner.image',
        'partner_id',
        string='Images')

    @api.onchange('firstname', 'lastname', 'is_company')
    def onchange_upper_name(self):
        if (not self.is_company) and self.lastname and self.lastname != self.lastname.upper():
            self.lastname = self.lastname.upper()
        if (not self.is_company) and self.firstname and self.firstname != self.firstname.capitalize():
            self.firstname = self.firstname.capitalize()
            
    def _membership_state(self):
        res = super(res_partner, self)._membership_state()
        today = fields.Date.today()
        for partner in self:
            s = 4
            if partner.member_lines:
                for mline in partner.member_lines.sorted(key=lambda r: r.id):
                    if (mline.date_to) >= today and (mline.date_from) <= today:
                        if mline.account_invoice_line.invoice_id.partner_id == partner:
                            mstate = mline.account_invoice_line.invoice_id.state
                            if mstate == 'paid':
                                inv = mline.account_invoice_line.invoice_id
                                if not inv.payment_move_line_ids:
                                    partner.free_member = 1
                                else:
                                    partner.free_member = 0

            if partner.free_member and s != 0:
                res[partner.id] = 'free'
                
        return res


class PartnerImage(models.Model):
    _name = 'partner.image'
    _description = 'Partner Image'

    name = fields.Char('Name')
    image = fields.Binary('Image', attachment=True)
    partner_id = fields.Many2one('res.partner', 'Related Partner', copy=True)