# from . import controllers
from . import models
from . import services
from . import datamodel

import logging

odoo_logger = logging.getLogger('odoo')
odoo_logger_level = odoo_logger.getEffectiveLevel()

pyc3l_logger = logging.getLogger('pyc3l')
pyc3l_logger.setLevel(odoo_logger_level)

