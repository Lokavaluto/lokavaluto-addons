import logging

from psycopg2 import sql

from odoo.tools import parse_version
from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

OLD_MODEL = "res.partner.backend"
NEW_MODEL = "res.wallet"
OLD_TABLE = "res_partner_backend"
NEW_TABLE = "res_wallet"


def migrate(cr, version):
    # Older backend migrations still use the historical model/table names.
    # Upgrade to the last pre-rename release before deploying this release.
    if parse_version(version) < parse_version("16.0.1.4.0"):
        raise RuntimeError("Upgrade lcc_lokavaluto_app_connection to 16.0.1.4.0 before renaming wallets.")
    for module, minimum in (
        ("lcc_comchain_base", "16.0.1.2.0"),
        ("lcc_cyclos_base", "16.0.1.1.0"),
    ):
        cr.execute("SELECT latest_version FROM ir_module_module WHERE name = %s AND state IN ('installed', 'to upgrade')", (module,))
        row = cr.fetchone()
        if row and parse_version(row[0] or "0") < parse_version(minimum):
            raise RuntimeError("Upgrade %s to %s before renaming wallets." % (module, minimum))
    if not openupgrade.table_exists(cr, OLD_TABLE) or openupgrade.table_exists(cr, NEW_TABLE):
        raise RuntimeError("Wallet rename requires res_partner_backend and no existing res_wallet table.")
    cr.execute("SELECT 1 FROM ir_model WHERE model = %s", (NEW_MODEL,))
    if cr.fetchone():
        raise RuntimeError("A res.wallet model already exists; refusing to merge it with wallets.")

    # Keep original rows and metadata IDs until end-migrate, after all extensions load.
    cr.execute("CREATE TEMP TABLE wallet_rename_rows AS SELECT id, to_jsonb(w) - 'write_date' - 'write_uid' AS data FROM res_partner_backend w")
    cr.execute("CREATE TEMP TABLE wallet_rename_model AS SELECT id FROM ir_model WHERE model = %s", (OLD_MODEL,))
    cr.execute("CREATE TEMP TABLE wallet_rename_fields AS SELECT id, name FROM ir_model_fields WHERE model = %s", (OLD_MODEL,))
    cr.execute("CREATE TEMP TABLE wallet_rename_tags AS SELECT * FROM res_partner_backend_wallet_tag_rel")

    # Rename implicit M2M tables/columns before the ORM can create empty replacements.
    cr.execute("SELECT DISTINCT relation_table, column1, column2 FROM ir_model_fields WHERE ttype = 'many2many' AND relation_table LIKE %s", ("%res\\_partner\\_backend%",))
    for table, column1, column2 in cr.fetchall():
        new_table = table.replace(OLD_TABLE, NEW_TABLE)
        if not openupgrade.table_exists(cr, table):
            continue
        if openupgrade.table_exists(cr, new_table):
            raise RuntimeError("Wallet relation table already exists: %s" % new_table)
        openupgrade.rename_tables(cr, [(table, new_table)])
        for column in {column1, column2}:
            if column == OLD_TABLE + "_id":
                cr.execute(sql.SQL("ALTER TABLE {} RENAME COLUMN {} TO {}").format(sql.Identifier(new_table), sql.Identifier(column), sql.Identifier(NEW_TABLE + "_id")))
        cr.execute("UPDATE ir_model_fields SET relation_table = %s, column1 = replace(column1, %s, %s), column2 = replace(column2, %s, %s) WHERE relation_table = %s", (new_table, OLD_TABLE, NEW_TABLE, OLD_TABLE, NEW_TABLE, table))
        cr.execute("UPDATE ir_model_relation SET name = %s WHERE name = %s", (new_table, table))

    openupgrade.rename_models(cr, [(OLD_MODEL, NEW_MODEL)])
    openupgrade.rename_tables(cr, [(OLD_TABLE, NEW_TABLE)])

    # Include views/actions and optional installed addons' textual model references.
    # Integer model_id references already point to the preserved ir.model record.
    cr.execute("""
        SELECT table_name, column_name FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND data_type IN ('character varying', 'text')
          AND column_name IN ('model', 'res_model', 'model_name', 'relation', 'parent_res_model')
    """)
    for table, column in cr.fetchall():
        cr.execute(sql.SQL("UPDATE {} SET {} = %s WHERE {} = %s").format(sql.Identifier(table), sql.Identifier(column), sql.Identifier(column)), (NEW_MODEL, OLD_MODEL))

    # Odoo generates these XML IDs from the model name. Preserve selection IDs too.
    old_prefix = "selection__res_partner_backend__"
    new_prefix = "selection__res_wallet__"
    cr.execute("UPDATE ir_model_data SET name = %s || substring(name FROM %s) WHERE model = 'ir.model.fields.selection' AND starts_with(name, %s)", (new_prefix, len(old_prefix) + 1, old_prefix))

    # Stored custom views/expressions are not necessarily reloaded from XML.
    for table, column in (
        ("ir_ui_view", "arch_db"),
        ("ir_act_window", "domain"),
        ("ir_act_window", "context"),
        ("ir_act_server", "code"),
        ("ir_filters", "domain"),
        ("ir_filters", "context"),
        ("ir_rule", "domain_force"),
        ("ir_model_fields", "compute"),
        ("ir_model_fields", "domain"),
    ):
        cr.execute("SELECT data_type FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s", (table, column))
        row = cr.fetchone()
        if not row:
            continue
        cast = sql.SQL("::jsonb") if row[0] == "jsonb" else sql.SQL("")
        cr.execute(sql.SQL("UPDATE {table} SET {column} = replace({column}::text, %s, %s){cast} WHERE strpos({column}::text, %s) > 0").format(table=sql.Identifier(table), column=sql.Identifier(column), cast=cast), (OLD_MODEL, NEW_MODEL, OLD_MODEL))
    cr.execute("SELECT count(*) FROM res_wallet")
    _logger.info("Renamed %s wallets to res.wallet", cr.fetchone()[0])
