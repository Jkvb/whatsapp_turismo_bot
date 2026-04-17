from odoo import fields, models


class WhatsappBotSession(models.Model):
    _name = 'whatsapp.bot.session'
    _description = 'Sesión conversacional de WhatsApp'
    _order = 'last_message_at desc, id desc'

    phone = fields.Char(required=True, index=True)
    provider_id = fields.Many2one('tourism.provider', ondelete='set null')
    state = fields.Selection(
        [
            ('start', 'Inicio'),
            ('asking_business_name', 'Pidiendo nombre del negocio'),
            ('asking_responsible_name', 'Pidiendo responsable'),
            ('asking_category', 'Pidiendo categoría'),
            ('asking_phone', 'Pidiendo teléfono'),
            ('asking_email', 'Pidiendo correo'),
            ('asking_location', 'Pidiendo ubicación'),
            ('asking_description', 'Pidiendo descripción'),
            ('asking_profile_photo', 'Pidiendo foto de perfil'),
            ('completed', 'Completado'),
        ],
        default='start',
        required=True,
    )
    active = fields.Boolean(default=True)
    last_message_at = fields.Datetime()
    last_payload = fields.Json()
    last_user_message = fields.Text()
    last_bot_message = fields.Text()
    retry_count = fields.Integer(default=0)

    _sql_constraints = [
        ('session_phone_active_unique', 'unique(phone, active)', 'Ya existe una sesión activa para este número.'),
    ]

    def next_state(self, target_state, bot_message=None):
        self.write({
            'state': target_state,
            'last_bot_message': bot_message or self.last_bot_message,
            'last_message_at': fields.Datetime.now(),
        })
