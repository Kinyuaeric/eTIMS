# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import ValidationError
import time

STANDARD_CODE_MAP = {
    'Refund Reason': 'refund_reason',
    'Bank': 'bank',
    'Locale': 'locale',
}

DATE_FORMAT = 'YmdH%M%S'

import logging

_logger = logging.getLogger(__name__)


class EtimsCodes(models.AbstractModel):
    _name = 'etims.code'
    
    code_type = fields.Selection(
        selection=[('refund_reason', 'Refund Reason'), ('bank', 'Bank'), 
                   ('locale', 'Locale'), ('other', 'Other')], string='Type', default='other')
    description = fields.Text(string='Description')
    name = fields.Char(string='Name', required=True)
    parentid = fields.Char(string='Parent ID')
    noticeNo = fields.Char(string='Notice No')
    
    
    def upsert(self, name, code_type, **kwargs):
        code = self.search([('name', '=', name), ('code_type', '=', code_type)])
        if code:
            return code.write(kwargs)
        kwargs.update(name=name, code_type=code_type)
        return self.create(kwargs)

    def name_get(self):
        return [(rec.id, f"[{rec.name}] {rec.description or ''}".strip()) for rec in self]
    

class EtimsStandardCodes(models.Model):
    _name = 'etims.standard.code'
    _inherit = 'etims.code'
    _description = 'ETIMS standard codes'
    
    def save_data(self, data):
        for group in data:
            code_type = STANDARD_CODE_MAP.get(group.get('cdClsNm'), 'other')
            
            for line in group.get('dtlList', []):
                kw = dict(description=line.get('cdNm'), parentid=group.get('cdCls'))
                self.upsert(name=line.get('cd'), code_type=code_type, **kw)


class EtimsClassificationCodes(models.Model):
    _name = 'etims.classification.code'
    _inherit = 'etims.code'
    _description = 'ETIMS classification codes'

    def save_data(self, data):
        for line in data:             
            kw = dict(description=line.get('itemClsNm'), parentid=line.get('itemClsLvl'))
            self.upsert(name=line.get('itemClsCd'), code_type='other', **kw)



class EtimsNotices(models.Model):
    _name = 'etims.notices'
    _inherit = 'etims.code'
    _description = 'ETIMS Notices Board'



    dtlUrl = fields.Char('URL')
    regrNm = fields.Char('Reg Number')
    

    def save_data(self, data):
        for line in data:             
            kw = dict(description=line.get('dtlUrl'), parentid=line.get('noticeNo'))
            self.upsert(name=line.get('title'), code_type='other', **kw)




class EtimsBranches(models.Model):
    _name = 'etims.branches'
    _inherit = 'etims.code'
    _description = 'ETIMS Branches'



    tin = fields.Char('KRA PIN')
    regrNm = fields.Char('Reg Number')
    

    def save_data(self, data):
        for line in data:             
            kw = dict(description=line.get('bhfNm'), parentid=line.get('mgrNm'),tin=line.get('tin'))
            self.upsert(name=line.get('bhfId'), code_type='other', **kw)



class EtimsStockCodes(models.AbstractModel):
    _name = 'etims.stock.code'
    _description = 'ETIMS Stock Codes'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    
    def name_get(self):
        return [(rec.id, f'[{rec.code}] {rec.name}') for rec in self]

    
class EtimsPackagingCodes(models.Model):
    _name = 'etims.package.code'
    _inherit = 'etims.stock.code'
    _description = 'ETIMS Packaging Codes'
        

class EtimsUOMCodes(models.Model):
    _name = 'etims.uom.code'
    _inherit = 'etims.stock.code'
    _description = 'ETIMS Uoms Codes'
    

class Uom(models.Model):
    _inherit = 'uom.uom'
    
    etims_code_id = fields.Many2one('etims.uom.code', string='ETIMS Code')


class ProductTemplate(models.Model):
    _inherit = 'product.template'



    incoming_quantity = fields.Integer(string='Incoming Stock')
    
    etims_ok = fields.Boolean(string='Etims Ok', readonly=True)
    country_origin_id = fields.Many2one('res.country', string='Country of Origin')
    etims_package_code_id = fields.Many2one('etims.package.code', string='Packaging')
    class_code_id = fields.Many2one('etims.classification.code', string='Etims Class Code')
    item_code = fields.Char(string='Item Code', readonly=False)
    etims_type = fields.Selection(string='ETIMS Product Type',
                                          selection=[('1', 'Raw Material'),
                                                     ('2', 'Finished Product'),
                                                     ('3', 'Service')])
    def _get_etims_code(self):
        self.ensure_one()
        if self.item_code:
            return self.item_code
        sequence = self.env["ir.sequence"].next_by_code("etims.product.code")
        return f'{self.country_origin_id.code}{self.etims_type}{self.etims_package_code_id.code}{self.uom_id.etims_code_id.code}{sequence}'
    
    def etims_save(self):
        etims = self.env['etims.core']
        res = None
        for rec in self:
            etims_code = rec._get_etims_code()
            # rec.write({'item_code':etims_code})
            # time.sleep(5)
            tax = self.taxes_id.filtered('etims_code').mapped('etims_code')[0]
            if not tax:
                raise ValidationError("Some products are missing a tax or the field 'Tax Type' on the tax has not been mapped")
            main_list= []

            stock_location = self.env['stock.location'].search([('branch_id.name', '=', self.env.company.etims_branchid)])
            _logger.info('stock_location.id')
            _logger.info(stock_location.id)
            _logger.info(stock_location.name)

        # find quantity of product in that location

            quantity = self.with_context({'location': stock_location.id}).qty_available


            
            payload = {
                # "BranchId": self.env.company.etims_branchid,
                
                "itemCode": etims_code,
                "itemClassifiCode": rec.class_code_id.name,
                "itemTypeCode": rec.etims_type,
                "itemName": rec.name,
                "itemStrdName": "",
                "countryCode": rec.country_origin_id.code,
                "pkgUnitCode": rec.etims_package_code_id.code,
                "qtyUnitCode": rec.uom_id.etims_code_id.code ,
                "taxTypeCode": tax,
                "batchNo": "",
                "barcode": "",
                "unitPrice": rec.list_price,
                "group1UnitPrice": 0,
                "group2UnitPrice": 0,
                "group3UnitPrice": 0,
                "group4UnitPrice": 0,
                "group5UnitPrice": 0,
                "additionalInfo": "",
                "saftyQuantity": round (quantity),
                "isInrcApplicable": True,
                "isUsed": True,
                "quantity": round (quantity),
                "packageQuantity": 0
            }

            main_list.append(payload)
            res = etims._call_etims(company=self.env.company, endpoint='save_item', payload=main_list)
            if res:
                rec.write({'etims_ok': True, 'item_code': etims_code})
        title = 'Products Save Details'
        if res:
            return etims._notify(title=title, message='Successfully Saved!')
        
        return etims._notify(title=title, message='Upload Failed! Please consult your Admin', type='danger')

    def _mass_etims_save(self):
        self.etims_save()



    def update_master_stock(self):
    
        etims = self.env['etims.core']

        _logger.info('==========================update_master_stock==========================')
        # get the user default stock location
        stock_location = self.env['stock.location'].search([('branch_id.name', '=', self.env.company.etims_branchid)])
        _logger.info('stock_location.id')
        _logger.info(stock_location.id)
        _logger.info(stock_location.name)

        # find quantity of product in that location

        quantity = self.with_context({'location': stock_location.id}).qty_available


        _logger.info("TEXT>>>>>>>>>>>>0>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> %s ",quantity)


        payload = {
            # "tin": self.env.company.vat,
            # "bhfId": self.env.company.etims_branchid, 
            "itemCode": self.item_code,
            "quantity": round (quantity),
            "packageQuantity": round (quantity),
            # "rsdQty": round (quantity),
            

            # "regrId": "null", 
            # "regrNm": "null", 
            # "modrId": "null", 
            # "modrNm": "null"
            }
        
        

        res = etims._call_etims(company=self.env.company, endpoint='master_stock', payload=payload)
        if res:
            title = 'Product Update Master Stock'
            if res:
                return etims._notify(title=title, message='Successfully Saved!')
            
        return etims._notify(title=title, message='Upload Failed! Please consult your Admin', type='danger')

        # response_data = api.move_master_update(json.dumps(payload))

        # _logger.info(response_data)

        # if response_data.get('resultCd') != '000':
        #     _logger.error(response_data.get('resultMsg'))
        #     raise UserError(f"API Error: {response_data.get('resultMsg')}")
            




    
    
class ProductProduct(models.Model):
    _inherit = 'product.product'


    incoming_quantity = fields.Integer(string='Incoming Stock')



    def update_master_stock(self):
        
        etims = self.env['etims.core']

        _logger.info('==========================update_master_stock==========================')
        # get the user default stock location
        stock_location = self.env['stock.location'].search([('branch_id.name', '=', self.env.company.etims_branchid)])
        _logger.info('stock_location.id')
        _logger.info(stock_location.id)
        _logger.info(stock_location.name)

        # find quantity of product in that location

        quantity = self.with_context({'location': stock_location.id}).qty_available


        _logger.info("TEXT>>>>>>>>>>>>0>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> %s ",quantity)


        payload = {
            # "tin": self.env.company.vat,
            # "bhfId": self.env.company.etims_branchid, 
            "itemCode": self.item_code,
            "quantity": round (quantity),
            "packageQuantity": round (quantity),
            }
        
        

        res = etims._call_etims(company=self.env.company, endpoint='master_stock', payload=payload)
        if res:
            title = 'Product Update Master Stock'
            if res:
                return etims._notify(title=title, message='Successfully Saved!')
            
        return etims._notify(title=title, message='Upload Failed! Please consult your Admin', type='danger')

        # response_data = api.move_master_update(json.dumps(payload))

        # _logger.info(response_data)

        # if response_data.get('resultCd') != '000':
        #     _logger.error(response_data.get('resultMsg'))
        #     raise UserError(f"API Error: {response_data.get('resultMsg')}")
            

            
    
    def etims_save(self):
        return self.product_tmpl_id.etims_save()
    
    def _mass_etims_save(self):
        for rec in self:
            rec.product_tmpl_id.etims_save()


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    branch_id = fields.Many2one('etims.branches', string="Branch")


class StockLocation(models.Model):
    _inherit = 'stock.location'

    branch_id = fields.Many2one('etims.branches', string="Branch")
