# -*- coding: utf-8 -*-
import hashlib
from odoo import http
from odoo.http import request


class SahaApi(http.Controller):

    # -------------------------------------------------------------------------
    # YARDIMCI: AKILLI HASH ÜRETİCİ (HER İHTİMALİ DÜŞÜNÜR)
    # -------------------------------------------------------------------------
    def _get_hash_variants(self, phone):
        """
        Gelen bir numara için olası tüm varyasyonların hash'lerini döndürür.
        Örnek Girdi: "555 904 19 99"

        Üretilen Hashler:
        1. "5559041999"  (Saf hali)
        2. "05559041999" (Başında 0 olan hali - Türkiye Standartı)
        3. "905559041999" (Başında 90 olan hali)

        Böylece veritabanında numara nasıl kayıtlı olursa olsun (0'lı veya 0'sız)
        eşleşme yakalanır.
        """
        if not phone:
            return []

        # 1. Temizlik: Sadece rakamları bırak
        val = str(phone)
        if val.endswith('.0'):
            val = val[:-2]

        clean_phone = "".join(filter(str.isdigit, val))

        if not clean_phone:
            return []

        # 2. Varyasyonları Üret
        variations = set()  # Aynıları eklememek için set kullanıyoruz

        # A) Olduğu gibi (Temizlenmiş hali)
        variations.add(clean_phone)

        # B) Eğer 10 haneli ise (555...) -> Başına 0 ekle (0555...)
        if len(clean_phone) == 10:
            variations.add("0" + clean_phone)
            variations.add("90" + clean_phone)

        # C) Eğer 11 haneli ve 0 ile başlıyorsa (0555...) -> 0'ı at (555...)
        if len(clean_phone) == 11 and clean_phone.startswith("0"):
            variations.add(clean_phone[1:])  # 555...
            variations.add("9" + clean_phone)  # 90555... (0 yerine 90 koyduk gibi düşünme, pratik ekleme)

        # D) Eğer 12 haneli ve 90 ile başlıyorsa (90555...) -> 90'ı at
        if len(clean_phone) == 12 and clean_phone.startswith("90"):
            variations.add(clean_phone[2:])  # 555...
            variations.add("0" + clean_phone[2:])  # 0555...

        # 3. Tüm varyasyonların Hash'lerini hesapla
        hash_list = []
        for v in variations:
            hash_val = hashlib.sha256(v.encode('utf-8')).hexdigest()
            hash_list.append(hash_val)

        return hash_list

    # -------------------------------------------------------------------------
    # 1. LOGIN
    # -------------------------------------------------------------------------
    @http.route('/api/login', type='json', auth='public', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        db = kwargs.get("db")
        login = kwargs.get("login")
        password = kwargs.get("password")
        try:
            uid = request.session.authenticate(db, {'login': login, 'password': password, 'type': 'password'})
            if uid:
                return {'status': 'success', 'session_id': request.session.sid, 'user_id': uid,
                        'message': 'Giris Basarili'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        return {'status': 'error', 'message': 'Kullanici adi veya sifre hatali.'}

    # -------------------------------------------------------------------------
    # 2. REHBER SORGULA (GARANTİ EŞLEŞME)
    # -------------------------------------------------------------------------
    @http.route('/api/rehber_sorgula', type='json', auth='user', methods=['POST'], csrf=False)
    def rehber_sorgula(self, **kwargs):
        telefon_listesi = kwargs.get("telefon_listesi")

        if not telefon_listesi or not isinstance(telefon_listesi, list):
            return {'status': 'error', 'message': 'Telefon listesi gonderilmedi.'}

        # 1. ADIM: Gelen her numara için TÜM HASH VARYASYONLARINI listeye ekle
        # Gelen: ["5559041999"]
        # Aranan: [HASH(5559041999), HASH(05559041999), HASH(905559041999)]
        aranacak_hashler = []
        for tel in telefon_listesi:
            variants = self._get_hash_variants(tel)
            aranacak_hashler.extend(variants)

        if not aranacak_hashler:
            return {'status': 'success', 'count': 0, 'data': []}

        # 2. ADIM: Veritabanında ara
        # Listeyi set(list(...)) yaparak tekrar eden hashleri temizleyebiliriz (performans için)
        aranacak_hashler = list(set(aranacak_hashler))

        domain = [('mobile_hash', 'in', aranacak_hashler)]
        fields_to_read = ['id', 'name', 'mobile', 'phone', 'taraf', 'sicil_no', 'kimlik_no', 'kurum_adi', 'bolge_adi',
                          'sorumlu_id']

        contacts = request.env['res.partner'].sudo().search_read(domain, fields_to_read)

        bulunanlar = []
        for c in contacts:
            bulunanlar.append({
                'id': c['id'],
                'name': c['name'],
                # Uygulama numaranın açık halini görmek isteyebilir (izin varsa)
                'telefon': c['mobile'] or c['phone'] or "",
                'taraf': c['taraf'] or False,
                'sicil_no': c['sicil_no'] or "",
                'kimlik_no': c['kimlik_no'] or "",
                'kurum': c['kurum_adi'] or "",
                'bolge': c['bolge_adi'] or "",
                'sorumlu': c['sorumlu_id'][1] if c['sorumlu_id'] else ""
            })

        return {
            'status': 'success',
            'count': len(bulunanlar),
            'data': bulunanlar
        }

    # -------------------------------------------------------------------------
    # 3. ETİKETLE
    # -------------------------------------------------------------------------
    @http.route('/api/etiketle', type='json', auth='user', methods=['POST'], csrf=False)
    def etiketle(self, **kwargs):
        customer_id = kwargs.get("customer_id")
        renk = kwargs.get("renk")
        try:
            partner = request.env['res.partner'].browse(int(customer_id))
            if not partner.exists():
                return {'status': 'error', 'message': 'Musteri bulunamadi'}

            if renk not in ['kirmizi', 'mavi', 'yesil', 'beyaz']:
                return {'status': 'error', 'message': 'Gecersiz renk kodu.'}

            partner.write({'taraf': renk, 'etiketleyen_id': request.env.user.id})

            return {'status': 'success', 'message': 'Guncellendi', 'yeni_renk': renk,
                    'etiketleyen': request.env.user.name}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}