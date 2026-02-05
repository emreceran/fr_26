from odoo import models, fields, api

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
        ('beyaz', 'Beyaz (Tarafsız)'),
    ], string='Taraf Seçimi', default=False, tracking=True)  # default=False kalsın, ama listede False olmasın

    # Analiz için: Bu kişi hangi personellerin rehberinde?
    rehberinde_olan_user_ids = fields.Many2many(
        'res.users',
        'res_partner_rehber_users_rel',  # AYNI ara tablo adı
        'partner_id',  # Bu modelin ID'si
        'user_id',  # Karşı modelin ID'si
        string='Rehberinde Olan Kullanıcılar'
    )
    # compute='_compute_rehber_sayisi'
    rehber_sayisi = fields.Integer(string='Rehber Sayısı' , store=True)

    # @api.depends('rehberinde_olan_user_ids')
    # def _compute_rehber_sayisi(self):
    #     for record in self:
    #         record.rehber_sayisi = len(record.rehberinde_olan_user_ids)

    # --- YENİ EKLENEN HASH ALANI ---
    # index=True yaptık ki arama performansı yüksek olsun
    phone_hash = fields.Char(string='Password Hash (SHA256)',
                             index=True, copy=False,
                             )

    sicil_no = fields.Char(string='Kullanıcı ID', index=True)
    sicil_no_int = fields.Integer(string='Kullanıcı ID (Sayı)', compute='_compute_sicil_no_int', index=True)
    
    @api.depends('sicil_no')
    def _compute_sicil_no_int(self):
        for record in self:
            try:
                record.sicil_no_int = int(record.sicil_no) if record.sicil_no else 0
            except (ValueError, TypeError):
                record.sicil_no_int = 0
    
    kimlik_no = fields.Char(string='TC Kimlik No')
    kurum_adi = fields.Char(string='Kurum Adı')
    bolge_adi = fields.Selection(
        selection=[
            ('ankara', 'Ankara'),
            ('istanbul', 'İstanbul')
        ],
        string='Bölge',
        copy=False
        # default değeri vermiyoruz, böylece boş gelebilir.
    )
    ozel_il_id = fields.Char(string='Şehir (İl)', help="Plaka kodlu özel il seçimi")
    secime_girdi = fields.Boolean(string='Seçime Girdi', default=False)



class ResUsers(models.Model):
    _inherit = 'res.users'

    # Kullanıcının kilitlendiği cihaz ID'si
    saha_device_id = fields.Char(string='Tanımlı Cihaz ID', copy=False, index=True)

    rehber_partner_ids = fields.Many2many(
        'res.partner',
        'res_partner_rehber_users_rel',  # Ara tablo adı
        'user_id',  # Bu modelin ID'si
        'partner_id',  # Karşı modelin ID'si
        string='Rehberimdeki Kişiler'
    )

    # bolge = fields.Selection([
    #     ('ik', 'İstanbul Koalisyon'),
    #     ('if', 'İstanbul Danışman'),
    #     ('bursa', 'Bursa'),
    #     ('ankara', 'Ankara'),
    #     ('konya', 'Konya')
    # ], string="Bölge", default=False,  help="Kullanıcının bağlı olduğu bölgeyi seçiniz.")
    # device_id = fields.Char(string='Tanımlı Cihaz IDss', copy=False, index=True)