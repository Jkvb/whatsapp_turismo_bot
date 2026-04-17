import json

from odoo import fields, http
from odoo.http import request


class WhatsAppWebhookController(http.Controller):

    @http.route('/whatsapp/webhook', type='http', auth='public', methods=['GET'], csrf=False)
    def verify_webhook(self, **kwargs):
        mode = kwargs.get('hub.mode')
        challenge = kwargs.get('hub.challenge')
        token = kwargs.get('hub.verify_token')
        expected_token = request.env['ir.config_parameter'].sudo().get_param(
            'whatsapp_turismo_bot.whatsapp_verify_token'
        )
        if mode == 'subscribe' and token and token == expected_token:
            return request.make_response(challenge or '', headers=[('Content-Type', 'text/plain')])
        return request.make_response('Verification failed', status=403)

    @http.route('/whatsapp/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_webhook(self):
        payload = request.jsonrequest or {}
        whatsapp_service = request.env['whatsapp.service'].sudo()
        onboarding_service = request.env['tourism.onboarding.service'].sudo()
        media_service = request.env['tourism.media.service'].sudo()
        session_model = request.env['whatsapp.bot.session'].sudo()

        for msg in whatsapp_service.extract_incoming_messages(payload):
            phone = msg.get('from')
            message_type = msg.get('type')
            if not phone:
                continue

            session = session_model.search([('phone', '=', phone), ('active', '=', True)], limit=1)
            if not session:
                session = session_model.create({'phone': phone, 'state': 'start', 'last_payload': payload})

            user_text = ''
            if message_type == 'text':
                user_text = msg.get('text', {}).get('body', '').strip()
                self._process_text_message(session, user_text, onboarding_service, whatsapp_service)
            elif message_type == 'image':
                media_id = msg.get('image', {}).get('id')
                if media_id and session.provider_id and session.state == 'asking_profile_photo':
                    media_service.save_whatsapp_image_to_provider(session.provider_id, media_id, 'profile_image_1920')
                    session.next_state('completed', whatsapp_service.build_reply_for_state('asking_profile_photo'))
                    whatsapp_service.send_text(phone, session.last_bot_message)

            session.write({
                'last_payload': payload,
                'last_user_message': user_text or message_type,
                'last_message_at': fields.Datetime.now(),
            })

        return {'status': 'ok'}

    def _process_text_message(self, session, user_text, onboarding_service, whatsapp_service):
        current_state = session.state
        provider = session.provider_id

        if current_state == 'start':
            session.next_state('asking_business_name', whatsapp_service.build_reply_for_state('start'))
        elif current_state == 'asking_business_name':
            provider = onboarding_service.create_or_update_provider(
                {'name': user_text, 'commercial_name': user_text, 'whatsapp_number': session.phone},
                source='whatsapp',
            )
            session.write({'provider_id': provider.id})
            session.next_state('asking_responsible_name', whatsapp_service.build_reply_for_state(current_state))
        elif current_state == 'asking_responsible_name' and provider:
            provider.write({'responsible_name': user_text})
            session.next_state('asking_category', whatsapp_service.build_reply_for_state(current_state))
        elif current_state == 'asking_category' and provider:
            category = request.env['tourism.provider.category'].sudo().search([('name', 'ilike', user_text)], limit=1)
            if category:
                provider.write({'category_id': category.id})
            session.next_state('asking_phone', whatsapp_service.build_reply_for_state(current_state))
        elif current_state == 'asking_phone' and provider:
            provider.write({'phone': user_text, 'mobile': user_text})
            session.next_state('asking_email', whatsapp_service.build_reply_for_state(current_state))
        elif current_state == 'asking_email' and provider:
            provider.write({'email': user_text})
            session.next_state('asking_location', whatsapp_service.build_reply_for_state(current_state))
        elif current_state == 'asking_location' and provider:
            provider.write({'location_text': user_text})
            session.next_state('asking_description', whatsapp_service.build_reply_for_state(current_state))
        elif current_state == 'asking_description' and provider:
            provider.write({'description': user_text, 'approval_state': 'pending'})
            session.next_state('asking_profile_photo', whatsapp_service.build_reply_for_state(current_state))
        elif current_state == 'completed':
            session.next_state('completed', whatsapp_service.build_reply_for_state('completed'))
        else:
            session.write({'retry_count': session.retry_count + 1})
            session.next_state(current_state, 'No entendí tu respuesta, por favor intenta de nuevo.')

        if session.last_bot_message:
            whatsapp_service.send_text(session.phone, session.last_bot_message)


class JsonEncoder(json.JSONEncoder):
    pass
