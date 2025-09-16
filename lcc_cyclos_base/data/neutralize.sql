-- deactivate cyclos transactions
UPDATE res_company
   SET cyclos_server_password = NULL;
