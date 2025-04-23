# -*- coding: utf-8 -*-

from odoo import models, api
    
    
class PosOrder(models.Model):
    _name = "pos.order"
    _inherit = ['pos.order', 'etims.core']
    
    @property
    def invoice_line_ids(self):
        return self.lines

    @property
    def move_type(self):
        return self.refunded_order_ids and 'out_refund' or 'out_invoice'

    @property
    def invoice_date(self):
        return self.date_order
    
    @property
    def reversed_entry_id(self):
        return self.refunded_order_ids and self.refunded_order_ids[0] or self
    
    def etims_save(self):
        self.sign_invoice()

    @api.model
    def etims_receipt_payload(self, ref):
        order = self.env['pos.order'].search([('pos_reference', '=', ref)], limit=1)
        order.sign_invoice()
        order.save_etims_stock_moves()
        
        payload = {
            'receipt_no': order.receipt_no,
            'receipt_sign': order.receipt_sign,
            'cu_invoice_no': order.cu_invoice_no,
            'qrcode_url': order.qrcode_url,
            'sdc_id': order.sdc_id,
            'intr_data': order.intr_data,
            'receipt_date': order.receipt_date,
            'qrcode': order.qrcode,
        }
        return payload


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"
    
    @property
    def tax_ids(self):
        return self.tax_ids_after_fiscal_position
    
    @property
    def quantity(self):
        return self.qty
    
    
class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_res_company(self):
        res = super()._loader_params_res_company()
        res['search_params']['fields'].append('has_etims')
        return res