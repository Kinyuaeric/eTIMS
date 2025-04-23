odoo.define('oo_interswitch_etims.PaymentScreen', function (require) {
    'use strict';

    const Registries = require("point_of_sale.Registries");
    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const rpc = require("web.rpc");

    const PaymentScreenExtend = PaymentScreen => class extends PaymentScreen {

        async _finalizeValidation() {
            await super._finalizeValidation(...arguments);
            await this.etims_sign_receipt();
        }

        async etims_sign_receipt() {
            const self = this
            console.log('self.env.pos.company :', self.env.pos.company);
            if (self.env.pos.company.has_etims) {
                const order = self.env.pos.get_order();

                await rpc.query({
                    model: "pos.order",
                    method: "etims_receipt_payload",
                    args: [order.name],
                }).then(function (res) {
                    console.log('res :', res);
                    order.receipt_no = res.receipt_no;
                    order.receipt_sign = res.receipt_sign;
                    order.cu_invoice_no = res.cu_invoice_no;
                    order.sdc_id = res.sdc_id;
                    order.intr_data = res.intr_data;
                    order.receipt_date = res.receipt_date;
                    order.qrcode = res.qrcode;
                });
            }
        }
    }


    Registries.Component.extend(PaymentScreen, PaymentScreenExtend);
});
