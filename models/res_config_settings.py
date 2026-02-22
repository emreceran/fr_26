from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    etiketleme_aktif = fields.Boolean(
        string='Etiketleme Aktif',
        default=True,
        config_parameter='fr_26.etiketleme_aktif',
        help='Etiketleme işlemini aktif veya pasif hale getirir'
    )
