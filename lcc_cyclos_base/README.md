# Cyclos Odoo


## OAuth Configuration

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