odoo.define('lcc_members_website.oe_lokavaluto', function (require) {
    $(document).ready(function () {
        "use strict";
        var ajax = require('web.ajax');

        $('.oe_lokavaluto').each(function () {
            var oe_lokavaluto = this;

            $('#member_product_id').change(function () {
                var member_product_id = $("#member_product_id").val();
                ajax.jsonRpc("/subscription/get_member_product", 'call', {
                    'member_product_id': member_product_id,
                })
                    .then(function (data) {
                        $('input[name=total_membership]').val(data[member_product_id].list_price)
                        if (!data[member_product_id].dynamic_price){
                            $('input[name=total_membership]').prop('readonly', true);
                        } else {
                            $('input[name=total_membership]').prop('readonly', false);
                        }
                    });
            });

            $('#member_product_id').trigger('change');

            $("[name='birthdate']").inputmask();
        });
    });
});
