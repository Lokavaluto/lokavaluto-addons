# lcc_comchain_base

Base models and logics using comchain as transaction provider for numeric local complementary currency
It's part of Lokavaluto Project (https://lokavaluto.fr)

## Installation

Just install lcc_comchain_base, all dependencies
will be installed by default.

TODO: Configuration -> ...

## Known issues / Roadmap

## Credit request reconciliation

The module implements the on-chain lookup used to reconcile uncertain credit
requests. When a topup send was interrupted, the hourly cron
`Alt Currency: reconcile uncertain credit requests` matches pending requests
against the Odoo wallet transaction history (recipient, amount and status)
and either confirms them, retries them, or flags them for manual review.


## Bug Tracker

Bugs are tracked on `GitHub Issues
<https://github.com/Lokavaluto/lokavaluto-addons/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

## Credits


### Images

* Lokavaluto: `Icon <https://lokavaluto.fr/web/image/res.company/1/logo?unique=f3db262>`_.

### Contributors

* Stéphan SAINLEGER <https://github.com/stephansainleger>
* Nicolas JEUDY <https://github.com/njeudy>
* Lokavaluto Teams

### Funders

The development of this module has been financially supported by:

* Lokavaluto (https://lokavaluto.fr)
* Mycéliandre (https://myceliandre.fr)
* Elabore (https://elabore.coop)

### Maintainer

This module is maintained by LOKAVALUTO.

LOKAVALUTO, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and ecosystem for local complementary currency organizations.