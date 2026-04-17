import json
import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

MAX_UNKNOWN_RETRIES = 5
CANCEL_KEYWORDS = {'cancelar', 'cancel', 'salir', 'detener', 'stop'}


class WhatsAppWebhookController(http.Controller):

    @http.route('/whatsapp/webhook', type='http', auth='public', methods=['GET'], csrf=False)
    def verify_webhook(self, **kwargs):
        mode = kwargs.get('hub.mode')
        challenge = kwargs.get('hub.challenge')
        token = kwargs.get('hub.verify_token')
        expected_token = request.env['ir.config_parameter'].sudo().get_param(
            'whatsapp_turismo_bot.whatsapp_verify_token'
        )

        _logger.warning(
            'WA WEBHOOK GET | mode=%s | challenge=%s | token=%s | expected_token=%s',
            mode, challenge, token, expected_token
        )

        if mode == 'subscribe' and token and token == expected_token:
            _logger.warning('WA WEBHOOK GET OK | returning challenge=%s', challenge)
            return request.make_response(
                challenge or '',
                headers=[('Content-Type', 'text/plain')]
            )

        _logger.error(
            'WA WEBHOOK GET FAIL | mode=%s | token=%s | expected_token=%s',
            mode, token, expected_token
        )
        return request.make_response('Verification failed', status=403)

    def _extract_payload_context(self, payload):
        entry0 = (payload.get('entry') or [{}])[0]
        change0 = (entry0.get('changes') or [{}])[0]
        value0 = change0.get('value') or {}
        metadata = value0.get('metadata') or {}

        field_name = change0.get('field')
        display_phone_number = metadata.get('display_phone_number')
        phone_number_id = metadata.get('phone_number_id')

        is_meta_sample = (
            phone_number_id == '123456123'
            or display_phone_number == '16505551111'
        )

        return {
            'entry0': entry0,
            'change0': change0,
            'value0': value0,
            'metadata': metadata,
            'field_name': field_name,
            'display_phone_number': display_phone_number,
            'phone_number_id': phone_number_id,
            'is_meta_sample': is_meta_sample,
        }

    def _can_send_reply(self, phone, payload_ctx):
        if payload_ctx.get('is_meta_sample'):
            return False
        if not phone:
            return False
        return True

    @http.route('/whatsapp/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def receive_webhook(self, **kwargs):
        try:
            headers = request.httprequest.headers
            _logger.warning(
                'WA WEBHOOK HEADERS | remote_addr=%s | user_agent=%s | x_forwarded_for=%s | x_hub_signature_256=%s',
                request.httprequest.remote_addr,
                headers.get('User-Agent'),
                headers.get('X-Forwarded-For'),
                headers.get('X-Hub-Signature-256'),
            )

            raw_body = request.httprequest.get_data(as_text=True)
            _logger.warning('WA WEBHOOK POST RAW BODY: %s', raw_body)

            try:
                payload = json.loads(raw_body or '{}')
            except Exception:
                _logger.exception('WA WEBHOOK POST | invalid json body')
                payload = {}

            _logger.warning(
                'WA WEBHOOK POST PARSED PAYLOAD: %s',
                json.dumps(payload, ensure_ascii=False, default=str)
            )

            payload_ctx = self._extract_payload_context(payload)
            _logger.warning(
                'WA PAYLOAD META | field=%s | sample=%s | display_phone_number=%s | phone_number_id=%s',
                payload_ctx['field_name'],
                payload_ctx['is_meta_sample'],
                payload_ctx['display_phone_number'],
                payload_ctx['phone_number_id'],
            )

            if payload_ctx['is_meta_sample']:
                _logger.warning(
                    'WA META SAMPLE DETECTED | sample payload received from Meta dashboard test'
                )
            else:
                _logger.warning(
                    'WA REAL INBOUND CANDIDATE | display_phone_number=%s | phone_number_id=%s',
                    payload_ctx['display_phone_number'],
                    payload_ctx['phone_number_id'],
                )

            whatsapp_service = request.env['whatsapp.service'].sudo()
            onboarding_service = request.env['tourism.onboarding.service'].sudo()
            media_service = request.env['tourism.media.service'].sudo()
            session_model = request.env['whatsapp.bot.session'].sudo()

            messages = whatsapp_service.extract_incoming_messages(payload)
            _logger.warning('WA WEBHOOK POST | extracted_messages=%s', len(messages))

            for msg in messages:
                phone = msg.get('from')
                message_type = msg.get('type')

                _logger.warning(
                    'WA WEBHOOK MSG | phone=%s | type=%s | msg=%s',
                    phone, message_type, json.dumps(msg, ensure_ascii=False, default=str)
                )

                if not phone:
                    _logger.warning('WA WEBHOOK MSG SKIPPED | no phone')
                    continue

                session = session_model.search([('phone', '=', phone), ('active', '=', True)], limit=1)
                if not session:
                    session = session_model.create({
                        'phone': phone,
                        'state': 'start',
                        'last_payload': payload,
                    })
                    _logger.warning('WA SESSION CREATED | id=%s | phone=%s', session.id, phone)
                else:
                    _logger.warning(
                        'WA SESSION FOUND | id=%s | phone=%s | state=%s',
                        session.id, phone, session.state
                    )

                user_text = ''

                if message_type == 'text':
                    user_text = msg.get('text', {}).get('body', '').strip()
                    _logger.warning(
                        'WA TEXT RECEIVED | session_id=%s | text=%s',
                        session.id, user_text
                    )
                    self._process_text_message(
                        session=session,
                        user_text=user_text,
                        onboarding_service=onboarding_service,
                        whatsapp_service=whatsapp_service,
                        payload_ctx=payload_ctx,
                    )

                elif message_type == 'image':
                    media_id = msg.get('image', {}).get('id')
                    _logger.warning(
                        'WA IMAGE RECEIVED | session_id=%s | media_id=%s | state=%s',
                        session.id, media_id, session.state
                    )

                    if media_id and session.provider_id and session.state == 'asking_profile_photo':
                        try:
                            media_service.save_whatsapp_image_to_provider(
                                session.provider_id,
                                media_id,
                                'profile_image_1920'
                            )
                            _logger.warning(
                                'WA IMAGE SAVED | provider_id=%s | media_id=%s',
                                session.provider_id.id,
                                media_id
                            )

                            session.next_state(
                                'completed',
                                whatsapp_service.build_reply_for_state('asking_profile_photo')
                            )
                            _logger.warning(
                                'WA SESSION COMPLETED BY IMAGE | session_id=%s | new_state=%s',
                                session.id, session.state
                            )

                            if self._can_send_reply(phone, payload_ctx):
                                whatsapp_service.send_text(phone, session.last_bot_message)
                                _logger.warning(
                                    'WA REPLY SENT AFTER IMAGE | session_id=%s | phone=%s',
                                    session.id, phone
                                )
                            else:
                                _logger.warning(
                                    'WA REPLY SKIPPED | reason=meta_sample | session_id=%s | phone=%s',
                                    session.id, phone
                                )

                        except Exception:
                            _logger.exception(
                                'WA IMAGE PROCESS FAIL | session_id=%s | phone=%s | media_id=%s',
                                session.id, phone, media_id
                            )
                    else:
                        _logger.warning(
                            'WA IMAGE IGNORED | session_id=%s | phone=%s | media_id=%s | state=%s | provider_id=%s',
                            session.id,
                            phone,
                            media_id,
                            session.state,
                            session.provider_id.id if session.provider_id else False
                        )

                else:
                    _logger.warning('WA MSG TYPE NOT HANDLED | type=%s', message_type)

                session.write({
                    'last_payload': payload,
                    'last_user_message': user_text or message_type,
                    'last_message_at': fields.Datetime.now(),
                })

                _logger.warning(
                    'WA SESSION UPDATED | id=%s | state=%s | last_user_message=%s',
                    session.id, session.state, session.last_user_message
                )

            return request.make_response(
                json.dumps({'status': 'ok'}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception:
            _logger.exception('WA WEBHOOK POST FATAL ERROR')
            return request.make_response(
                json.dumps({'status': 'error'}),
                headers=[('Content-Type', 'application/json')],
                status=500
            )

    def _process_text_message(self, session, user_text, onboarding_service, whatsapp_service, payload_ctx):
        current_state = session.state
        provider = session.provider_id
        normalized_text = (user_text or '').strip().lower()

        _logger.warning(
            'WA PROCESS START | session_id=%s | phone=%s | current_state=%s | provider_id=%s | text=%s',
            session.id, session.phone, current_state, provider.id if provider else False, user_text
        )

        if normalized_text in CANCEL_KEYWORDS:
            session.write({'active': False})
            session.next_state(
                current_state,
                whatsapp_service.build_reply_for_state('cancelled')
            )
            _logger.warning(
                'WA SESSION CANCELLED BY USER | session_id=%s | state=%s | text=%s',
                session.id, current_state, user_text
            )
            return self._send_session_reply(session, whatsapp_service, payload_ctx)

        if current_state == 'start':
            session.next_state('asking_business_name', whatsapp_service.build_reply_for_state('start'))
            _logger.warning(
                'WA STATE CHANGE | session_id=%s | from=%s | to=%s',
                session.id, current_state, session.state
            )

        elif current_state == 'asking_business_name':
            provider = onboarding_service.create_or_update_provider(
                {
                    'name': user_text,
                    'commercial_name': user_text,
                    'whatsapp_number': session.phone,
                },
                source='whatsapp',
            )
            session.write({'provider_id': provider.id})
            _logger.warning(
                'WA PROVIDER UPSERT | session_id=%s | provider_id=%s | business_name=%s',
                session.id, provider.id, user_text
            )

            session.next_state('asking_responsible_name', whatsapp_service.build_reply_for_state(current_state))
            _logger.warning(
                'WA STATE CHANGE | session_id=%s | from=%s | to=%s',
                session.id, current_state, session.state
            )

        elif current_state == 'asking_responsible_name' and provider:
            provider.write({'responsible_name': user_text})
            _logger.warning(
                'WA PROVIDER UPDATE | provider_id=%s | responsible_name=%s',
                provider.id, user_text
            )

            session.next_state('asking_category', whatsapp_service.build_reply_for_state(current_state))
            _logger.warning(
                'WA STATE CHANGE | session_id=%s | from=%s | to=%s',
                session.id, current_state, session.state
            )

        elif current_state == 'asking_category' and provider:
            category = request.env['tourism.provider.category'].sudo().search(
                [('name', 'ilike', user_text)], limit=1
            )

            _logger.warning(
                'WA CATEGORY SEARCH | text=%s | found_category_id=%s',
                user_text, category.id if category else False
            )

            if category:
                provider.write({'category_id': category.id})
                _logger.warning(
                    'WA PROVIDER UPDATE | provider_id=%s | category_id=%s',
                    provider.id, category.id
                )

            session.next_state('asking_phone', whatsapp_service.build_reply_for_state(current_state))
            _logger.warning(
                'WA STATE CHANGE | session_id=%s | from=%s | to=%s',
                session.id, current_state, session.state
            )

        elif current_state == 'asking_phone' and provider:
            provider.write({'phone': user_text, 'mobile': user_text})
            _logger.warning(
                'WA PROVIDER UPDATE | provider_id=%s | phone=%s',
                provider.id, user_text
            )

            session.next_state('asking_email', whatsapp_service.build_reply_for_state(current_state))
            _logger.warning(
                'WA STATE CHANGE | session_id=%s | from=%s | to=%s',
                session.id, current_state, session.state
            )

        elif current_state == 'asking_email' and provider:
            provider.write({'email': user_text})
            _logger.warning(
                'WA PROVIDER UPDATE | provider_id=%s | email=%s',
                provider.id, user_text
            )

            session.next_state('asking_location', whatsapp_service.build_reply_for_state(current_state))
            _logger.warning(
                'WA STATE CHANGE | session_id=%s | from=%s | to=%s',
                session.id, current_state, session.state
            )

        elif current_state == 'asking_location' and provider:
            provider.write({'location_text': user_text})
            _logger.warning(
                'WA PROVIDER UPDATE | provider_id=%s | location=%s',
                provider.id, user_text
            )

            session.next_state('asking_description', whatsapp_service.build_reply_for_state(current_state))
            _logger.warning(
                'WA STATE CHANGE | session_id=%s | from=%s | to=%s',
                session.id, current_state, session.state
            )

        elif current_state == 'asking_description' and provider:
            provider.write({'description': user_text, 'approval_state': 'pending'})
            _logger.warning(
                'WA PROVIDER UPDATE | provider_id=%s | description=%s | approval_state=pending',
                provider.id, user_text
            )

            session.next_state('asking_profile_photo', whatsapp_service.build_reply_for_state(current_state))
            _logger.warning(
                'WA STATE CHANGE | session_id=%s | from=%s | to=%s',
                session.id, current_state, session.state
            )

        elif current_state == 'completed':
            session.next_state('completed', whatsapp_service.build_reply_for_state('completed'))
            _logger.warning(
                'WA COMPLETED REPLY | session_id=%s | state=%s',
                session.id, session.state
            )

        else:
            retry_count = session.retry_count + 1
            session.write({'retry_count': retry_count})
            _logger.warning(
                'WA UNKNOWN INPUT | session_id=%s | state=%s | retry_count=%s | text=%s',
                session.id, session.state, session.retry_count, user_text
            )
            if retry_count >= MAX_UNKNOWN_RETRIES:
                session.write({'active': False})
                session.next_state(
                    current_state,
                    whatsapp_service.build_reply_for_state('too_many_retries')
                )
                _logger.warning(
                    'WA SESSION AUTO-CANCELLED | session_id=%s | state=%s | retry_count=%s',
                    session.id, current_state, retry_count
                )
            elif current_state == 'asking_profile_photo':
                session.next_state(
                    current_state,
                    whatsapp_service.build_reply_for_state('asking_profile_photo_retry')
                )
            else:
                session.next_state(current_state, 'No entendí tu respuesta, por favor intenta de nuevo.')

        self._send_session_reply(session, whatsapp_service, payload_ctx)

    def _send_session_reply(self, session, whatsapp_service, payload_ctx):
        if session.last_bot_message:
            try:
                _logger.warning(
                    'WA SENDING REPLY | session_id=%s | phone=%s | message=%s | is_meta_sample=%s',
                    session.id, session.phone, session.last_bot_message, payload_ctx.get('is_meta_sample')
                )

                if self._can_send_reply(session.phone, payload_ctx):
                    whatsapp_service.send_text(session.phone, session.last_bot_message)
                    _logger.warning(
                        'WA REPLY SENT OK | session_id=%s | phone=%s',
                        session.id, session.phone
                    )
                else:
                    _logger.warning(
                        'WA REPLY SKIPPED | reason=meta_sample | session_id=%s | phone=%s | message=%s',
                        session.id, session.phone, session.last_bot_message
                    )

            except Exception:
                _logger.exception(
                    'WA REPLY SEND FAIL | session_id=%s | phone=%s | message=%s',
                    session.id, session.phone, session.last_bot_message
                )
        else:
            _logger.warning(
                'WA NO BOT MESSAGE TO SEND | session_id=%s | phone=%s | state=%s',
                session.id, session.phone, session.state
            )


class JsonEncoder(json.JSONEncoder):
    pass
