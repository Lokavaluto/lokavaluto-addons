![Lokavaluto logo](https://drive.lokavaluto.fr/s/fyLon3G23wMHyyx/preview)
# Lokavaluto Odoo addons

This repository gathers the Odoo add-ons developped by the french association Lokavaluto (https://lokavaluto.fr).

Lokavaluto is an associative digital commons, initiated in 2019 by several French-speaking complementary local currency associations, with the aim of offering digital tools to all projects promoting monetary or economic alternatives.

Lokavaluto's purpose is to pool human and financial resources around the IT issues faced by local currencies. The association relieves local currencies of the need for technical expertise, operational maintenance, technology watch and software development, enabling them to concentrate on their core activity: running and developing local currencies!

## Installation

- clone the current repository on your host system
- link your Odoo addons volumes with the cloned repository
- installed the add-ons throught Odoo Applications

## Configuration

Each add-on has its own configuration and guidelines, please consult the corresponding README files.

## Demo instance

A demonstration Odoo instance is available on https://demo.lokavaluto.fr.
An account needs to be created, you might need help from Lokavaluto technical teams. Do not hesitate to contact them through the website https://lokavaluto.fr

## Contribute

Feel free to open issues and propose Pull Requests!
The priorities and all the development tasks are decided by Lokavaluto's actors and developers. These last ones will provide feedbacks to your contribution to ensure it complies with Local currencies needs and normative rules.

## Continuous integration

### Global picture

Hosts are available through sftp (sftp is using ssh). The
authentication is the SSH one through a private key on the github side
(managed in github secrets) and accessible through
`secrets.sftp_private_key` in the yaml workflow definition.

All content of the workdir is sent to the hosts (ideally mirrored and
only difference should be sent), but this is not yet the case for
`lftp` limitation over using `sftp` and setting dates
correctly. `rclone` should be able to handle this better but is not
yet used. A simple git push could be studied also.

To trigger the restart of odoo on the host, we set up a inotify
watcher through `incron`.

### Host setup

#### odoo

To add `odoo` services to a compose read host, add this section to
your `compose.yml`:

```yaml
odoo:
  charm: odoo-tecnativa
  docker-compose:
    command:
      - "--dev=xml,qweb,werkzeug"
      - "--log-level=debug"
      - "--limit-time-cpu=500"
      - "--limit-time-real=500"
      - "--limit-memory-soft=25273917440"
      - "--limit-memory-hard=25273917440"
      - "--addons-path=/opt/odoo/auto/lokavaluto,/opt/odoo/auto/addons"
    volumes:
      - /srv/datastore/data/odoo/opt/odoo/auto/lokavaluto:/opt/odoo/auto/lokavaluto:rw
    image: docker.0k.io/mirror/odoo:rc_12.0-MYC-INIT-3.7
  options:
    workers: 4
    modules:
    - lcc_lokavaluto_app_connection
    - lcc_comchain_base
    - lcc_cyclos_base
  relations:
    web-proxy:
      frontend:
        domain: odoo.mydomain.org
```

Notice:

- the `--addons` path correlates with the `volumes` section.
- the `modules` section list the current modules

#### sftp

To add `sftp` services to a compose ready host, add this section to
your `compose.yml`:

```yaml
sftp:
  docker-compose:
    ports:
      - "10322:22"
    volumes:
      - /srv/datastore/data/odoo/opt/odoo/auto/lokavaluto:/home/monujo/lokavaluto-addons:rw
  options:
    users:
      monujo:
        groups:
          - monujo-rw:3000
        password: yLzTieeTwJmMlFZG
        keys:
          - "ssh-rsa AAAAB3N...PUBLICKEYGOESHERE... odoo@example.org"
```

The volumes section allows to `publish` and give access to the place
where odoo reads the module's code.

The public key is the public key part corresponding to the private key
that needs to be sent by the client (in github secrets).

Note that group `monujo-rw` is important. You should give the right of
all files that are to be modified the group `3000` from the host:

```
chown 1000:3000 /srv/datastore/data/odoo/opt/odoo/auto/lokavaluto -R
```

#### incron

Incron is the tool used for the github deployement to signal the end
of the upload of the new files. It should trigger a restart of the
odoo docker.

Directory that allows triggering the event must be created and
permissions should be set so sftp user can write in it:

```bash
mkdir -p /srv/datastore/data/sftp/home/monujo/lokavaluto-addons.updated
cd /srv/datastore/data/sftp/home/monujo/lokavaluto-addons.updated
chown 1000:3000 -R .
```

To install `incron`:

```bash
apt-get install incron
echo "root" > /etc/incron.allow
```

To edit:

```bash
EDITOR=vim incrontab -e
```

Line to create in current installation

```
/srv/datastore/data/sftp/home/monujo/lokavaluto-addons.updated  IN_CREATE,IN_MODIFY             docker restart myc_odoo_1
```

It is expected that the client will delete and add a file in folder:
`lokavaluto-addons.updated` to trigger the reload.

## Licenses

This repository is licensed under AGPL-3.0.

