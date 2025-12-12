# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SahaApi(http.Controller):

    # -------------------------------------------------------------------------
    # 1. LOGIN (GİRİŞ)
    # -------------------------------------------------------------------------
    @http.route('/api/login', type='json', auth='public', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        db = kwargs.get("db")
        login = kwargs.get("login")
        password = kwargs.get("password")
        print(db)
        print(login)
        print(password)
        try:
            # Odoo standart login yapısı yerine, senin sisteminin istediği
            # 'credential' sözlük yapısını kullanıyoruz.
            my_credentials = {
                'login': login,
                'password': password,
                'type': 'password'
            }

            # Doğrulama işlemi
            uid = request.session.authenticate(db, my_credentials)

            if uid:
                return {
                    'status': 'success',
                    'session_id': request.session.sid,
                    'user_id': uid,
                    'message': 'Giris Basarili'
                }
        except Exception as e:
            return {'status': 'error', 'message': f'Hata: {str(e)}'}

        return {'status': 'error', 'message': 'Kullanici adi veya sifre hatali.'}

    # -------------------------------------------------------------------------
    # 2. REHBER SORGULA (DETAYLI BİLGİ DÖNER)
    # -------------------------------------------------------------------------
    @http.route('/api/rehber_sorgula', type='json', auth='user', methods=['POST'], csrf=False)
    def rehber_sorgula(self, **kwargs):
        telefon_listesi = kwargs.get("telefon_listesi")
        """
        Input: ["0555...", "0532..."]
        Output: Eşleşen kayıtların TÜM detayları (Sicil, Kurum, Taraf vb.)
        """
        if not telefon_listesi or not isinstance(telefon_listesi, list):
            return {'status': 'error', 'message': 'Telefon listesi gonderilmedi.'}

        # Hem Cep (mobile) Hem Sabit (phone) alanında arama yap
        domain = ['|', ('mobile', 'in', telefon_listesi), ('phone', 'in', telefon_listesi)]

        # Mobil uygulamaya göndermek istediğimiz alanları seçiyoruz
        # GÜNCELLEME: Yeni eklediğimiz alanları buraya dahil ettim.
        fields_to_read = [
            'id',
            'name',
            'mobile',
            'phone',
            'taraf',
            'sicil_no',
            'kimlik_no',
            'kurum_adi',
            'bolge_adi',
            'sorumlu_id'  # Sorumlunun ID'si ve Adı (Odoo otomatik (ID, "Ad") şeklinde verir)
        ]

        # Veritabanından çek
        contacts = request.env['res.partner'].search_read(domain, fields_to_read)

        bulunanlar = []
        for c in contacts:
            bulunanlar.append({
                'id': c['id'],
                'name': c['name'],
                'telefon': c['mobile'] or c['phone'],
                'taraf': c['taraf'] or False,  # Renk kodu veya False
                'sicil_no': c['sicil_no'] or "",  # Boşsa boş string
                'kimlik_no': c['kimlik_no'] or "",
                'kurum': c['kurum_adi'] or "",
                'bolge': c['bolge_adi'] or "",
                'sorumlu': c['sorumlu_id'][1] if c['sorumlu_id'] else ""  # Sadece ismini alalım
            })

        return {
            'status': 'success',
            'count': len(bulunanlar),
            'data': bulunanlar
        }

    # -------------------------------------------------------------------------
    # 3. ETİKETLE (KİMİN YAPTIĞINI KAYDEDER)
    # -------------------------------------------------------------------------
    @http.route('/api/etiketle', type='json', auth='user', methods=['POST'], csrf=False)
    def etiketle(self, **kwargs):

        customer_id = kwargs.get("customer_id")
        renk = kwargs.get("renk")
        try:
            # 1. Müşteriyi bul
            partner = request.env['res.partner'].browse(int(customer_id))
            if not partner.exists():
                return {'status': 'error', 'message': 'Musteri bulunamadi'}

            # 2. Renk Güvenliği (Beyaz dahil)
            gecerli_renkler = ['kirmizi', 'mavi', 'yesil', 'beyaz']
            if renk not in gecerli_renkler:
                return {'status': 'error', 'message': 'Gecersiz renk kodu.'}

            # 3. YAZMA İŞLEMİ
            # 'request.env.user.id' -> API'ye o an bağlı olan (etiketleyen) kullanıcının ID'sidir.
            partner.write({
                'taraf': renk,
                'etiketleyen_id': request.env.user.id
            })

            return {
                'status': 'success',
                'message': 'Guncellendi',
                'yeni_renk': renk,
                'etiketleyen': request.env.user.name
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}