import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Clean res_company table
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_activate_automatic_topup")
    cr.execute("ALTER TABLE res_company DROP COLUMN tmp_commission_product_id")
