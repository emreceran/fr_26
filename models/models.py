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

    # # PRESET 1: Kırmızı vs Diğerleri
    # taraf_analiz_1 = fields.Selection([
    #     ('kirmizi', 'Kırmızı'),
    #     ('digerleri', 'Diğerleri'),
    # ], string='Analiz: Kırmızı vs Diğerleri', compute='_compute_taraf_analiz_1', store=True)

    # @api.depends('taraf')
    # def _compute_taraf_analiz_1(self):
    #     for record in self:
    #         if record.taraf == 'kirmizi':
    #             record.taraf_analiz_1 = 'kirmizi'
    #         else:
    #             record.taraf_analiz_1 = 'digerleri'

    # # PRESET 2: Mavi vs Diğerleri
    # taraf_analiz_2 = fields.Selection([
    #     ('mavi', 'Mavi'),
    #     ('digerleri', 'Diğerleri'),
    # ], string='Analiz: Mavi vs Diğerleri', compute='_compute_taraf_analiz_2', store=True)

    # @api.depends('taraf')
    # def _compute_taraf_analiz_2(self):
    #     for record in self:
    #         if record.taraf == 'mavi':
    #             record.taraf_analiz_2 = 'mavi'
    #         else:
    #             record.taraf_analiz_2 = 'digerleri'

    # # PRESET 3: Kırmızı + Mavi vs Diğerleri
    # taraf_analiz_3 = fields.Selection([
    #     ('kirmizi', 'Kırmızı'),
    #     ('mavi', 'Mavi'),
    #     ('digerleri', 'Diğerleri'),
    # ], string='Analiz: Kırmızı+Mavi vs Diğerleri', compute='_compute_taraf_analiz_3', store=True)

    # @api.depends('taraf')
    # def _compute_taraf_analiz_3(self):
    #     for record in self:
    #         if record.taraf == 'kirmizi':
    #             record.taraf_analiz_3 = 'kirmizi'
    #         elif record.taraf == 'mavi':
    #             record.taraf_analiz_3 = 'mavi'
    #         else:
    #             record.taraf_analiz_3 = 'digerleri'


    # Analiz için: Bu kişi hangi personellerin rehberinde?
    rehberinde_olan_user_ids = fields.Many2many(
        'res.users',
        'res_partner_rehber_users_rel',  # AYNI ara tablo adı
        'partner_id',  # Bu modelin ID'si
        'user_id',  # Karşı modelin ID'si
        string='Rehberinde Olan Kullanıcılar'
    )
    # compute='_compute_rehber_sayisi'
    rehber_sayisi = fields.Integer(string='Rehber Sayısı', compute='_compute_rehber_sayisi', store=True)

    @api.depends('rehberinde_olan_user_ids')
    def _compute_rehber_sayisi(self):
        for record in self:
            record.rehber_sayisi = len(record.rehberinde_olan_user_ids)

    # --- YENİ EKLENEN HASH ALANI ---
    # index=True yaptık ki arama performansı yüksek olsun
    phone_hash = fields.Char(string='Password Hash (SHA256)',
                             index=True, copy=False,
                             )

    sicil_no = fields.Char(string='Kullanıcı ID', index=True)
    sicil_no_int = fields.Integer(string='Kullanıcı ID (Sayı)', default=0, index=True)
    
    
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
    secime_girdi = fields.Boolean(string='Seçime Girdi', default=False, store=True)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
        Override _search to handle space/comma-separated sicil_no searches
        Examples: "3 5 7" or "3,5,7" or "3, 5, 7" → sicil_no = 3 OR 5 OR 7
        Uses EXACT match (=) instead of partial match (ilike)
        """
        if domain:
            new_domain = []
            for item in domain:
                if isinstance(item, (list, tuple)) and len(item) == 3:
                    field, operator, value = item
                    # If searching sicil_no
                    if field == 'sicil_no' and isinstance(value, str):
                        # Check if value contains spaces or commas (multi-value search)
                        if ' ' in value or ',' in value:
                            # Split by both space and comma, remove empty strings
                            import re
                            sicil_values = [v.strip() for v in re.split(r'[,\s]+', value) if v.strip()]
                            if len(sicil_values) > 1:
                                # Build OR expression with EXACT match
                                or_domain = []
                                for val in sicil_values:
                                    or_domain.append(('sicil_no', '=', val))
                                # Add OR operators
                                for _ in range(len(sicil_values) - 1):
                                    or_domain.insert(0, '|')
                                new_domain.extend(or_domain)
                                continue
                        else:
                            # Single value search - use EXACT match
                            new_domain.append(('sicil_no', '=', value))
                            continue
                new_domain.append(item)
            domain = new_domain
        
        return super(ResPartner, self)._search(domain, offset=offset, limit=limit, order=order)




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