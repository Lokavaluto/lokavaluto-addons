from odoo.exceptions import MissingError

from odoo.addons.component.core import Component


class LccApiService(Component):
    """Shared base for services using ``@lcc_api`` header-based auth.

    Provides ``_auth_user_uri`` and ``_get_caller_currency`` hooks
    that backends override once — all inheriting services (wallet,
    recipient, etc.) get comchain/cyclos auth automatically.
    """

    _inherit = "base.rest.service"
    _name = "lcc.api.service"
    _collection = "lokavaluto.private.services"

    def _auth_user_uri(self, user_uri):
        """Authenticate caller from user URI. Override in backends.

        Called by the @lcc_api decorator to check if the caller has
        access to the entrypoint.

        Each backend overrides this to resolve the caller's wallet
        from the user URI, verify ownership, store whatever it needs
        on ``self.env``, and return the caller's authorized actions.

        Args:
            user_uri: value of the ``X-Lokapi-Caller-User-Uri`` header.

        Returns:
            list: authorized action strings. Empty in base.

        """
        return []

    def _get_caller_currency(self):
        """Return the currency of the authenticated caller.

        Override in backend add-ons.  Called after ``_auth_user_uri``
        has stored the caller wallet on ``self.env``.

        Returns:
            Single ``res.alt.currency`` record.

        Raises:
            odoo.exceptions.MissingError: always in base (no
                backend configured).
        """
        raise MissingError("No backend configured to identify caller currency")
