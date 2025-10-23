import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Save global currency config
    ## Add tmp columns
    cr.execute("ALTER TABLE res_company ADD tmp_activate_automatic_topup bool")
    cr.execute("ALTER TABLE res_company ADD tmp_commission_product_id int")

    ## Copy data to be kept during the migration
    cr.execute(
        "UPDATE res_company SET tmp_activate_automatic_topup = activate_automatic_topup"
    )
    cr.execute(
        "UPDATE res_company SET tmp_commission_product_id = commission_product_id"
    )
