Wallet model rename validation
==============================

Restore a backup into a disposable database and restore its filestore under the
same database name. Disable cron workers and HTTP, and isolate external services.
The database must first be upgraded with the last pre-rename code: core module
16.0.1.4.0, Comchain >= 16.0.1.2.0 and Cyclos >= 16.0.1.1.0 when installed.
Historical migration files deliberately keep their original names and behavior.

The migration uses openupgradelib, declared as a Python external dependency.
It renames the model, SQL table, generated metadata IDs and implicit M2M storage.
Public keys such as monujo_backends and rpb, wallet URIs and lcc_backend_ids stay
unchanged. RPC callers using res.partner.backend must switch to res.wallet.

Run wallet_rename.py through Odoo shell with the OLD code to create fixtures and
save a baseline. Set WALLET_RENAME_TEST_DB to the disposable database name,
WALLET_RENAME_BASELINE to a writable JSON path, and WALLET_RENAME_PHASE=prepare::

    odoo shell -d TEST_DB --no-http --max-cron-threads=0 < wallet_rename.py

Switch to the NEW code and upgrade all installed affected modules together::

    odoo -d TEST_DB --no-http --max-cron-threads=0 --stop-after-init \
        -u lcc_lokavaluto_app_connection,lcc_comchain_base,lcc_cyclos_base,lcc_credit_requests_from_contracts

Include lcc_wallet_qr in -u if installed. Then run the shell script again with
WALLET_RENAME_PHASE=verify and the new code. The verifier checks exact wallet
business rows (excluding write_date/write_uid refreshed by XML reloads), IDs, incoming foreign-key rows, tags, chatter, attachments, model/field and
selection XML IDs, saved filters, actions and creation using the renamed sequence.
Its final rollback removes the temporary wallet used to check creation.

For every migration revision, restore a fresh copy before preparing fixtures.
Also test a fresh installation and the existing wallet/API tests. Tests involving
financial backends must mock external API calls. The live development database
must not be used as the migration test database.

Set ODOO_RC to the test configuration before invoking Odoo shell so addon discovery
uses the correct source paths from the start. Do not rely only on --addons-path
when another configured path contains older copies of these modules.
