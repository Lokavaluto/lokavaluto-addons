from odoo.addons.component.core import Component


class WalletService(Component):
    _inherit = "base.rest.service"
    _name = "wallet.service"
    _usage = "wallet"
    _collection = "lokavaluto.private.services"
    _description = """Wallet Service — wallet management operations."""

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
