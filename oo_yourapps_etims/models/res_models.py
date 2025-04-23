# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
from datetime import datetime
DATE_FORMAT = 'YmdH%M%S'
import logging
_logger= logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    has_etims = fields.Boolean(string='Enable ETIMS', copy=False, help="Etims has been enabled")
    etims_ok = fields.Boolean(string='ETIMS Ok', readonly=True, copy=False, help="Branch is registered to Etims")
    etims_url = fields.Char(string='ETIMS Url', help="Etims url to send data to")
    etims_token = fields.Text(string='ETIMS Token', readonly=False, copy=False, help="Technical field having the etims access token")
    etims_last_request = fields.Char(string='ETIMS Last Request', copy=False, help="Technical field to retrieve last request date for requests")
    etims_branchid = fields.Char(string='Branch ID', copy=False, help="Unique etims branch ID")
    etims_device_serial = fields.Char(string='Device Serial', copy=False, help="Unique etims device serial number")
    etims_clientid = fields.Char(string='Client ID', copy=False, help="Etims Username / Client ID")
    etims_client_secret = fields.Char(string='Client Secrect', copy=False, help="Etims Client Secret / Password")
    
    @api.constrains('etims_branchid', 'etims_device_serial')
    def _constrains_etims(self):
        branches = self.search([('etims_branchid', 'in', self.mapped('etims_branchid')), ('id', 'not in', self.ids)])
        if branches:
            raise ValidationError(f"Duplicate ETIMS branch IDs are not allowed: {branches.mapped('etims_branchid')}")
        
    def etims_initialize(self):
        self.ensure_one()
        if not self.vat or not self.etims_branchid or not self.etims_branchid:
            raise ValidationError(f"Missing required fields: any of [vat, etims_branchid, etims_branchid]")
        
        etims = self.env['etims.core']
        # etims._login(self)
        payload = {
            'tin': self.vat.upper(),
            'bhfId': self.etims_branchid,
            'dvcSrlNo': self.etims_device_serial
        }
        res = etims._call_etims(company=self, endpoint='init', payload=payload)
        title = 'ETIMS Status'
        if res:
            return etims._notify(title=title, message='Successfully Initialized!')
        return etims._notify(title=title, message='Initialization Failed!', type='danger')
    
    def etims_save_branch(self):
        self.ensure_one()
        etims = self.env['etims.core']
        request_date = fields.Datetime.now().strftime(DATE_FORMAT)
        payload = {
            "tin": self.vat.upper(),
            "bhfId": self.etims_branchid,
            "lastReqDt": request_date
        }
        res = etims._call_etims(company=self, endpoint='save_branch', payload=payload)
        title = 'Branch Save Details'
        if res:
            self.write({'etims_ok': True, 'etims_last_request': request_date})
            return etims._notify(title=title, message='Successfully Saved!')
        
        return etims._notify(title=title, message='Upload Failed! Please consult your Admin', type='danger')
    
    def etims_save_users(self):
        return self.env['res.users'].search([]).etims_save()
        
    def etims_get_standard_codes(self):
        self.ensure_one()
        etims = self.env['etims.core']

        params = { "date": '20210301000000' }
        headers = { 'Content-Type': 'application/json','key': self.etims_token}
        
        key= "/GetCodeListV2"
        url= self.etims_url + key 
        try:

            response = requests.request('GET', url, headers=headers, params=params)
            response_data = response.json()
            if response_data.get('message') == 'Success':
                title = 'Get Product Codes'
                self.env['etims.standard.code'].save_data(response_data.get('responseData', {}).get('clsList', []))
                self.write({'etims_ok': True, 'etims_last_request': fields.Datetime.now().strftime(DATE_FORMAT)})
                return etims._notify(title=title, message='Successfully Retrieved!')
            
            else:
                return etims._notify(title=title, message='Error while Retrieving Codes! Please consult your Admin', type='danger')

        except Exception as e:
            _logger.error(e)
            return None

    def etims_get_classification_codes(self):
        self.ensure_one()
        etims = self.env['etims.core']
        params = { "date": '20210301000000' }
        headers = { 'Content-Type': 'application/json','key': self.etims_token}
        
        key= "/GetItemClassificationListV2"

        url= self.etims_url + key 

        try:
            response = requests.request('GET', url, headers=headers, params=params)
            _logger.info(headers)
            response_data = response.json()
            _logger.info(response.text)
            if response_data.get('message') == 'Success':
                title = 'Get Product Classification Codes'
                self.env['etims.classification.code'].save_data(response_data.get('responseData', {}).get('itemClsList', []))
                self.write({'etims_ok': True, 'etims_last_request': fields.Datetime.now().strftime(DATE_FORMAT)})
                return etims._notify(title=title, message='Successfully Retrieved!')
                
            else:
                return etims._notify(title=title, message='Error while Retrieving Codes! Please consult your Admin', type='danger')

        except Exception as e:
            _logger.error(e)
            return None
      
    def etims_get_notices(self):
        self.ensure_one()
        etims = self.env['etims.core']
        params = { "date": '20210301000000' }
        headers = { 'Content-Type': 'application/json','key': self.etims_token}
        
        key= "/GetNoticeListV2"

        url= self.etims_url + key 

        try:
            response = requests.request('GET', url, headers=headers, params=params)
            _logger.info(headers)
            response_data = response.json()
            _logger.info(response.text)
            if response_data.get('message') == 'Success':
                title = 'Get eTIMS Notices'
                self.env['etims.notices'].save_data(response_data.get('responseData', {}).get('noticeList', []))
                self.write({'etims_ok': True, 'etims_last_request': fields.Datetime.now().strftime(DATE_FORMAT)})
                return etims._notify(title=title, message=' NOtices Successfully Retrieved!')
                
            else:
                return etims._notify(title=title, message='Error while Retrieving Notices! Please consult your Admin', type='danger')

        except Exception as e:
            _logger.error(e)
            return None
        


    def etims_get_branches(self):
        self.ensure_one()
        etims = self.env['etims.core']
        params = { "date": '20210301000000' }
        headers = { 'Content-Type': 'application/json','key': self.etims_token}
        
        key= "/GetBranchListV2"

        url= self.etims_url + key 

        try:
            response = requests.request('GET', url, headers=headers, params=params)
            _logger.info(headers)
            response_data = response.json()
            _logger.info(response.text)
            if response_data.get('message') == 'Success':
                title = 'Get eTIMS Branches'
                self.env['etims.branches'].save_data(response_data.get('responseData', {}).get('bhfList', []))
                self.write({'etims_ok': True, 'etims_last_request': fields.Datetime.now().strftime(DATE_FORMAT)})
                return etims._notify(title=title, message=' Branches Successfully Retrieved!')
                
            else:
                return etims._notify(title=title, message='Error while Retrieving Branches! Please consult your Admin', type='danger')

        except Exception as e:
            _logger.error(e)
            return None
    
    def action_get_purchases(self):
        self.ensure_one()
        etims = self.env['etims.core']
        params = { "date": '20210301000000' }
        headers = { 'Content-Type': 'application/json','key': self.etims_token}
        
        key= "/GetPurchaseListV2"

        url= self.etims_url + key 

        try:
            response = requests.request('GET', url, headers=headers, params=params)
            _logger.info(headers)
            response_data = response.json()
            _logger.info(response.text)
            if response_data.get('message') == 'Success':
                title = 'Get Purchases'
                self.env['etims.purchases'].create_etims_purchase(response_data.get('responseData', {}).get('saleList', []))
                self.write({'etims_ok': True, 'etims_last_request': fields.Datetime.now().strftime(DATE_FORMAT)})
                return etims._notify(title=title, message=' Purchases Successfully Retrieved!')
                
            else:
                return etims._notify(title=title, message='Error while Retrieving Purchases! Please consult your Admin', type='danger')

        except Exception as e:
            _logger.error(e)
            return None
        # api = ETIMSConnect(self.kra_pin, self.env.user.branch_id.bhf_id)
        # # sudo = self
        # response = api.get_purchases()
        # if response:
        #     if response.get('resultCd') != '000':
        #         raise UserError(f"API Error: {response.get('resultMsg')}")
        #     else:
        #         self.env['etims.purchases'].create_etims_purchase(response.get('data', {}).get('saleList', []))
        #     return {
        #         'type': 'ir.actions.client',
        #         'tag': 'display_notification',
        #         'params': {
        #             'title': 'Success',
        #             'message': 'Purchases Fetched successfully',
        #             'type': 'success',
        #             'sticky': True,
        #         }
        #     }

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    etims_ok = fields.Boolean(string='ETIMS Ok', readonly=True, copy=False)
    
    def etims_save(self):
        etims = self.env['etims.core']
        if not self.vat:
            raise ValidationError('Missing required fields: [vat] on customer {self.name}')
        
        company = self.env.company or self.company_id
        address = (self.street or "") + (self.street2 or "") + (self.city or "")

        payload = {
        
            "customerNo": f'{self.id}',
            "customerTin": self.vat.upper(),
            "customerName": self.name.upper(),
            "address": address[:30],
            "telNo": self.phone,
            "email": self.email,
            "faxNo": "",
            "isUsed": True,
            "remark": "Active"
        }
        res = etims._call_etims(company=company, endpoint='save_customer', payload=payload)
        title = 'Customer Save Details'
        if res:
            self.write({'etims_ok': True})
            return etims._notify(title=title, message='Successfully Saved!')
        return etims._notify(title=title, message='Upload Failed! Please consult your Admin', type='danger')

    def _mass_etims_save(self):
        for rec in self:
            rec.etims_save()
            

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    etims_ok = fields.Boolean(string='ETIMS Ok', readonly=True, copy=False)
    
    def etims_save(self):
        etims = self.env['etims.core']
        for rec in self:
            company = self.env.company
            payload = {
                # "BranchId": company.etims_branchid,
                "branchUserId": f'{rec.id}',
                "branchUserName": rec.login,
                "password": "testpassword",
                "address": "Nairobi",
                "contactNo": "9876543210",
                "authenticationCode": "123456",
                "remark": "Active",
                "isUsed": True,


            }
            res = etims._call_etims(company=company, endpoint='save_user', payload=payload)
            title = 'User Save Details'
            if res:
                rec.write({'etims_ok': True})
                return etims._notify(title=title, message='Successfully Saved!')
            return etims._notify(title=title, message='Upload Failed! Please consult your Admin', type='danger')
    