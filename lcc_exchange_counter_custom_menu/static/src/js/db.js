odoo.define('lcc_point_of_sale.db', function (require) {
    "use strict";

    var PosDB = require('point_of_sale.DB');
    var utils = require('web.utils');

    // Overide _product_search_string, search_product_in_category to allow searching product with accents
    PosDB.include({
        add_partners: function(partners){
            var updated = {};
            var new_write_date = '';
            var partner;

            for (var i = 0, len = partners.length; i < len; i++) {
                partner = partners[i];

                //TODO partner_by_id ne retourne rien...
                if (this.partner_by_id[partner.id]){
                    console.log("TOTO")
                    console.log(this.partner_by_id[partner.id])
                    partner.is_main_profile = this.partner_by_id[partner.id].is_main_profile;
                }

                var local_partner_date = (this.partner_write_date || '').replace(/^(\d{4}-\d{2}-\d{2}) ((\d{2}:?){3})$/, '$1T$2Z');
                var dist_partner_date = (partner.write_date || '').replace(/^(\d{4}-\d{2}-\d{2}) ((\d{2}:?){3})$/, '$1T$2Z');
                if (this.partner_write_date &&
                    this.partner_by_id[partner.id] &&
                    new Date(local_partner_date).getTime() + 1000 >=
                    new Date(dist_partner_date).getTime()) {
                    continue;
                } else if (new_write_date < partner.write_date) {
                    new_write_date = partner.write_date;
                }
                if (!this.partner_by_id[partner.id]) {
                    this.partner_sorted.push(partner.id);
                } else {
                    const oldPartner = this.partner_by_id[partner.id];
                    if (oldPartner.barcode) {
                        delete this.partner_by_barcode[oldPartner.barcode];
                    }
                }
                if (partner.barcode) {
                    this.partner_by_barcode[partner.barcode] = partner;
                }
                updated[partner.id] = partner;
                this.partner_by_id[partner.id] = partner;
            }
    
            this.partner_write_date = new_write_date || this.partner_write_date;
    
            const updatedChunks = new Set();
            const CHUNK_SIZE = 100;
            for (const id in updated) {
                const chunkId = Math.floor(id / CHUNK_SIZE);
                if (updatedChunks.has(chunkId)) {
                    continue;
                }
                updatedChunks.add(chunkId);
    
                let searchString = "";
                for (let id = chunkId * CHUNK_SIZE; id < (chunkId + 1) * CHUNK_SIZE; id++) {
                    if (!(id in this.partner_by_id)) {
                        continue;
                    }
                    const partner = this.partner_by_id[id];
                    partner.address = (partner.street ? partner.street + ', ' : '') +
                                      (partner.zip ? partner.zip + ', ' : '') +
                                      (partner.city ? partner.city + ', ' : '') +
                                      (partner.state_id ? partner.state_id[1] + ', ' : '') +
                                      (partner.country_id ? partner.country_id[1] : '');
                    searchString += this._partner_search_string(partner);
                }
    
                this.partner_search_strings[chunkId] = utils.unaccent(searchString);
            }
            return Object.keys(updated).length;
        },
    });

});