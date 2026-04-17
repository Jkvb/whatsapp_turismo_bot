import base64

from odoo import http
from odoo.http import request


class TourismRegistrationController(http.Controller):

    @http.route('/tourism/register', type='http', auth='public', website=True)
    def tourism_register_form(self, **kwargs):
        categories = request.env['tourism.provider.category'].sudo().search([])
        return request.render('whatsapp_turismo_bot.tourism_register_template', {
            'categories': categories,
            'values': kwargs,
        })

    @http.route('/tourism/register/submit', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def tourism_register_submit(self, **post):
        vals = {
            'name': post.get('commercial_name') or post.get('responsible_name'),
            'commercial_name': post.get('commercial_name'),
            'responsible_name': post.get('responsible_name'),
            'category_id': int(post['category_id']) if post.get('category_id') else False,
            'phone': post.get('phone'),
            'mobile': post.get('phone'),
            'whatsapp_number': post.get('whatsapp_number') or post.get('phone'),
            'email': post.get('email'),
            'description': post.get('description'),
            'location_text': post.get('location_text'),
        }

        profile_image = post.get('profile_image')
        if profile_image and getattr(profile_image, 'read', None):
            vals['profile_image_1920'] = base64.b64encode(profile_image.read())

        cover_image = post.get('cover_image')
        if cover_image and getattr(cover_image, 'read', None):
            vals['cover_image'] = base64.b64encode(cover_image.read())

        request.env['tourism.onboarding.service'].sudo().create_or_update_provider(vals, source='web')

        return request.render('whatsapp_turismo_bot.tourism_register_success_template')
