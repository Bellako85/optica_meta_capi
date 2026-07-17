{
    'name': 'Optica Meta CAPI',
    'version': '17.0.1.0.0',
    'summary': 'Integración de Meta Conversions API (CAPI) para Óptica Zamora.',
    'description': """
Módulo personalizado para integrar Odoo con la API de Conversiones de Meta (CAPI).
=================================================================================

Flujos automatizados y eventos soportados:
-----------------------------------------
* **Lead (CRM):** Se dispara automáticamente cuando un prospecto es arrastrado a la etapa de 'Calificado' en el CRM, enviando los datos de contacto del cliente de forma segura.
* **Schedule (Citas):** Registra el evento de agendación en Meta cuando se envía la invitación por correo electrónico al paciente desde el asistente de citas de la óptica.
* **Purchase (Ventas):** Envía el evento de compra con el valor real y la moneda al confirmar un presupuesto en el módulo de Ventas.

Características de Seguridad y Optimización:
--------------------------------------------
* Encriptación automática de datos personales (correo y teléfono) usando SHA-256 antes del envío.
* Configuración centralizada desde el panel de Ajustes de Odoo (Token de acceso, Pixel ID, activar/desactivar y código de eventos de prueba).
* Soporte para eventos del lado del navegador (Pixel) y del servidor (CAPI) para mejorar la calidad de coincidencia.
    """,
    'author': 'Bellako85',
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
        'mail',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
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
