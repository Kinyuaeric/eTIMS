odoo.define('oo_interswitch_etims.OrderReceipt', function (require) {
    "use strict";

    const Registries = require("point_of_sale.Registries");
    const OrderReceipt = require('point_of_sale.OrderReceipt')

    const OrderReceiptEsd = OrderReceipt =>
        class extends OrderReceipt {
            get receipt() {
                let res = super.receipt;
                let order = this.env.pos.get_order()
                console.log('order :', order);

                res.receipt_no = order.receipt_no;
                res.receipt_sign = order.receipt_sign;
                res.cu_invoice_no = order.cu_invoice_no;
                res.sdc_id = order.sdc_id;
                res.intr_data = order.intr_data;
                res.receipt_date = order.receipt_date;
                res.qrcode = order.qrcode;
                console.log('res :', res);

                return res
            }
        }
    Registries.Component.extend(OrderReceipt, OrderReceiptEsd)
})