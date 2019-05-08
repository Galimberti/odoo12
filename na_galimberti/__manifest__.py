# -*- encoding: utf-8 -*-
{
    'name': 'NexApp Galimberti',
    'version': '1',
    'depends':	[
        'account',
        'base_geolocalize',
        'contacts',
        'crm',
        'mail',
        'purchase',
        'sale_management',
        'sale_crm',
        'stock',
        'sale_stock',
        'web_google_maps',
        'web_notify',
    ],
    'author': "Manuel Pagani",

    'website': 'http://www.nexapp.it',
    'category': 'NexApp',
    'sequence':	1,
    'data': [
        'data/zap_parameters.xml',
        'security/ir.model.access.csv',
        'views/category.xml',
        'views/crm.xml',
        'views/email.xml',
        # 'views/pacchi.xml',
        'views/product.xml',
        'views/purchase.xml',
        'views/res_partner.xml',
        'views/sale.xml',
        'views/scripts.xml',
        'views/sequence.xml',
        'views/stock.xml',
        'views/tendina.xml',
        'views/value_temp.xml',
    ],

    'installable': True,
    'application': True,
}