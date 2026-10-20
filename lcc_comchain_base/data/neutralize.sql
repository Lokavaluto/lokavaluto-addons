-- deactivate comchain transactions
UPDATE res_wallet
   SET comchain_wallet_pwd = NULL;
