import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    checks = (
        ("wallet data", "SELECT 1 FROM wallet_rename_rows b FULL JOIN res_wallet w ON w.id = b.id WHERE b.data IS DISTINCT FROM (to_jsonb(w) - 'write_date' - 'write_uid') LIMIT 1"),
        ("model identity", "SELECT 1 FROM wallet_rename_model b FULL JOIN (SELECT id FROM ir_model WHERE model = 'res.wallet') m USING (id) WHERE b.id IS NULL OR m.id IS NULL"),
        ("field identities", "SELECT 1 FROM wallet_rename_fields b LEFT JOIN ir_model_fields f ON f.id = b.id AND f.model = 'res.wallet' AND f.name = b.name WHERE f.id IS NULL LIMIT 1"),
        ("wallet tags", "SELECT 1 FROM ((SELECT res_partner_backend_id, wallet_tag_id FROM wallet_rename_tags EXCEPT SELECT res_wallet_id, wallet_tag_id FROM res_wallet_wallet_tag_rel) UNION ALL (SELECT res_wallet_id, wallet_tag_id FROM res_wallet_wallet_tag_rel EXCEPT SELECT res_partner_backend_id, wallet_tag_id FROM wallet_rename_tags)) diff LIMIT 1"),
        ("old model metadata", "SELECT 1 FROM ir_model WHERE model = 'res.partner.backend' UNION ALL SELECT 1 FROM ir_model_fields WHERE model = 'res.partner.backend' OR relation = 'res.partner.backend' LIMIT 1"),
    )
    for label, query in checks:
        cr.execute(query)
        if cr.fetchone():
            raise RuntimeError("Wallet rename failed preservation check: %s" % label)
    cr.execute("DROP TABLE wallet_rename_rows, wallet_rename_model, wallet_rename_fields, wallet_rename_tags")
    _logger.info("Wallet rename verified: rows, model/field identities and tags preserved")
