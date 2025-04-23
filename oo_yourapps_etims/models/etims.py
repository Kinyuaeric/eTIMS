# -*- coding: utf-8 -*-
import xmltodict

import base64
import json
import logging
from io import BytesIO

import requests
from odoo import models, fields
from odoo.exceptions import ValidationError
from odoo.tools import float_round
from qrcode import QRCode, constants

_logger = logging.getLogger(__name__)

from datetime import datetime

SUCCESS = '000'

PATHS = {
    'init': 'InitializationV2',
    'login': 'Token',
    'Addinsurance': 'AddInsuranceV2',
    'standard_codes': 'GetCodeListV2',
    'item_class': 'GetItemClassificationListV2',
    'get_branch': 'GetBranchListV2',
    'save_customer': 'AddCustomerV2',
    'save_user': 'AddBranchUserV2',
    'save_item': 'AddItemsListV2',
    'get_imports': 'selectImportPurchases',
    'save_sales': 'etims_vscu/invoices',
    'get_purchases': 'selectLocalPurchases',
    'save_purchases': 'etims_vscu/credit_notes',
    'inventory_moves': 'StockAdjustment',
    'GetNotices': 'GetNoticeListV2',
    # 'update_master_stock': 'StockMasterSaveRequestV2',
    'master_stock': 'ItemOpeningStockV2',

    


    
}

DOCUMENT_MAP = {
    'out_invoice': 'Sale',
    'out_refund': 'Credit Note',
    'in_refund': 'Credit Note',
    'in_invoice': 'Purchase',
}

STOCK_MOVE_MAP = {
    'out_invoice': 'GoodsIssue',
    'out_refund': 'GoodsReceipt',
    'in_invoice': 'GoodsReceipt',
    'in_refund': 'GoodsIssue',
}


class EtimsCore(models.AbstractModel):
    _name = 'etims.core'
    _description = 'ETIMS'

    receipt_no = fields.Char(string='Receipt No', readonly=True, copy=False)
    receipt_sign = fields.Char(string='Receipt Sign', readonly=True, copy=False)
    cu_invoice_no = fields.Char(string='CU No', readonly=True, copy=False)
    qrcode_url = fields.Char(string='QrCode Url', readonly=True, copy=False)
    sdc_id = fields.Char(string='SDC', readonly=True, copy=False)
    intr_data = fields.Char(string='INTR', readonly=True, copy=False)
    receipt_date = fields.Datetime('Receipt Date', readonly=True, copy=False)
    qrcode = fields.Binary(string='QrCode', readonly=True, copy=False)
    refund_reason_id = fields.Many2one('etims.standard.code',
                                       string='Refund Reason', 
                                       copy=False,
                                       domain=[('code_type', '=', 'refund_reason')])

    def _notify(self, title, message, type='success', sticky=False):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': type,
                'sticky': sticky,
            },
        }

    def _error_handler(self, response):
        if not response:
            raise ValidationError('ETIMS: something went wrong! Please review the logs for more details.')
        _logger.info(f'ETIMS response: {response.status_code} and message: {response.json()}')

        res = response.json()
        if response.status_code // 100 != 2:
            raise ValidationError(f"ETIMS: failure: ({res.get('status')}) ({res.get('message')})")
        return res
    
    def _call_etims(self, company, endpoint, payload, method='POST', headers=None):
        response = False
        try:
            url = (company.etims_url.endswith('/') and company.etims_url or f'{company.etims_url}/') + PATHS[endpoint]           
            headers = headers or {'Content-Type': 'application/json', 'x-struts-api-key': 'YEUnOHLlTRO3aXwZg1ANsQZLe6bY4cIC'}
            data = json.dumps(payload)# needs a new variable to hold undumped payload due to the login retry.

            _logger.info(f'ETIMS: calling url: {url} with payload: {data} and headers: {headers}')
            
            response = requests.request(method.upper(), url, headers=headers, data=data)
            _logger.error(response)
            
            # if response.status_code == 401: # try to login again
            #     self._login(company)
            #     return self._call_etims(company=company, endpoint=endpoint, payload=payload, method=method)
        except Exception as e:
            _logger.error(e, exc_info=True)
        return self._error_handler(response)
    
    def _make_signature_qrcode(self, url):
        qr = QRCode(version=1, box_size=25, border=6, error_correction=constants.ERROR_CORRECT_L)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        temp_img = BytesIO()
        img.save(temp_img, format='PNG')
        return base64.b64encode(temp_img.getvalue())

    def _remove_non_alphanumerics(self, name):
        return ''.join(filter(str.isalnum, name))
    
    def _validate_product_code(self, product):
        if not product.item_code:
            raise ValidationError(f'Please save to etims product {product.name} before continuing')
    
    def _validate_tax_mapping(self, taxes):
        if not taxes.filtered('etims_code'):
            raise ValidationError('Please add etims codes on your sales taxes')
        return taxes.filtered('etims_code')[0]
    
    def _prepare_etims_stock_moves_lines(self):
        self.ensure_one()
        lines = []
        warehouses = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)]).ids
        for line in self.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            product = line.product_id
            self._validate_product_code(product)            
            tax = self._validate_tax_mapping(line.tax_ids or product.taxes_id)
            quants = self.env['stock.quant'].sudo().search(
                [('product_id', '=', product.id), ('warehouse_id', 'in', warehouses)])
            stockbalance = sum(quants.mapped('quantity'))
            lines.append({
                'itemCode': product.item_code,
                
                'quantity': abs(line.quantity),
                'packageQuantity': 0,
                })
        return lines
    
    def _prepare_etims_stock_moves(self):
        self.ensure_one()
        return {
            'storeReleaseTypeCode': '11',
            'remark': "True",
            'mapping':"test",
            'stockItemList': self._prepare_etims_stock_moves_lines()
            }


    def save_etims_stock_moves(self):
        for rec in self:
            payload = rec._prepare_etims_stock_moves()
            rec._call_etims(company=rec.company_id, endpoint='inventory_moves', payload=payload)
       
    def _prepare_etims_invoice_lines_vals(self):
        self.ensure_one()
        lines = []
        for line in self.invoice_line_ids:
            product = line.product_id
            self._validate_product_code(product)
            tax = self._validate_tax_mapping(line.tax_ids or product.taxes_id)

            lines.append({
                    'ItemCode': product.item_code,
                    'quantity': abs(line.quantity),
                    'unitPrice': float_round(line.price_unit, precision_digits=2),
                    'TaxRate': tax.amount,
                    'taxTypeCode': tax.etims_code,
                    'discountRate': line.discount,
                    'discountAmt': float_round(line.discount * line.price_subtotal, precision_digits=2)
                })
        return lines
    
    def _invoice_values(self):
        self.ensure_one()
        company = self.company_id
        return {
            'traderInvoiceNo': self._remove_non_alphanumerics(self.name),
            'customerTin': self.partner_id.vat or '',
            'customerName': self.partner_id.name or '',
            'CustBranchId': company.etims_branchid,
            'customerMobileNo':'',
            'confirmDate': self.invoice_date.strftime('%Y%m%d%H%M%S'),
            'salesDate': self.invoice_date.strftime('%Y%m%d'),
            
            }
        


# STRUT TESTIBG>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    # def _prepare_etims_invoice_lines_vals(self):
    #     self.ensure_one()
    #     lines = []
    #     for line in self.invoice_line_ids:
    #         product = line.product_id
    #         # self._validate_product_code(product)
    #         tax = self._validate_tax_mapping(line.tax_ids or product.taxes_id)

    #         lines.append({
    #                 'item_name': product.name,
    #                 'item_qty': abs(line.quantity),
    #                 'unit_price': float_round(line.price_unit, precision_digits=2),
    #                 # 'TaxRate': tax.amount,
    #                 'tax_rate': tax.etims_code,
    #                 # 'discountRate': line.discount,
    #                 'discountAmt': 0,
    #                 'total_amount':line.price_subtotal,
    #             })
    #     return lines

    # def _invoice_values(self):
    #     self.ensure_one()
    #     company = self.company_id
    #     return {
    #         'customer_pin': self.partner_id.vat or '',
    #         'customer_name': self.partner_id.name or '',
    #         'invoice_number': 541,
    #         'total':self.amount_total_signed,
    #         'vat': self.amount_tax_signed,
            
    #         }
    
    # def _common_move_vals(self):
    #     self.ensure_one()
    #     company = self.company_id
    #     return{
        
    #         'invoice_items': self._prepare_etims_invoice_lines_vals()
    #         }
    

    # def _bill_values(self):
    #     self.ensure_one()
    #     return {
    #         'customer_pin': self.partner_id.vat or '',
    #         'customer_name': self.partner_id.name or '',
    #         'original_invoice_number': 541,
    #         'total':self.amount_total_signed * -1,
    #         'vat': self.amount_tax_signed *-1,
    #         'credit_note_number':540,  
    #         # "original_invoice_number": 111,

    #         }


# END TESTING>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>



    def _bill_values(self):
        self.ensure_one()
        return {
            # 'SystemInvoiceNo': self._remove_non_alphanumerics(self.name),
            'supplierTin': self.partner_id.vat,
            'SupplierName': self.partner_id.name,
            'SupplierInvoiceNo': self.ref or '',
            'supplierBhfId': self.company_id.etims_branchid,
            # 'supplierInvcNo':'',
            'purchDate': self.invoice_date.strftime('%Y%m%d'),
            "purchTypeCode": "N",
            'pmtTypeCode':'01',
            "purchStatusCode": "02",
            # "occurredDate": self.invoice_date.strftime('%Y%m%d')

            }
        
    def _common_move_vals(self):
        self.ensure_one()
        company = self.company_id
        return{
            'tin': company.vat,
            'BranchId': company.etims_branchid,
            'DocumentType': DOCUMENT_MAP[self.move_type],
            'PostStockMovement': 'N',
            'invoiceStatusCode':'02',
            'CurrencyCode': self.currency_id.name,
            'ExchangeRate': 1,
            'RefInvoiceNo': self.reversed_entry_id.receipt_no or 0,
            'CreditNoteReason': self.refund_reason_id.name or '',
            'CreatedBy': self.create_uid.name,
            'CreatedByName': self.create_uid.name,
            'salesType':'',
            'paymentType':'',
            'stockReleseDate':self.invoice_date.strftime('%Y%m%d%H%M%S'),
            'receiptPublishDate':self.invoice_date.strftime('%Y%m%d%H%M%S'),
            'occurredDate':self.invoice_date.strftime('%Y%m%d'),
        
            'invoice_items': self._prepare_etims_invoice_lines_vals()
            }
        
    def sign_invoice(self):
        for rec in self:
            if not rec.company_id.has_etims or not rec.company_id.etims_ok:
                raise ValidationError('This company branch has not been registered with ETIMS')
            
            if rec.move_type in ['out_invoice']:
                payload = dict(**rec._invoice_values(),**rec._common_move_vals() )
                res = rec._call_etims(company=rec.company_id, endpoint='save_sales', payload=payload)
                if res:
                    # _logger.info (">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> %s.....................................?>>>>>",res)
                    main_data = res
                    data = main_data.get('responseData', {})
                    # _logger.info (">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> %s.....................................?>>>>>",data)

                    rec.write({
                        'receipt_no': main_data['etims_total_receipt_number'],
                        'receipt_sign': main_data['etims_receipt_signature'],
                        'cu_invoice_no': main_data['etims_mrc_number'],
                        'qrcode_url': main_data['verification_url'],
                        'sdc_id': main_data['etims_sdcid'],
                        'intr_data': main_data['etims_internal_data'],
                        'receipt_date':datetime.strptime(main_data['etims_result_date_time'],"%Y%m%d%H%M%S"),
                        'qrcode': self._make_signature_qrcode(main_data['verification_url'])

                    })
            elif rec.move_type in ['out_refund']:
                payload = dict(**rec._bill_values(),**rec._common_move_vals() )
                res = rec._call_etims(company=rec.company_id, endpoint='save_purchases', payload=payload)
                if res:
                    # _logger.info (">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> %s.....................................?>>>>>",res)
                    main_data = res
                    data = main_data.get('responseData', {})
                    # _logger.info (">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> %s.....................................?>>>>>",data)

                    rec.write({
                        'receipt_no': main_data['etims_total_receipt_number'],
                        'receipt_sign': main_data['etims_receipt_signature'],
                        'cu_invoice_no': main_data['etims_mrc_number'],
                        'qrcode_url': main_data['verification_url'],
                        'sdc_id': main_data['etims_sdcid'],
                        'intr_data': main_data['etims_internal_data'],
                        'receipt_date':datetime.strptime(main_data['etims_result_date_time'],"%Y%m%d%H%M%S"),
                        'qrcode': self._make_signature_qrcode(main_data['verification_url'])

                    })
            if rec.move_type in ['in_invoice', 'in_refund']:
                payload = dict(**rec._common_move_vals(), **rec._bill_values())                
                res = rec._call_etims(company=rec.company_id, endpoint='save_purchases', payload=payload).get('data', {})
                return self._notify(title='Success', message='Bill Successfully Saved!')
            