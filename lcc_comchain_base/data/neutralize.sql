-- deactivate comchain transactions
UPDATE res_partner_backend
   SET comchain_wallet_pwd = NULL;
