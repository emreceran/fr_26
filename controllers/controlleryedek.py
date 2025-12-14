# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import hashlib
import re


class SahaApi(http.Controller):

    # -------------------------------------------------------------------------
    # YARDIMCI FONKSİYON
    # -------------------------------------------------------------------------
    def _clean_and_hash(self, phone):
        """
        Telefonu temizler ve hashler.
        """
        if not phone:
            return None

        clean_str = re.sub(r'\D', '', str(phone))

        # Başta 90 varsa sil
        if clean_str.startswith('90') and len(clean_str) > 10:
            clean_str = clean_str[2:]

        # Başta 0 varsa sil
        if clean_str.startswith('0'):
            clean_str = clean_str[1:]

        if not clean_str:
            return None

        return hashlib.sha256(clean_str.encode('utf-8')).hexdigest()

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
        except Exception:
            pass
        return {'status': 'error', 'message': 'Kullanici adi veya sifre hatali.'}

    # -------------------------------------------------------------------------
    # 2. REHBER SORGULA (ORİJİNAL NUMARA DÖNEN VERSİYON)
    # -------------------------------------------------------------------------
    @http.route('/api/rehber_sorgula', type='json', auth='user', methods=['POST'], csrf=False)
    def rehber_sorgula(self, **kwargs):
        print("\n\n--- REHBER SORGULA BAŞLADI (YENİ KOD) ---")  # <--- KODUN GÜNCELLENDİĞİNİ BURADAN ANLAYACAĞIZ

        telefon_listesi = kwargs.get("telefon_listesi")

        if not telefon_listesi or not isinstance(telefon_listesi, list):
            return {'status': 'error', 'message': 'Telefon listesi gonderilmedi.'}

        # 1. Hash Haritası Oluştur
        hash_map = {}
        aranacak_hashler = []

        for tel in telefon_listesi:
            hashed_val = self._clean_and_hash(tel)
            if hashed_val:
                aranacak_hashler.append(hashed_val)
                # Hash -> Orijinal Numara eşleşmesi
                hash_map[hashed_val] = tel

        print(f"DEBUG: Hesaplanan Hash Sayisi: {len(aranacak_hashler)}")

        if not aranacak_hashler:
            return {'status': 'success', 'count': 0, 'data': []}

        # 2. Veritabanında Ara
        domain = [('phone_hash', 'in', aranacak_hashler)]

        fields_to_read = [
            'id', 'name', 'phone_hash', 'taraf',
            'sicil_no', 'kimlik_no', 'kurum_adi',
            'bolge_adi', 'sorumlu_id', 'ozel_il_id'
        ]

        try:
            contacts = request.env['res.partner'].search_read(domain, fields_to_read)
        except ValueError:
            return {'status': 'error', 'message': 'phone_hash alani bulunamadi.'}

        # 3. Sonuçları Eşleştir
        bulunanlar = []
        for c in contacts:
            db_hash = c['phone_hash']

            # Hash haritasından orijinal numarayı çek
            orijinal_tel = hash_map.get(db_hash, "Bilinmiyor")

            # DEBUG: Eşleşme kontrolü
            # print(f"DEBUG: DB Hash: {db_hash[:10]}... -> Tel: {orijinal_tel}")

            bulunanlar.append({
                'id': c['id'],
                'name': c['name'],
                'telefon': orijinal_tel,  # <--- İŞTE BURASI: Orijinal numara burada
                'hash': db_hash,
                'taraf': c['taraf'] or False,
                'sicil_no': c['sicil_no'] or "",
                'kimlik_no': c['kimlik_no'] or "",
                'kurum': c['kurum_adi'] or "",
                'bolge': c['bolge_adi'] or "",
                'sorumlu': c['sorumlu_id'][1] if c['sorumlu_id'] else "",
                'sehir': c['ozel_il_id'] or ""
            })

        print("--- REHBER SORGULA BİTTİ ---\n\n")
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
            if partner.exists() and renk in ['kirmizi', 'mavi', 'yesil', 'beyaz']:
                partner.write({'taraf': renk, 'etiketleyen_id': request.env.user.id})
                return {'status': 'success', 'message': 'Guncellendi'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        return {'status': 'error', 'message': 'Hata'}