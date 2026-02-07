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
    # 1. LOGIN (CİHAZ KONTROLLÜ + YETKİ DÖNEN VERSİYON)
    # -------------------------------------------------------------------------
    @http.route('/api/login', type='json', auth='public', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        db = kwargs.get("db")
        login = kwargs.get("login")
        password = kwargs.get("password")
        device_id = kwargs.get("device_id")

        if not device_id:
            return {'status': 'error', 'message': 'Cihaz ID bilgisi gönderilmedi.'}

        try:
            # Odoo 18 Kimlik Doğrulama
            auth_result = request.session.authenticate(db, {
                'login': login,
                'password': password,
                'type': 'password'
            })

            # Odoo 18 Singleton hatasını önlemek için uid kontrolü
            if isinstance(auth_result, dict):
                uid = auth_result.get('uid')
            else:
                uid = auth_result

            if uid:
                user = request.env['res.users'].sudo().browse(uid)

                # 1. Yetki Kontrolü (Grup ID: fr_26.group_saha_etiket_degistirici)
                # Kullanıcı bu gruba dahilse admin: true dönecek
                is_admin = user.has_group('fr_26.group_saha_etiket_degistirici')

                # 2. Cihaz ID Kontrolü
                if not user.saha_device_id:
                    # İlk giriş: Cihazı kilitle
                    user.write({'saha_device_id': device_id})
                    return {
                        'status': 'success',
                        'session_id': request.session.sid,
                        'user_id': uid,
                        'admin': is_admin,  # Yetki bilgisini dönüyoruz
                        'message': 'Cihaz başarıyla tanımlandı ve giriş yapıldı.'
                    }

                elif user.saha_device_id == device_id:
                    # Tanımlı cihaz
                    return {
                        'status': 'success',
                        'session_id': request.session.sid,
                        'user_id': uid,
                        'admin': is_admin,  # Yetki bilgisini dönüyoruz
                        'message': 'Giriş Başarılı'
                    }

                else:
                    # Farklı cihaz
                    request.session.logout()
                    return {
                        'status': 'error',
                        'message': 'Bu hesaba sadece tanımlı cihazınızdan giriş yapabilirsiniz.'
                    }

        except Exception as e:
            return {'status': 'error', 'message': 'Kullanıcı adı veya şifre hatalı.'}

        return {'status': 'error', 'message': 'Kullanıcı adı veya şifre hatalı.'}
    # # -------------------------------------------------------------------------
    # # 1. LOGIN
    # # -------------------------------------------------------------------------
    # @http.route('/api/login', type='json', auth='public', methods=['POST'], csrf=False)
    # def login(self, **kwargs):
    #     db = kwargs.get("db")
    #     login = kwargs.get("login")
    #     password = kwargs.get("password")
    #     try:
    #         uid = request.session.authenticate(db, {'login': login, 'password': password, 'type': 'password'})
    #         if uid:
    #             return {'status': 'success', 'session_id': request.session.sid, 'user_id': uid,
    #                     'message': 'Giris Basarili'}
    #     except Exception:
    #         pass
    #     return {'status': 'error', 'message': 'Kullanici adi veya sifre hatali.'}

    # -------------------------------------------------------------------------
    # 2. REHBER SORGULA: Bulunanları otomatik olarak rehbere ekler (Analiz Odaklı)
    # -------------------------------------------------------------------------
    @http.route('/api/rehber_sorgula', type='json', auth='user', methods=['POST'], csrf=False)
    def rehber_sorgula(self, **kwargs):
        telefon_listesi = kwargs.get("telefon_listesi")
        if not telefon_listesi or not isinstance(telefon_listesi, list):
            return {'status': 'error', 'message': 'Telefon listesi gönderilmedi.'}

        # Hash haritası çıkar
        hash_map = {}
        for tel in telefon_listesi:
            hashed_val = self._clean_and_hash(tel)
            if hashed_val:
                hash_map[hashed_val] = tel

        if not hash_map:
            return {'status': 'success', 'count': 0, 'data': []}

        try:
            user = request.env.user
            # sudo() kullanarak yetki bariyerlerini aşıyoruz
            partners = request.env['res.partner'].sudo().search([
                ('phone_hash', 'in', list(hash_map.keys()))
            ])

            # --- OTOMATİK EŞLEŞTİRME (REHBERE EKLEME) ---
            if partners:
                # Kullanıcının kendi kaydına yazma yetkisi olmasa bile sudo() ile ekliyoruz
                user.sudo().write({
                    'rehber_partner_ids': [(4, p.id) for p in partners]
                })

            # Alanları oku
            fields_to_read = [
                'id', 'name', 'phone_hash', 'taraf', 'sicil_no',
                'kimlik_no', 'kurum_adi', 'bolge_adi', 'sorumlu_id',
                'ozel_il_id', 'etiketleyen_id', 'secime_girdi'
            ]
            contacts = partners.read(fields_to_read)

            bulunanlar = []
            for c in contacts:
                db_hash = c['phone_hash']
                etiketleyen_id = c['etiketleyen_id'][0] if c['etiketleyen_id'] else False

                bulunanlar.append({
                    'id': c['id'],
                    'name': c['name'],
                    'telefon': hash_map.get(db_hash, "Bilinmiyor"),
                    'hash': db_hash,
                    'taraf': c['taraf'] or False,
                    'sicil_no': c['sicil_no'] or "",
                    'kimlik_no': c['kimlik_no'] or "",
                    'kurum': c['kurum_adi'] or "",
                    'bolge': c['bolge_adi'] or "",
                    'sorumlu': c['sorumlu_id'][1] if c['sorumlu_id'] else "",
                    'sehir': c['ozel_il_id'] or "",
                    'etiketleyen_ben_miyim': (etiketleyen_id == user.id),
                    'rehberimde_mi': True,  # Sorguda geldiği için artık rehberinde
                    'secime_girdi': c['secime_girdi'] or False
                })

            return {'status': 'success', 'count': len(bulunanlar), 'data': bulunanlar}

        except Exception as e:
            return {
                'status': 'error',
                'message': 'İşlem gerçekleştirilemedi. Lütfen daha sonra tekrar deneyiniz.'
            }

    # -------------------------------------------------------------------------
    # 3. ETİKETLE (YETKİ KONTROLLÜ)
    # -------------------------------------------------------------------------
    @http.route('/api/etiketle', type='json', auth='user', methods=['POST'], csrf=False)
    def etiketle(self, **kwargs):
        from datetime import datetime
        import pytz
        
        customer_id = kwargs.get("customer_id")
        renk = kwargs.get("renk")
        user = request.env.user

        # --- ZAMAN KONTROLÜ ---
        # Türkiye saat diliminde şu anki saati al
        tz = pytz.timezone('Europe/Istanbul')
        now = datetime.now(tz)
        current_time = now.time()
        
        # 15:30'dan sonra etiketlemeye izin verme
        cutoff_time = datetime.strptime("15:30", "%H:%M").time()
        if current_time > cutoff_time:
            return {
                'status': 'error',
                'message': 'Etiketleme zamanı geçti. Etiketleme işlemi saat 15:30\'a kadar yapılabilir.'
            }

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

            # --- DEĞER KONTROLÜ ---
            # Kabul ettiğimiz string değerler + None/False (sıfırlama için)
            gecerli_renkler = ['kirmizi', 'mavi', 'yesil', 'beyaz']

            if renk in gecerli_renkler or renk in [None, False]:
                # Eğer renk listede varsa onu yaz, yoksa (None/False ise) False yazarak alanı boşalt
                yazilacak_deger = renk if renk in gecerli_renkler else False

                partner.write({
                    'taraf': yazilacak_deger,
                    'etiketleyen_id': user.id
                })
                return {'status': 'success', 'message': 'Guncellendi'}
            else:
                return {'status': 'error', 'message': 'Hatalı renk parametresi.'}

        except Exception as e:
            return {
                'status': 'error',
                'message': 'İşlem gerçekleştirilemedi. Lütfen daha sonra tekrar deneyiniz.'
            }