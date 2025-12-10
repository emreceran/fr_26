# -*- coding: utf-8 -*-
from odoo import models, fields

class SahaIl(models.Model):
    _name = 'saha.il'
    _description = 'İl ve Plaka Tanımları'
    _order = 'code' # Listelerken plaka sırasına göre gelsin
    _rec_name = 'name' # İlişkilerde (Many2one) görünecek isim

    name = fields.Char(string='İl Adı', required=True)
    code = fields.Char(string='Plaka Kodu', required=True)
    
    # Aynı plaka veya isimden 2 tane olmasın diye kısıtlama (Opsiyonel ama önerilir)
    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'Bu plaka kodu zaten mevcut!'),
        ('name_uniq', 'unique (name)', 'Bu il ismi zaten mevcut!'),
    ]

class ResPartner(models.Model):
    _inherit = 'res.partner'

    sorumlu_id = fields.Many2one('res.users', string='Sorumlu Personel', index=True)
    etiketleyen_id = fields.Many2one('res.users', string='Etiketleyen Personel', readonly=True)

    taraf = fields.Selection([
        ('kirmizi', 'Kırmızı'),
        ('mavi', 'Mavi'),
        ('yesil', 'Yeşil'),
        ('beyaz', 'Beyaz (Tarafsız)'), # Yeni seçeneğimiz
    ], string='Taraf Seçimi')

    sicil_no = fields.Char(string='Sicil No', index=True)
    kimlik_no = fields.Char(string='TC Kimlik No')
    kurum_adi = fields.Char(string='Kurum Adı')
    bolge_adi = fields.Char(string='Bölge') 
    ozel_il_id = fields.Many2one('saha.il', string='Şehir (İl)', help="Plaka kodlu özel il seçimi")