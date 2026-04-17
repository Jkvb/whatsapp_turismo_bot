from odoo import api, fields, models


class TourismPost(models.Model):
    _name = 'tourism.post'
    _description = 'Publicaciones de prestadores turísticos'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'published_date desc, create_date desc'

    provider_id = fields.Many2one('tourism.provider', required=True, ondelete='cascade', tracking=True)
    author_partner_id = fields.Many2one('res.partner', required=True, default=lambda s: s.env.user.partner_id)
    title = fields.Char(required=True, tracking=True)
    content = fields.Text(required=True)
    image = fields.Image(max_width=1920, max_height=1920)
    state = fields.Selection(
        [('draft', 'Borrador'), ('published', 'Publicado'), ('archived', 'Archivado')],
        default='draft',
        tracking=True,
    )
    published_date = fields.Datetime()
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records.filtered(lambda r: r.state == 'published' and not r.published_date):
            rec.published_date = fields.Datetime.now()
        return records

    def action_publish(self):
        self.write({'state': 'published', 'published_date': fields.Datetime.now()})

    def action_archive(self):
        self.write({'state': 'archived'})
