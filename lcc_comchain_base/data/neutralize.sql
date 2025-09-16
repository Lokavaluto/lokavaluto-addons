-- deactivate comchain transactions
UPDATE res_company
   SET comchain_odoo_wallet_password = NULL;
