{
    'name': 'WhatsApp Turismo Bot',
    'summary': 'Onboarding de prestadores turísticos por WhatsApp y web con aprobación interna',
    'version': '18.0.1.1.0',
    'author': 'Tu Organización',
    'website': 'https://example.com',
    'license': 'LGPL-3',
    'category': 'Website',
    'depends': [
        'base',
        'mail',
        'portal',
        'website',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/default_data.xml',
        'data/cron.xml',
        'views/tourism_provider_views.xml',
        'views/whatsapp_bot_session_views.xml',
        'views/tourism_post_views.xml',
        'views/menu_views.xml',
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'whatsapp_turismo_bot/static/src/css/portal_tourism.css',
        ],
    },
    'installable': True,
    'application': True,
}
