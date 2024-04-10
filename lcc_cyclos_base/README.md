# lcc_cyclos_base


Base models and logics using cyclos as transaction provider for numeric local complementary currency
It's part of Lokavaluto Project (https://lokavaluto.fr)

## Installation


Just install lcc_cyclos_base, all dependencies
will be installed by default.

## Configuration 

### Link with Cyclos instance

Define the Cyclos instance to which Odoo must connect in ``Settings/Digital Currency``

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
- scope: "openid profile" (space separated)
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


