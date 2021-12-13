# Copyright 2020 Lokavaluto ()
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

from odoo.osv.expression import OR


class CustomerPortal(CustomerPortal):

    def get_domain_my_profiles(self, user):
        return [
            ('contact_id', '=', user.partner_id.id),
            ('active', '=', True)
        ]

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['profile_count'] = request.env['res.partner'].search_count(self.get_domain_my_profiles(request.env.user))
        return values

    def _profile_get_page_view_values(self, profile, access_token, **kwargs):
        values = {
            'page_name': 'profile',
            'profile': profile,
        }
        return self._get_page_view_values(profile, access_token, values, 'my_profiles_history', False, **kwargs)

    @http.route(['/my/profiles', '/my/profiles/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_profiles(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        profile = request.env['res.partner']
        domain = self.get_domain_my_profiles(request.env.user)

        searchbar_sortings = {
            'name': {'label': _('Name'), 'order': 'name'},
            'partner_profile': {'label': _('Profile Type'), 'order': 'partner_profile'},
            'parent_id': {'label': _('Company'), 'order': 'parent_id'},
        }
        if not sortby:
            sortby = 'name'
        order = searchbar_sortings[sortby]['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('res.partner', domain)

        # profiles count
        profile_count = profile.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/profiles",
            url_args={'sortby': sortby},
            total=profile_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        profiles = profile.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_profiles_history'] = profiles.ids[:100]

        values.update({
            'profiles': profiles,
            'page_name': 'profile',
            'archive_groups': archive_groups,
            'default_url': '/my/profiles',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("lcc_members.portal_my_profiles", values)

    @http.route(['/my/profile/<int:profile_id>'], type='http', auth="public", website=True)
    def portal_my_profile(self, profile_id=None, access_token=None, **kw):
        try:
            profile_sudo = self._document_check_access('res.partner', profile_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._profile_get_page_view_values(profile_sudo, access_token, **kw)
        return request.render("lcc_members.portal_my_profile", values)
        countries = request.env["res.country"].sudo().search([])
        industries = request.env["res.partner.industry"].sudo().search([])

        values.update(
            {
                "countries": countries,
                "industries": industries,
            }
        )

        return request.render("lcc_members.portal_my_profile", values)
