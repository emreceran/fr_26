# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import hashlib
import re


class SahaApi(http.Controller):

    # -------------------------------------------------------------------------
    # YARDIMCI FONKSİYON (Excel Scripti ile BİREBİR AYNI)
    # -------------------------------------------------------------------------
    def _clean_and_hash(self, phone):
        """
        1. Sadece rakamları bırakır.
        2. Baştaki '0' varsa siler (Örn: 0555 -> 555).
        3. Baştaki '90' varsa siler (Örn: 90555 -> 555).
        4. Hashler.
        """
        if not phone:
            return None

        # 1. Adım: Sadece rakamları al
        clean_str = re.sub(r'\D', '', str(phone))

        # 2. Adım: Baştaki '90' ülke kodunu sil (Türkiye standardı)
        if clean_str.startswith('90') and len(clean_str) > 10:
            clean_str = clean_str[2:]

        # 3. Adım: Baştaki '0'ı sil
        if clean_str.startswith('0'):
            clean_str = clean_str[1:]

        # Boş kaldıysa dön
        if not clean_str:
            return None

        # 4. Adım: Hashle
        return hashlib.sha256(clean_str.encode('utf-8')).hexdigest()
    # -------------------------------------------------------------------------
    # 1. LOGIN (GİRİŞ)
    # -------------------------------------------------------------------------
    @http.route('/api/login', type='json', auth='public', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        db = kwargs.get("db")
        login = kwargs.get("login")
        password = kwargs.get("password")
        try:
            my_credentials = {
                'login': login,
                'password': password,
                'type': 'password'
            }
            # Odoo session authentication
            uid = request.session.authenticate(db, my_credentials)

            if uid:
                return {
                    'status': 'success',
                    'session_id': request.session.sid,
                    'user_id': uid,
                    'message': 'Giris Basarili'
                }
        except Exception as e:
            # Hata detayını güvenlik için gizleyebilirsin, loga yazdırıyoruz
            print(f"Login Error: {e}")
            return {'status': 'error', 'message': 'Giris islemi basarisiz.'}

        return {'status': 'error', 'message': 'Kullanici adi veya sifre hatali.'}

    # -------------------------------------------------------------------------
    # 2. REHBER SORGULA (Telefon Listesi Gelir -> Sunucu Hashler -> Arar)
    # -------------------------------------------------------------------------
    @http.route('/api/rehber_sorgula', type='json', auth='user', methods=['POST'], csrf=False)
    def rehber_sorgula(self, **kwargs):
        telefon_listesi = kwargs.get("telefon_listesi")

        # Input Validasyon
        if not telefon_listesi or not isinstance(telefon_listesi, list):
            return {'status': 'error', 'message': 'Telefon listesi gonderilmedi.'}

        # 1. Gelen listeyi temizleyip Hash Listesine çevir
        aranacak_hashler = []
        for tel in telefon_listesi:
            hashed_val = self._clean_and_hash(tel)
            if hashed_val:
                aranacak_hashler.append(hashed_val)

        # Eğer geçerli hiç numara yoksa boş dön
        if not aranacak_hashler:
            return {'status': 'success', 'count': 0, 'data': []}

        # 2. Veritabanında 'phone_hash' alanında arama yap
        # NOT: 'phone_hash' alanı res.partner modeline eklediğimiz Custom Field'dır.
        domain = [('phone_hash', 'in', aranacak_hashler)]

        fields_to_read = [
            'id',
            'name',
            'phone_hash',  # Eşleştirme için geri dönüyoruz
            'taraf',
            'sicil_no',
            'kimlik_no',
            'kurum_adi',
            'bolge_adi',
            'sorumlu_id'
        ]

        try:
            contacts = request.env['res.partner'].search_read(domain, fields_to_read)
        except ValueError as e:
            # Eğer 'phone_hash' alanı henüz eklenmediyse bu hatayı verir
            return {'status': 'error', 'message': 'Sunucu hatasi: phone_hash alani bulunamadi.'}

        # 3. Sonuçları hazırla
        bulunanlar = []
        for c in contacts:
            bulunanlar.append({
                'id': c['id'],
                'name': c['name'],
                'hash': c['phone_hash'],
                'taraf': c['taraf'] or False,
                'sicil_no': c['sicil_no'] or "",
                'kimlik_no': c['kimlik_no'] or "",
                'kurum': c['kurum_adi'] or "",
                'bolge': c['bolge_adi'] or "",
                'sorumlu': c['sorumlu_id'][1] if c['sorumlu_id'] else ""  # (ID, "İsim") formatından ismi al
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
            # ID kontrolü
            if not customer_id:
                return {'status': 'error', 'message': 'Musteri ID eksik.'}

            partner = request.env['res.partner'].browse(int(customer_id))
            if not partner.exists():
                return {'status': 'error', 'message': 'Musteri bulunamadi'}

            # Renk güvenliği
            gecerli_renkler = ['kirmizi', 'mavi', 'yesil', 'beyaz']
            if renk not in gecerli_renkler:
                return {'status': 'error', 'message': 'Gecersiz renk kodu.'}

            # Yazma işlemi
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