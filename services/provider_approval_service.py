from odoo import _, fields, models


class ProviderApprovalService(models.AbstractModel):
    _name = 'provider.approval.service'
    _description = 'Aprobación/rechazo de prestadores'

    def _portal_group(self):
        return self.env.ref('base.group_portal')

    def _tourism_portal_group(self):
        return self.env.ref('whatsapp_turismo_bot.group_tourism_portal_user')

    def _create_portal_user(self, provider):
        partner = provider.partner_id or self.env['res.partner'].sudo().create({
            'name': provider.responsible_name or provider.commercial_name or provider.name,
            'email': provider.email,
            'phone': provider.phone,
            'mobile': provider.whatsapp_number,
        })
        existing_user = self.env['res.users'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if existing_user:
            user = existing_user
        else:
            login = provider.email or provider.whatsapp_number or f'provider_{provider.id}'
            user = self.env['res.users'].sudo().create({
                'name': partner.name,
                'login': login,
                'partner_id': partner.id,
                'email': provider.email,
                'groups_id': [(6, 0, [self._portal_group().id, self._tourism_portal_group().id])],
            })
        return user

    def approve(self, provider):
        user = provider.portal_user_id or self._create_portal_user(provider)
        provider.sudo().write({
            'approval_state': 'approved',
            'portal_user_id': user.id,
            'approval_notes': False,
            'publication_state': 'published' if provider.is_published else 'unpublished',
        })
        if provider.whatsapp_number:
            self.env['whatsapp.service'].sudo().send_text(
                provider.whatsapp_number,
                _('Tu perfil turístico fue aprobado. Ya puedes ingresar al portal.'),
            )

    def reject(self, provider, notes=None):
        provider.sudo().write({
            'approval_state': 'rejected',
            'approval_notes': notes or _('Registro rechazado por revisión interna.'),
            'last_profile_update_request_date': fields.Datetime.now(),
        })
        if provider.whatsapp_number:
            self.env['whatsapp.service'].sudo().send_text(
                provider.whatsapp_number,
                _('Tu solicitud fue rechazada. Revisa observaciones y vuelve a enviarla.'),
            )
