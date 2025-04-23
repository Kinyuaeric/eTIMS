import json
from datetime import datetime

from odoo import models, fields, _
import logging
from odoo.exceptions import UserError
# from .etims_connect import ETIMSConnect

_logger = logging.getLogger(__name__)

from odoo import models, fields, api


class EtimsPurchases(models.Model):
    _name = 'etims.purchases'

    spplrTin = fields.Char('Supplier TIN')
    spplrNm = fields.Char('Supplier Name')
    spplrBhfId = fields.Char('Supplier Bhf Id')
    invcNo = fields.Integer('Invoice Number')
    rcptTyCd = fields.Char('Receipt Type Code')
    pmtTyCd = fields.Char('Payment Type Code')
    cfmDt = fields.Datetime('Confirmation Date')
    salesDt = fields.Date('Sales Date')
    stockRlsDt = fields.Date('Stock Release Date')
    totItemCnt = fields.Integer('Total Item Count')
    taxblAmtA = fields.Float('Taxable Amount A')
    taxblAmtB = fields.Float('Taxable Amount B')
    taxblAmtC = fields.Float('Taxable Amount C')
    taxblAmtD = fields.Float('Taxable Amount D')
    taxRtA = fields.Float('Tax Rate A')
    taxRtB = fields.Float('Tax Rate B')
    taxRtC = fields.Float('Tax Rate C')
    taxRtD = fields.Float('Tax Rate D')
    taxAmtA = fields.Float('Tax Amount A')
    taxAmtB = fields.Float('Tax Amount B')
    taxAmtC = fields.Float('Tax Amount C')
    taxAmtD = fields.Float('Tax Amount D')
    totTaxblAmt = fields.Float('Total Taxable Amount')
    totTaxAmt = fields.Float('Total Tax Amount')
    totAmt = fields.Float('Total Amount')
    remark = fields.Char('Remark')
    is_done = fields.Boolean("Purchase Generated")

    etims_purchase_items = fields.One2many('etims.purchase.items', 'etims_purchase_id', 'ETIMS Purchase Items')

    #s setr the breadcrum  name
    def name_get(self):
        result = []
        for record in self:
            formated_name = f'{record.spplrTin} - {record.invcNo}'
            result.append((record.id, formated_name))
        return result
    
    def action_process_items(self):
        for rec in self:
            supplier_pin =rec.spplrTin
            vendor_ref = rec.invcNo
            supplier = self.env['res.partner'].search([('vat', '=', supplier_pin)], limit=1)
            if not supplier:
                supplier = self.env['res.partner'].create({
                    'name': rec.spplrNm,
                    'vat': supplier_pin,
                })
            existing_purchase = self.env['purchase.order'].search(
                [('partner_ref', '=', vendor_ref), ('partner_id', '=', supplier.id)], limit=1)
            _logger.info('====Creating Purchase')
            new_purchase = self.env['purchase.order'].with_user(2).create({
                'partner_id': supplier.id,
                # 'partner_ref': vendor_ref,
                'date_order': datetime.now(),
                'company_id': self.env.company.id,
                'amount_total': self.totAmt,
                'amount_tax': self.totTaxAmt,
                'supplier_name': self.spplrNm,
                'supplier_tin': self.spplrTin,
                'supplier_invoice': self.invcNo,
                'supplier_branch': self.spplrBhfId
            })
            for purchase_line_data in rec.etims_purchase_items:

                product = purchase_line_data.product_id

                if not purchase_line_data.is_mapping and not product:
                    account_tax = self.env['account.tax'].search(
                        [('etims_code', '=', purchase_line_data.taxTyCd)], limit=1)
                    if account_tax:
                        product.taxes_id = account_tax
                    new_product = self.env['product.product'].with_user(2).create({
                        'name': purchase_line_data.itemNm,
                        'detailed_type': 'product',
                        'list_price': purchase_line_data.prc,
                        'incoming_quantity': purchase_line_data.qty,
                        'taxes_id': account_tax
                    })
                    product= new_product
                    purchase_line_data.write({'product_id': new_product})
                else:
                    product = product
                    product.write({'incoming_quantity':purchase_line_data.qty})
                    account_tax = self.env['account.tax'].search(
                        [('etims_code', '=', purchase_line_data.taxTyCd)], limit=1)
                    if account_tax:
                        product.taxes_id = account_tax
                self.env['purchase.order.line'].with_user(2).create({
                    'product_id': product.id,
                    'product_qty': purchase_line_data.qty,
                    'price_unit': purchase_line_data.prc,
                    'order_id': new_purchase.id,
                    'etims_purchase_line_id': purchase_line_data.id,
                })

        rec.write({'is_done':True})


    def create_etims_purchase(self, api_vals):
        _logger.info('Creating ETIMS Purchase')
        for api_val in api_vals:
            etims_purchase = self.env['etims.purchases'].with_user(2).create({
                'spplrTin': api_val['spplrTin'],
                'spplrNm': api_val['spplrNm'],
                'spplrBhfId': api_val['spplrBhfId'],
                'invcNo': api_val['spplrInvcNo'],
                'rcptTyCd': api_val['rcptTyCd'],
                'pmtTyCd': api_val['pmtTyCd'],
                # 'salesDt': datetime.strptime(api_val['salesDt'], '%Y%m%d').date() if api_val['salesDt'] else False,
                # 'stockRlsDt': datetime.strptime(api_val['stockRlsDt'], '%Y-%m-%d').date() if api_val['stockRlsDt'] else False,
                # 'cfmDt': datetime.strptime(api_val['cfmDt'], '%Y-%m-%d %H:%M:%S') if api_val['cfmDt'] else False,
                'totItemCnt': api_val['totItemCnt'],
                'taxblAmtA': api_val['taxblAmtA'],
                'taxblAmtB': api_val['taxblAmtB'],
                'taxblAmtC': api_val['taxblAmtC'],
                'taxblAmtD': api_val['taxblAmtD'],
                'taxRtA': api_val['taxRtA'],
                'taxRtB': api_val['taxRtB'],
                'taxRtC': api_val['taxRtC'],
                'taxRtD': api_val['taxRtD'],
                'taxAmtA': api_val['taxAmtA'],
                'taxAmtB': api_val['taxAmtB'],
                'taxAmtC': api_val['taxAmtC'],
                'taxAmtD': api_val['taxAmtD'],
                'totTaxblAmt': api_val['totTaxblAmt'],
                'totTaxAmt': api_val['totTaxAmt'],
                'totAmt': api_val['totAmt'],
                'remark': api_val['remark']
            })
            for item in api_val['itemList']:
                etims_purchase_items = self.env['etims.purchase.items'].with_user(2).create({
                    'etims_purchase_id': etims_purchase.id,
                    'itemSeq': item['itemSeq'],
                    'itemCd': item['itemCd'],
                    'itemClsCd': item['itemClsCd'],
                    'itemNm': item['itemNm'],
                    'bcd': item['bcd'],
                    'pkgUnitCd': item['pkgUnitCd'],
                    'pkg': item['pkg'],
                    'qtyUnitCd': item['qtyUnitCd'],
                    'qty': item['qty'],
                    'prc': item['prc'],
                    'splyAmt': item['splyAmt'],
                    'dcRt': item['dcRt'],
                    'dcAmt': item['dcAmt'],
                    'taxTyCd': item['taxTyCd'],
                    'taxblAmt': item['taxblAmt'],
                    'taxAmt': item['taxAmt'],
                    'totAmt': item['totAmt']
                })
        return True


class EtimsPurchaseItems(models.Model):
    _name = 'etims.purchase.items'

    etims_purchase_id = fields.Many2one('etims.purchases', 'Etims Purchase')
    product_id = fields.Many2one('product.product', 'Product')
    itemSeq = fields.Integer('Item Sequence')
    itemCd = fields.Char('Item Code')
    is_mapping = fields.Boolean("Is Mapping")
    itemClsCd = fields.Char('Item Class Code')
    itemNm = fields.Char('Item Name')
    bcd = fields.Char('BCD')
    pkgUnitCd = fields.Char('Package Unit Code')
    pkg = fields.Float('Package')
    qtyUnitCd = fields.Char('Quantity Unit Code')
    qty = fields.Float('Quantity')
    prc = fields.Float('Price')
    splyAmt = fields.Float('Supply Amount')
    dcRt = fields.Float('Discount Rate')
    dcAmt = fields.Float('Discount Amount')
    taxTyCd = fields.Char('Tax Type Code')
    taxblAmt = fields.Float('Taxable Amount')
    taxAmt = fields.Float('Tax Amount')
    totAmt = fields.Float('Total Amount')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    etims_purchase_line_id = fields.Many2one('etims.purchase.items', 'ETIMS Purchase Line')