import logging

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WhatsappService(models.AbstractModel):
    _name = 'whatsapp.service'
    _description = 'Servicios de integración con Meta Cloud API'

    def _get_params(self):
        icp = self.env['ir.config_parameter'].sudo()
        return {
            'verify_token': icp.get_param('whatsapp_turismo_bot.whatsapp_verify_token', default='TODO_VERIFY_TOKEN'),
            'access_token': icp.get_param('whatsapp_turismo_bot.whatsapp_access_token', default='TODO_ACCESS_TOKEN'),
            'phone_number_id': icp.get_param('whatsapp_turismo_bot.whatsapp_phone_number_id', default='TODO_PHONE_ID'),
            'graph_api_version': icp.get_param('whatsapp_turismo_bot.whatsapp_graph_api_version', default='v20.0'),
        }

    def build_send_url(self):
        params = self._get_params()
        return f"https://graph.facebook.com/{params['graph_api_version']}/{params['phone_number_id']}/messages"

    def send_text(self, phone, message):
        params = self._get_params()
        payload = {
            'messaging_product': 'whatsapp',
            'to': phone,
            'type': 'text',
            'text': {'body': message},
        }
        headers = {
            'Authorization': f"Bearer {params['access_token']}",
            'Content-Type': 'application/json',
        }
        response = requests.post(self.build_send_url(), json=payload, headers=headers, timeout=20)
        if response.status_code >= 400:
            _logger.exception('Error enviando WhatsApp: %s', response.text)
            raise UserError(_('No se pudo enviar mensaje de WhatsApp.'))
        return response.json()

    def fetch_media_binary(self, media_id):
        params = self._get_params()
        media_info_url = f"https://graph.facebook.com/{params['graph_api_version']}/{media_id}"
        headers = {'Authorization': f"Bearer {params['access_token']}"}
        info_resp = requests.get(media_info_url, headers=headers, timeout=20)
        info_resp.raise_for_status()
        media_url = info_resp.json().get('url')
        file_resp = requests.get(media_url, headers=headers, timeout=30)
        file_resp.raise_for_status()
        return file_resp.content

    def extract_incoming_messages(self, payload):
        messages = []
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                messages.extend(value.get('messages', []))
        return messages

    def build_reply_for_state(self, state):
        prompts = {
            'start': '¡Hola! Bienvenido/a al registro turístico. ¿Cuál es el nombre de tu negocio?',
            'asking_business_name': 'Gracias. Ahora indícame el nombre del responsable.',
            'asking_responsible_name': 'Perfecto. ¿Qué categoría turística te describe mejor?',
            'asking_category': 'Anotado. ¿Cuál es tu teléfono de contacto?',
            'asking_phone': 'Gracias. ¿Cuál es tu correo electrónico?',
            'asking_email': '¿En qué ubicación operas?',
            'asking_location': 'Cuéntame una descripción breve de tus servicios.',
            'asking_description': 'Por favor envíame una foto de perfil de tu negocio.',
            'asking_profile_photo': '¡Listo! Tu registro quedó en revisión. Te avisaremos cuando esté aprobado.',
            'completed': 'Tu información ya fue registrada. Si quieres actualizar datos responde "actualizar".',
        }
        return prompts.get(state, 'Gracias por tu mensaje. Te responderemos pronto.')
