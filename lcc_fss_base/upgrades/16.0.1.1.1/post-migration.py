import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("UPDATE res_partner SET arrival_year_territory = EXTRACT(YEAR FROM arrival_date_territory) WHERE arrival_date_territory IS NOT NULL;")
    _logger.info("Updated %s partners", cr.rowcount)
