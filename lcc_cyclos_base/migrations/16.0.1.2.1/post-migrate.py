import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Fill the missing ``ident`` of Cyclos wallets from their ``cyclos_id``.

    Until this version, ``ident`` was only copied from ``cyclos_id`` when a
    wallet was modified, not when it was created. Wallets created since
    the 16.0.1.1.0 migration therefore have no ``ident``, and a wallet URI
    ending in ``/wallet/False``: reconversions, which are now linked to
    their wallet by URI, would not find them.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    wallets = (
        env["res.partner.backend"]
        .with_context(active_test=False)
        .search(
            [
                ("type", "=", "cyclos"),
                ("cyclos_id", "!=", False),
                ("ident", "=", False),
            ]
        )
    )
    for wallet in wallets:
        wallet.write({"ident": wallet.cyclos_id})
    _logger.info(f"Ident field filled for {len(wallets)} Cyclos wallets")
