# -*- coding: utf-8 -*-

from odoo import models, fields
import time

import json
import logging

_logger = logging.getLogger(__name__)



class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    etims_code = fields.Selection(string='Tax Type', 
                            selection=[('A', 'A-Exempt'), 
                                       ('B', 'B-16%'),
                                       ('C', 'C-0%'), 
                                       ('D', 'D-Non-VAT'),
                                       ('E', 'E-8%')])
    
    
class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['account.move', 'etims.core']    
    
    def etims_save(self):
        self.sign_invoice()
        # time.sleep(15)

        # self.save_etims_stock_moves()
    tax_mapping = fields.Json(string='Tax Mapping', compute='_compute_tax_fields_v2')


    def _compute_tax_fields_v2(self):
            # get all taxes for invoice
        all_taxes = []
        taxes = self.env['account.tax'].search(
            [('etims_code', '!=', False), ('type_tax_use', '=', 'sale'),
             ('company_id', '=', self.company_id.id)
             ])
        for tax in taxes:
            # check i added to all_taxes

            # get all taxes of this type
            tax_lines = self.invoice_line_ids.filtered(lambda l: tax in l.tax_ids)
            taxbl_amt = sum(tax_lines.mapped('price_subtotal'))
            tax_amt = sum(tax_lines.mapped('price_total')) - taxbl_amt
            item_count = len(tax_lines)
            # get selection value for tax code
            value = dict(self.env['account.tax']._fields['etims_code'].selection).get(tax.etims_code)

            all_taxes.append({
                'tax_code': value,
                'name': tax.name,
                'taxbl_amt': round(taxbl_amt, 2),
                'tax_amt': round(tax_amt, 2),
                'item_count': item_count
            })

        _logger.info('=========all_taxes===========')
        _logger.info(json.dumps(all_taxes))
        self.tax_mapping = all_taxes

        pass

    def get_tax_rate_by_class(self, tax_class):
        """
        Get the tax rate for the given tax class.
        """
        # search etims.code.lines where code_class_name ='Taxation Type' and cd = tax_class
        # # return the tax rate
        # tax_code = self.env['etims.code.lines'].search([('cd_cls_nm', '=', 'Taxation Type'), ('cd', '=', tax_class)])
        # return tax_code.user_dfn_cd1

        return 16



class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    refund_reason_id = fields.Many2one('etims.standard.code',
                                       string='Refund Reason',
                                       domain=[('code_type', '=', 'refund_reason')])
    
    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        res.update(refund_reason_id=self.refund_reason_id.id)
        return res
