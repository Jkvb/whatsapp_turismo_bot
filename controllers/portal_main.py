import base64

from odoo import http
from odoo.http import request


class TourismPortalController(http.Controller):

    def _current_provider(self):
        return request.env['tourism.provider'].sudo().search([('portal_user_id', '=', request.env.user.id)], limit=1)

    @http.route('/my/tourism/profile', type='http', auth='user', website=True)
    def my_tourism_profile(self, **kwargs):
        provider = self._current_provider()
        return request.render('whatsapp_turismo_bot.tourism_my_profile_template', {
            'provider': provider,
            'status_message': kwargs.get('status_message'),
        })

    @http.route('/my/tourism/profile/save', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def my_tourism_profile_save(self, **post):
        provider = self._current_provider()
        if not provider or not provider.can_edit_from_portal():
            return request.not_found()

        vals = {
            'commercial_name': post.get('commercial_name'),
            'responsible_name': post.get('responsible_name'),
            'description': post.get('description'),
            'location_text': post.get('location_text'),
            'website': post.get('website'),
            'facebook_url': post.get('facebook_url'),
            'instagram_url': post.get('instagram_url'),
            'tiktok_url': post.get('tiktok_url'),
            'last_profile_update_request_date': False,
        }

        profile_image = post.get('profile_image')
        if profile_image and getattr(profile_image, 'read', None):
            vals['profile_image_1920'] = base64.b64encode(profile_image.read())

        cover_image = post.get('cover_image')
        if cover_image and getattr(cover_image, 'read', None):
            vals['cover_image'] = base64.b64encode(cover_image.read())

        provider.sudo().write(vals)
        return request.redirect('/my/tourism/profile?status_message=updated')

    @http.route('/my/tourism/posts', type='http', auth='user', website=True)
    def my_tourism_posts(self, **kwargs):
        provider = self._current_provider()
        posts = request.env['tourism.post'].sudo().search([('provider_id', '=', provider.id)]) if provider else []
        return request.render('whatsapp_turismo_bot.tourism_my_posts_template', {
            'provider': provider,
            'posts': posts,
            'status_message': kwargs.get('status_message'),
        })

    @http.route('/my/tourism/posts/create', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def create_my_tourism_post(self, **post):
        provider = self._current_provider()
        if not provider or provider.approval_state != 'approved':
            return request.not_found()

        vals = {
            'provider_id': provider.id,
            'author_partner_id': request.env.user.partner_id.id,
            'title': post.get('title'),
            'content': post.get('content'),
            'state': 'published' if post.get('publish_now') else 'draft',
        }
        post_image = post.get('image')
        if post_image and getattr(post_image, 'read', None):
            vals['image'] = base64.b64encode(post_image.read())

        request.env['tourism.post'].sudo().create(vals)
        return request.redirect('/my/tourism/posts?status_message=created')

    @http.route('/tourism/feed', type='http', auth='public', website=True)
    def tourism_feed(self):
        posts = request.env['tourism.post'].sudo().search([
            ('state', '=', 'published'),
            ('provider_id.approval_state', '=', 'approved'),
        ], limit=50)
        return request.render('whatsapp_turismo_bot.tourism_feed_template', {'posts': posts})

    @http.route('/tourism/provider/<int:provider_id>', type='http', auth='public', website=True)
    def tourism_provider_public(self, provider_id):
        provider = request.env['tourism.provider'].sudo().browse(provider_id)
        if not provider.exists() or provider.approval_state != 'approved':
            return request.not_found()
        posts = request.env['tourism.post'].sudo().search([
            ('provider_id', '=', provider.id),
            ('state', '=', 'published'),
        ])
        return request.render('whatsapp_turismo_bot.tourism_provider_public_template', {
            'provider': provider,
            'posts': posts,
        })
