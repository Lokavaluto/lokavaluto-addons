odoo.define("lcc_exchange_counter_custom_menu.PartnerListScreen", function (require) {
    "use strict";
   
    const PartnerListScreen = require("point_of_sale.PartnerListScreen");
    const Registries = require("point_of_sale.Registries");

    const PosPartnerListScreen = (OriginalPartnerListScreen) =>
        class extends OriginalPartnerListScreen {
            setup() {
                super.setup();

            }
            get partners() {
                let res;
                if (this.state.query && this.state.query.trim() !== '') {
                    res = this.env.pos.db.search_partner(this.state.query.trim());
                } else {
                    res = this.env.pos.db.get_partners_sorted(1000);
                }

                res.sort(function (a, b) { return (a.name || '').localeCompare(b.name || '') });
                // the selected partner (if any) is displayed at the top of the list
                if (this.state.selectedPartner) {
                    let indexOfSelectedPartner = res.findIndex( partner => 
                        partner.id === this.state.selectedPartner.id
                    );
                    if (indexOfSelectedPartner !== -1) {
                        res.splice(indexOfSelectedPartner, 1);
                    }
                    res.unshift(this.state.selectedPartner);
                }

                console.log(res);
                //return res.filter(partner => partner.id === 21);
                //return res.filter(partner => partner.is_main_profile === true);
                return res
            }
        };

    Registries.Component.extend(PartnerListScreen, PosPartnerListScreen);
    return PartnerListScreen;
});