# lcc_cyclos_base


Base models and logics using cyclos as transaction provider for numeric local complementary currency
It's part of Lokavaluto Project (https://lokavaluto.fr)

## Installation


Just install lcc_cyclos_base, all dependencies
will be installed by default.

## Configuration 

### Link with Cyclos instance

Define the Cyclos instance to which Odoo must connect in ``Settings/Digital Currency``

Odoo authenticates on the Cyclos REST API with the configured login and
password. Cyclos looks the login up with the default user identification
method of its ``webServices`` channel (``GET /api/auth/data-for-login``
shows it as ``defaultPrincipalType``). If the configured login is of
another kind, set ``Login type for cyclos server`` to the internal name of
that identification method (for instance ``username``): Odoo then sends it
in the ``Principal-Type`` header of every request.

A wrong login type makes Cyclos answer ``401`` with code ``login``, and
Cyclos blocks the IP address of the Odoo server for a while after a few
such failures (code ``remoteAddressBlocked``).

The internal names of the Cyclos objects Odoo uses depend on how the
Cyclos instance was configured. Set them on the currency (the defaults
match the Lokavaluto Cyclos configuration):

- ``Cyclos payment type to credit a user wallet`` / ``... a company
  wallet``: payment types used to credit wallets, as
  ``<system account type>.<transfer type>`` (defaults ``debit.toUser``
  and ``debit.toPro``; ``GET /api/system/payments/data-for-perform``
  lists the available ones).
- ``Cyclos reconversion account type``: system account type receiving
  the reconversion payments (default ``debit``; ``GET
  /api/system/accounts`` lists the system account types).
- ``Cyclos password type of wallets``: password type set when Odoo
  forces the password of a wallet user (default
  ``-4307382460900696903``; the internal name, e.g. ``login``, also
  works).
- ``Cyclos group of person wallets`` / ``... company wallets``: groups
  in which Odoo creates the Cyclos user of a new wallet (defaults
  ``particuliers`` and ``professionnels``; ``GET
  /api/users/groups-for-registration`` lists the available ones).

### OAuth Configuration

Source: [Cyclos OAuth wiki page](https://wiki.cyclos.org/index.php/OpenID_Connect_-_OAuth2)

All url should be with `https://` in front.

Follow instruction to:

- Enable channel as a valid way to users to authenticate
- Create a client configuration (Users / OAuth Client)

  - name: as you want, no real use.
  - Client id: can choose anything
  - Permissions OpenID Connect, Basic profile information
  - Read e-mail address
  - return url: (probably don't need all of them)

    ```
    https://${ODOO_URL}/my/home
    https://${ODOO_URL}/auth_oauth/signin
    https://${ODOO_URL}/my/web
    ```

In _odoo_: General Settings, search for 'OAuth providers'. Create one with:

- Same client-id then the one used in Cyclos
- scope: "openid profile email" (space separated). The ``email`` scope is
  required: Cyclos only returns the user e-mail in the ``userinfo``
  response when it is requested. Odoo uses that e-mail to reconcile the
  login with an existing ``res.users`` (or create a new one) and to create
  the ``res.partner.backend``.
- auth: ``${CYCLOS_URL}/api/oidc/authorize``
- validation: ``${CYCLOS_URL}/api/oidc/token``
- data: ``${CYCLOS_URL}/api/oidc/userinfo``

Only the client id will be used

Note: You must install `lcc_cyclos_base` module that corrects OAuth
implementation in odoo.



## Known issues / Roadmap


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
-------

The development of this module has been financially supported by:

* Lokavaluto (https://lokavaluto.fr)
* Mycéliandre (https://myceliandre.fr)
* Elabore (https://elabore.coop)

### Maintainer
----------

This module is maintained by LOKAVALUTO.

LOKAVALUTO, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and ecosystem for local complementary currency organizations.


