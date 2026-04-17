import base64

from odoo import models


class MediaService(models.AbstractModel):
    _name = 'tourism.media.service'
    _description = 'Normalización y almacenamiento de media'

    def save_whatsapp_image_to_provider(self, provider, media_id, field_name='profile_image_1920'):
        binary_data = self.env['whatsapp.service'].sudo().fetch_media_binary(media_id)
        # TODO: aplicar compresión/redimensionamiento con Pillow si se requiere optimización avanzada.
        provider.sudo().write({field_name: base64.b64encode(binary_data)})
        return True
