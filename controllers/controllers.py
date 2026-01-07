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
        if not phone:
            return None
        clean_str = re.sub(r'\D', '', str(phone))
        if clean_str.startswith('90') and len(clean_str) > 10:
            clean_str = clean_str[2:]
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
    # 2. REHBER SORGULA
    # -------------------------------------------------------------------------
    @http.route('/api/rehber_sorgula', type='json', auth='user', methods=['POST'], csrf=False)
    def rehber_sorgula(self, **kwargs):
        telefon_listesi = kwargs.get("telefon_listesi")
        if not telefon_listesi or not isinstance(telefon_listesi, list):
            return {'status': 'error', 'message': 'Telefon listesi gonderilmedi.'}

        hash_map = {}
        aranacak_hashler = []

        for tel in telefon_listesi:
            hashed_val = self._clean_and_hash(tel)
            if hashed_val:
                aranacak_hashler.append(hashed_val)
                hash_map[hashed_val] = tel

        if not aranacak_hashler:
            return {'status': 'success', 'count': 0, 'data': []}

        domain = [('phone_hash', 'in', aranacak_hashler)]
        fields_to_read = [
            'id', 'name', 'phone_hash', 'taraf',
            'sicil_no', 'kimlik_no', 'kurum_adi',
            'bolge_adi', 'sorumlu_id', 'ozel_il_id',
            'rehberinde_olan_user_ids'
        ]

        try:
            # Partners recordset'ini alıyoruz
            partners = request.env['res.partner'].search(domain)
            current_user_id = request.env.user.id

            # M2M Güncelleme: Sadece listede olmayan kullanıcıyı ekle
            for partner in partners:
                if current_user_id not in partner.rehberinde_olan_user_ids.ids:
                    partner.write({
                        'rehberinde_olan_user_ids': [(4, current_user_id, 0)]
                    })

            # Güncel veriyi oku
            contacts = partners.read(fields_to_read)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

        bulunanlar = []
        for c in contacts:
            db_hash = c['phone_hash']
            orijinal_tel = hash_map.get(db_hash, "Bilinmiyor")
            bulunanlar.append({
                'id': c['id'],
                'name': c['name'],
                'telefon': orijinal_tel,
                'hash': db_hash,
                'taraf': c['taraf'] or False,
                'sicil_no': c['sicil_no'] or "",
                'kimlik_no': c['kimlik_no'] or "",
                'kurum': c['kurum_adi'] or "",
                'bolge': c['bolge_adi'] or "",
                'sorumlu': c['sorumlu_id'][1] if c['sorumlu_id'] else "",
                'sehir': c['ozel_il_id'] or ""
            })

        return {'status': 'success', 'count': len(bulunanlar), 'data': bulunanlar}

    # -------------------------------------------------------------------------
    # 3. ETİKETLE (YETKİ KONTROLLÜ)
    # -------------------------------------------------------------------------
    @http.route('/api/etiketle', type='json', auth='user', methods=['POST'], csrf=False)
    def etiketle(self, **kwargs):
        customer_id = kwargs.get("customer_id")
        renk = kwargs.get("renk")
        user = request.env.user

        try:
            partner = request.env['res.partner'].browse(int(customer_id))
            if not partner.exists():
                return {'status': 'error', 'message': 'Müşteri bulunamadı.'}

            # --- YETKİ KONTROLÜ ---
            # Eğer halihazırda bir taraf seçilmişse (boş değilse)
            if partner.taraf:
                # Kullanıcı 'Etiket Değiştirme' grubunda mı?
                # NOT: 'fr_26' kısmını manifest'teki modül adınla aynı olduğundan emin ol.
                if not user.has_group('fr_26.group_saha_etiket_degistirici'):
                    return {
                        'status': 'error',
                        'message': 'Bu müşteri zaten etiketlenmiş. Değiştirmek için yetkiniz yok.'
                    }

            # Taraf boşsa veya kullanıcı yetkiliyse güncelleme yap
            if renk in ['kirmizi', 'mavi', 'yesil', 'beyaz']:
                partner.write({
                    'taraf': renk,
                    'etiketleyen_id': user.id
                })
                return {'status': 'success', 'message': 'Guncellendi'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

        return {'status': 'error', 'message': 'Hatalı parametre veya renk.'}