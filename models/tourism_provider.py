from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TourismProvider(models.Model):
    _inherit = 'tourism.provider'

    commercial_name = fields.Char(string='Nombre comercial')
    responsible_name = fields.Char(string='Responsable')
    whatsapp_number = fields.Char(string='WhatsApp')
    description = fields.Text()
    location_text = fields.Char(string='Ubicación')
    address = fields.Char()
    municipality = fields.Char()
    state_name = fields.Char(string='Departamento/Estado')
    country_id = fields.Many2one('res.country')
    profile_image_1920 = fields.Image(max_width=1920, max_height=1920)
    cover_image = fields.Image(max_width=1920, max_height=1920)
    website = fields.Char()
    facebook_url = fields.Char()
    instagram_url = fields.Char()
    tiktok_url = fields.Char()
    approval_state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('pending', 'En revisión'),
            ('approved', 'Aprobado'),
            ('rejected', 'Rechazado'),
        ],
        default='draft',
        tracking=True,
    )
    publication_state = fields.Selection(
        [
            ('unpublished', 'No publicado'),
            ('published', 'Publicado'),
            ('archived', 'Archivado'),
        ],
        default='unpublished',
        tracking=True,
    )
    portal_user_id = fields.Many2one('res.users', string='Usuario portal')
    onboarding_source = fields.Selection(
        [('whatsapp', 'WhatsApp'), ('web', 'Web'), ('internal', 'Interno')],
        default='internal',
        tracking=True,
    )
    approval_notes = fields.Text()
    is_published = fields.Boolean(default=False)
    last_profile_update_request_date = fields.Datetime()

    _sql_constraints = [
        ('provider_whatsapp_unique', 'unique(whatsapp_number)', 'El WhatsApp ya está registrado.'),
    ]

    @api.constrains('approval_state', 'portal_user_id')
    def _check_portal_user_for_approved(self):
        for rec in self:
            if rec.approval_state == 'approved' and not rec.portal_user_id:
                raise UserError(_('Un prestador aprobado debe tener usuario portal asociado.'))

    def action_approve_provider(self):
        self.ensure_one()
        self.env['provider.approval.service'].approve(self)

    def action_reject_provider(self):
        self.ensure_one()
        self.env['provider.approval.service'].reject(self, notes=self.approval_notes)

    def action_request_changes(self):
        self.ensure_one()
        self.write({
            'approval_state': 'draft',
            'last_profile_update_request_date': fields.Datetime.now(),
        })

    def can_edit_from_portal(self, user=None):
        user = user or self.env.user
        self.ensure_one()
        return self.approval_state == 'approved' and self.portal_user_id == user
