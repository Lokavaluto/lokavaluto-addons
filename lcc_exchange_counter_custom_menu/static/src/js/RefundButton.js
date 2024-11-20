odoo.define('lcc_exchange_counter_custom_menu.RefundButton', function(require) {
    'use strict';

    const RefundButton = require('point_of_sale.RefundButton');
    const Registries = require("point_of_sale.Registries");
    
    const CustomRefundButton = (OriginalRefundButton) =>
        class extends OriginalRefundButton {

            showRefundButton() {               
                    return this.env.pos && this.env.pos.config && this.env.pos.get_cashier().role === 'manager';
                }
        }

    Registries.Component.extend(RefundButton, CustomRefundButton);

    return RefundButton;
});
