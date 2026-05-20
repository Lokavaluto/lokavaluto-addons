"""Public REST service exposing the Monujo app configuration.

Serves ``GET /lokavaluto_api/public/config`` — the endpoint the
Monujo client calls at startup to fetch branding, theme, refresh
intervals and feature toggles. The response shape mirrors Monujo's
historical ``public/config.json``, plus three image URL fields
(``logoUrl``, ``loginLogoUrl``, ``faviconUrl``) pointing back to
Odoo's ``/web/image`` route.

Selection: the client may pass ``?ident=<value>`` to choose a
specific :class:`~odoo.addons.lcc_lokavaluto_app_connection.models.lcc_monujo_config.LccMonujoConfig`
record. When omitted, the record marked ``is_default`` is served.
"""

import logging

from odoo.exceptions import MissingError

from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class ConfigService(Component):
    _inherit = "base.rest.service"
    _name = "config.service"
    _usage = "config"
    _collection = "lokavaluto.public.services"
    _description = """
        Config Service
        Serve the Monujo client startup configuration.
    """

    @restapi.method([(["/", "/get"], "GET")], cors="*")
    def get(self, **params):
        """Return the Monujo configuration JSON.

        Args:
            **params: HTTP query string parameters. Supported key:
                ``ident`` — selects the matching
                ``lcc.monujo.config`` record. When absent, the record
                with ``is_default=True`` is returned.

        Returns:
            dict: JSON-serializable wire body (see
            :meth:`LccMonujoConfig.to_monujo_dict`).

        Raises:
            MissingError: if the requested ident matches no record,
                or if no default config exists.
        """
        ident = params.get("ident")
        Config = self.env["lcc.monujo.config"].sudo()
        if ident:
            config = Config.search([("ident", "=", ident)], limit=1)
            if not config:
                raise MissingError(
                    "No Monujo config with ident=%r" % ident
                )
        else:
            config = Config.search([("is_default", "=", True)], limit=1)
            if not config:
                raise MissingError("No default Monujo config available")

        base_url = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("web.base.url", default="")
        )
        return config.to_monujo_dict(base_url=base_url)

    def _validator_get(self):
        return {
            "ident": {"type": "string", "required": False, "nullable": True},
        }

    def _validator_return_get(self):
        # Loose schema — the wire shape is large and includes
        # dynamic theme keys; we let the model's to_monujo_dict()
        # be the source of truth.
        return {}
