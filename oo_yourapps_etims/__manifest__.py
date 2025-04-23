# -*- coding: utf-8 -*-
{
    'name': "KRA ETIMs VIA YourApps",

    'summary': """
        ETIMs via YourApps APIs""",

    'description': """
        Long description of module's purpose
    """,
    'category': 'Extra Tools',
    'version': '0.1',
    'author': 'Eric Kinyua ',
    'web': 'kinyuaeric332@gmail.com',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['account', 'point_of_sale','contacts'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/actions.xml',
        'data/etims.package.code.csv',
        'data/etims.uom.code.csv',
        
        'reports/invoice.xml',
        
        'views/res_models.xml',
        'views/etims.xml',
        'views/stock.xml',
        'views/accounts.xml',
        'views/pos.xml',
        'views/etims_purchases.xml',
    ],
    'assets': {
            'point_of_sale.assets': [
                'oo_yourapps_etims/static/src/js/PaymentScreen.js',
                'oo_yourapps_etims/static/src/js/Order.js',
                'oo_yourapps_etims/static/src/xml/OrderReceipt.xml',
            ],
        },
}
