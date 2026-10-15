"""Execute with Odoo shell on a disposable database; see README.rst."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path

from psycopg2 import sql

# Odoo shell supplies env. Require an explicit disposable database opt-in.
assert os.environ["WALLET_RENAME_TEST_DB"] == env.cr.dbname
phase = os.environ["WALLET_RENAME_PHASE"]
path = Path(os.environ["WALLET_RENAME_BASELINE"])
old = "res.partner.backend"
new = "res.wallet"


def digest(rows):
    values = sorted(json.dumps(row, sort_keys=True, default=str) for row in rows)
    return hashlib.sha256("\n".join(values).encode()).hexdigest()


def snapshot(model, table):
    cr = env.cr
    cr.execute(sql.SQL("SELECT to_jsonb(w) - 'write_date' - 'write_uid' FROM {} w ORDER BY id").format(sql.Identifier(table)))
    wallets = [row[0] for row in cr.fetchall()]
    model_id = env["ir.model"]._get_id(model)
    cr.execute("SELECT id, name FROM ir_model_fields WHERE model = %s ORDER BY id", (model,))
    fields = cr.fetchall()
    cr.execute("SELECT module, name, res_id, model FROM ir_model_data WHERE model IN ('ir.model', 'ir.model.fields', 'ir.model.fields.selection') AND (name = %s OR starts_with(name, %s) OR starts_with(name, %s)) ORDER BY module, name", ("model_" + table, "field_" + table + "__", "selection__" + table + "__"))
    xmlids = [(module, name.replace("res_partner_backend", "res_wallet"), rid, target) for module, name, rid, target in cr.fetchall()]
    cr.execute("""
        SELECT c.conrelid::regclass::text, a.attname
        FROM pg_constraint c JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
        WHERE c.contype = 'f' AND c.confrelid = %s::regclass AND array_length(c.conkey, 1) = 1
        ORDER BY 1, 2
    """, (table,))
    relations = {}
    for target, column in cr.fetchall():
        cr.execute(sql.SQL("SELECT to_jsonb(t) FROM {} t WHERE {} IS NOT NULL").format(sql.Identifier(target), sql.Identifier(column)))
        rows = [{k.replace("res_partner_backend", "res_wallet"): v for k, v in row[0].items()} for row in cr.fetchall()]
        relations[target.replace("res_partner_backend", "res_wallet") + "." + column.replace("res_partner_backend", "res_wallet")] = digest(rows)
    references = {}
    for target, column in (("mail_message", "model"), ("mail_followers", "res_model"), ("mail_activity", "res_model"), ("ir_attachment", "res_model")):
        cr.execute(sql.SQL("SELECT to_jsonb(t) - %s FROM {} t WHERE {} = %s").format(sql.Identifier(target), sql.Identifier(column)), (column, model))
        references[target] = digest([row[0] for row in cr.fetchall()])
    return {"wallets": digest(wallets), "wallet_ids": [w["id"] for w in wallets], "model_id": model_id, "fields": fields, "xmlids": xmlids, "relations": relations, "references": references}


if phase == "prepare":
    wallet = env[old].search([("alt_currency_id", "!=", False)], limit=1)
    assert wallet
    tag = env["wallet.tag"].create({"name": "Wallet rename preservation fixture"})
    wallet.tag_ids |= tag
    message = env["mail.message"].create({"model": old, "res_id": wallet.id, "body": "Wallet rename history fixture", "message_type": "comment"})
    attachment = env["ir.attachment"].create({"name": "wallet-rename.txt", "res_model": old, "res_id": wallet.id, "datas": base64.b64encode(b"wallet rename attachment")})
    follower = env["mail.followers"].search([("res_model", "=", old), ("res_id", "=", wallet.id), ("partner_id", "=", env.user.partner_id.id)], limit=1)
    if not follower:
        follower = env["mail.followers"].create({"res_model": old, "res_id": wallet.id, "partner_id": env.user.partner_id.id})
    activity = env["mail.activity"].create({"res_model_id": env["ir.model"]._get_id(old), "res_id": wallet.id, "activity_type_id": env.ref("mail.mail_activity_data_todo").id, "user_id": env.user.id, "summary": "Wallet rename activity fixture"})
    saved_filter = env["ir.filters"].create({"name": "Wallet rename filter", "model_id": old, "domain": "[]", "context": "{'model': 'res.partner.backend'}"})
    action = env["ir.actions.act_window"].create({"name": "Wallet rename action", "res_model": old, "view_mode": "tree,form"})
    server_action = env["ir.actions.server"].create({"name": "Wallet rename server action", "model_id": env["ir.model"]._get_id(old), "state": "code", "code": "env['res.partner.backend'].browse([])"})
    env.flush_all()
    data = snapshot(old, "res_partner_backend")
    data["fixture"] = {"wallet": wallet.id, "tag": tag.id, "message": message.id, "attachment": attachment.id, "activity": activity.id, "follower": follower.id, "filter": saved_filter.id, "action": action.id, "server_action": server_action.id}
    path.write_text(json.dumps(data, indent=2, default=str))
    env.cr.commit()
    print("Wallet migration baseline prepared:", len(data["wallet_ids"]), "wallets")
elif phase == "verify":
    before = json.loads(path.read_text())
    after = json.loads(json.dumps(snapshot(new, "res_wallet"), default=str))
    for key in after:
        assert before[key] == after[key], "Preservation failed: " + key
    fixture = before["fixture"]
    assert old not in env.registry
    wallet = env[new].with_context(active_test=False).browse(fixture["wallet"])
    assert fixture["tag"] in wallet.tag_ids.ids
    assert base64.b64decode(env["ir.attachment"].browse(fixture["attachment"]).datas) == b"wallet rename attachment"
    assert env["ir.filters"].browse(fixture["filter"]).model_id == new
    assert new in env["ir.filters"].browse(fixture["filter"]).context
    assert env["ir.actions.act_window"].browse(fixture["action"]).res_model == new
    assert new in env["ir.actions.server"].browse(fixture["server_action"]).code
    for model, field in (("credit.request", "wallet_id"), ("debit.request", "wallet_id"), ("payment.request", "sender_wallet_id"), ("payment.request.recurrent.contract", "receiver_wallet_id"), ("res.partner", "lcc_backend_ids")):
        assert env[model]._fields[field].comodel_name == new
    # Unsupported upgrades and accidental reruns must fail before changing data.
    from odoo.addons import lcc_lokavaluto_app_connection

    migration_path = Path(lcc_lokavaluto_app_connection.__file__).parent / "migrations" / "16.0.1.5.0" / "pre-migrate.py"
    spec = importlib.util.spec_from_file_location("wallet_rename_pre", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    for version, message in (("16.0.1.3.0", "Upgrade lcc_lokavaluto_app_connection"), ("16.0.1.4.0", "Wallet rename requires")):
        try:
            migration.migrate(env.cr, version)
        except RuntimeError as error:
            assert message in str(error)
        else:
            raise AssertionError("Unsafe migration state was accepted")
    # The renamed sequence must still permit allocating a new ID.
    copy = wallet.copy({"name": "Wallet rename creation check", "ident": "rename-creation-check"})
    assert copy.id > max(before["wallet_ids"])
    env.cr.rollback()
    print("PASS: wallet rows, IDs, foreign keys, tags, history, attachments, metadata and creation")
else:
    raise ValueError("Unknown WALLET_RENAME_PHASE")
