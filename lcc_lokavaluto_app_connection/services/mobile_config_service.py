"""Public REST service exposing the Monujo mobile-app metadata.

Serves ``GET /lokavaluto_api/public/mobile-config/`` — distinct from
``/config`` because the consumer is different: app-store deep links,
launcher icons, and splash screens, none of which are needed by the
Monujo web client at runtime. Keeping the two endpoints separated
avoids leaking store IDs and large splash images into every web
page-load.

Selects records the same way ``/config`` does: ``?ident=<value>``
chooses an :class:`lcc.monujo.config` by its ``ident`` field, falling
back to the record marked ``is_default`` when no ident is given.
"""

import logging

from odoo.exceptions import MissingError

from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class MobileConfigService(Component):
    _inherit = "base.rest.service"
    _name = "mobile.config.service"
    _usage = "mobile-config"
    _collection = "lokavaluto.public.services"
    _description = """
        Mobile Config Service
        Serve the Monujo mobile-app metadata (icon, splash, store IDs).
    """

    @restapi.method([(["/", "/get"], "GET")], cors="*")
    def get(self, **params):
        """Return the Monujo mobile-app metadata JSON.

        Args:
            **params: HTTP query string parameters. Supported key:
                ``ident`` — selects the matching ``lcc.monujo.config``
                record. When absent, the record with ``is_default=True``
                is returned.

        Returns:
            dict: JSON-serializable wire body (see
            :meth:`LccMonujoConfig.to_mobile_dict`).

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
        return config.to_mobile_dict(base_url=base_url)

    def _validator_get(self):
        return {
            "ident": {"type": "string", "required": False, "nullable": True},
        }

    def _validator_return_get(self):
        # Loose schema — let the model's to_mobile_dict() be the
        # source of truth.
        return {}
