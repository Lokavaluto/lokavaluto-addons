odoo.define('lcc_exchange_counter_custom_menu.RefundButton', function(require) {
    'use strict';

    const RefundButton = require('point_of_sale.RefundButton');
    const ProductScreen = require('point_of_sale.ProductScreen');

    // Replace the existing RefundButton control definition with a condition
    // that shows the button only when the current cashier has role 'manager'.
    ProductScreen.addControlButton({
        component: RefundButton,
        condition: function () {
            try {
                const cashier = this.env && this.env.pos && this.env.pos.get_cashier
                    ? this.env.pos.get_cashier()
                    : null;
                if (!cashier) {
                    return false;
                }
                // exact match as requested
                return cashier.role === 'manager';
            } catch (e) {
                // be safe: hide the button on errors
                return false;
            }
        },
        // replace the original RefundButton registration (avoid duplicate)
        position: ['replace', 'RefundButton'],
    });

    // nothing else to export
    return {};
});
