
from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import datetime
import logging

_logger = logging.getLogger(__name__)
stock_movements = [
    ('01', 'Import '),
    ('02', 'Purchase'),
    ('03', 'Return'),
    ('04', 'Stock Movement (Incoming)'),
    ('05', 'Processing'),
    ('06', 'Adjustment (Incoming)'),
    ('11', 'Sale'),
    ('12', 'Return (Outgoing)'),
    ('13', 'Stock Movement (Outgoing)'),
    ('14', 'Processing (Outgoing)'),
    ('15', 'Discarding'),
    ('16', 'Adjustment (Outgoing)'),
]


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sent_to_etims = fields.Boolean(string='Sent to eTIMS', default=False)

    supplier_tin = fields.Char("Supplier Tin")
    supplier_invoice = fields.Char("Supplier Invoice Number")
    supplier_name = fields.Char("Supplier Name")
    supplier_branch = fields.Char("supplier Branch")

    purchase_type_code = fields.Selection([
        ('C', 'Copy'),
        ('N', 'Normal'),
        ('P', 'Proforma'),
        ('T', 'Training')
    ], string='Purchase Type Code')
    registration_type_code = fields.Selection([
        ('A', 'Automatic'),
        ('M', 'Manual')
    ], string='Registration Type Code')

    receipt_type = fields.Selection([
        ('P', "Purchase"),
        ('R', 'Credit Note after Purchase')
    ])

    payment_type_code = fields.Selection([
        ('01', "CASH"),
        ('02', "CREDIT"),
        ('03', "CASH/CREDIT"),
        ('04', 'BANK CHECK'),
        ('05', "DEBIT&CREDIT"),
        ('06', 'MOBILE MONEY'),
        ('07', 'OTHER')
    ])

    purchase_status = fields.Selection([
        ('01', "Wait for Approval"),
        ('02', "Approved"),
        ('03', "Credit Note Requested"),
        ('04', 'Cancelled'),
        ('05', "Credit Note Generated"),
        ('06', 'Transferred'),
    ])
