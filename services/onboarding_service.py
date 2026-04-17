from odoo import api, fields, models


class OnboardingService(models.AbstractModel):
    _name = 'tourism.onboarding.service'
    _description = 'Servicio central de onboarding web/WhatsApp'

    @api.model
    def _normalize_phone(self, phone):
        if not phone:
            return False
        cleaned = ''.join(ch for ch in phone if ch.isdigit() or ch == '+')
        if cleaned.startswith('00'):
            cleaned = '+' + cleaned[2:]
        return cleaned

    @api.model
    def _provider_domain(self, vals):
        domain = []
        if vals.get('whatsapp_number'):
            domain = [('whatsapp_number', '=', vals['whatsapp_number'])]
        elif vals.get('email'):
            domain = [('email', '=', vals['email'])]
        return domain

    @api.model
    def create_or_update_provider(self, vals, source='web'):
        provider_vals = dict(vals)
        provider_vals['onboarding_source'] = source
        provider_vals['approval_state'] = 'pending'
        provider_vals['phone'] = self._normalize_phone(provider_vals.get('phone'))
        provider_vals['mobile'] = self._normalize_phone(provider_vals.get('mobile'))
        provider_vals['whatsapp_number'] = self._normalize_phone(provider_vals.get('whatsapp_number'))

        domain = self._provider_domain(provider_vals)
        provider = self.env['tourism.provider'].sudo().search(domain, limit=1) if domain else False
        if provider:
            provider.sudo().write(provider_vals)
        else:
            provider = self.env['tourism.provider'].sudo().create(provider_vals)

        provider.sudo().write({
            'approval_state': 'pending',
            'last_profile_update_request_date': fields.Datetime.now(),
        })
        return provider
