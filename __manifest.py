{
    'name': 'Optica Meta CAPI',
    'version': '17.0.1.0.0',
    'summary': 'Meta Conversions API integration for Optica Zamora',
    'description': """
Meta Conversions API integration for Odoo 17.

Features:
- Purchase Events
- WhatsApp Click Events
- Lead Events
- Server-side Meta CAPI
- Event Deduplication
- SHA-256 User Hashing
""",
    'author': 'Optica Zamora',
    'website': 'https://optica-zamora.com',
    'category': 'Website',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'web',
        'website',
        'website_sale',
        'crm',
        'sale',
    ],

    'data': [
        'views/res_config_settings_views.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'optica_meta_capi/static/src/js/meta_pixel.js',
        ],
    },

    'installable': True,
    'application': False,
    'auto_install': False,
}
