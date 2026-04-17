from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    tourism_provider_ids = fields.One2many('tourism.provider', 'portal_user_id', string='Prestadores turísticos')
