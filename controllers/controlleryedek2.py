# -*- coding: utf-8 -*-
import hashlib
from odoo import http
from odoo.http import request


class SahaApi(http.Controller):

    # -------------------------------------------------------------------------
    # YARDIMCI FONKSİYON: HASH HESAPLAMA
    # -------------------------------------------------------------------------
    def _compute_phone_hash(self, phone):
        """
        Gelen telefon numarasını temizler (sadece rakam) ve SHA-256 hashini döndürür.
        Örnek: "+90 (555) 123 45 67" -> "905551234567" -> HASH
        """
        if not phone:
            return None

        # 1. Stringe çevir ve float (.0) temizliği yap
        val = str(phone)
        if val.endswith('.0'):
            val = val[:-2]

        # 2. Sadece rakamları bırak (Boşluk, +, parantez silinir)
        clean_phone = "".join(filter(str.isdigit, val))

        if not clean_phone:
            return None

        # 3. Hashle (SHA-256)
        return hashlib.sha256(clean_phone.encode('utf-8')).hexdigest()

    # -------------------------------------------------------------------------
    # 1. LOGIN (GİRİŞ)
    # -------------------------------------------------------------------------
    @http.route('/api/login', type='json', auth='public', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        db = kwargs.get("db")
        login = kwargs.get("login")
        password = kwargs.get("password")
        # print(db, login, password) # Log kirliliği yapmaması için yorum satırı yaptım
        try:
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
    # 2. REHBER SORGULA (HASH KONTROLÜ İLE)
    # -------------------------------------------------------------------------
    @http.route('/api/rehber_sorgula', type='json', auth='user', methods=['POST'], csrf=False)
    def rehber_sorgula(self, **kwargs):
        telefon_listesi = kwargs.get("telefon_listesi")
        """
        Input: ["0555 123 45 67", "+90532..."] (Ham Numaralar)
        Process: Gelen numaralar hashlenir -> DB'deki 'mobile_hash' alanında aranır.
        Output: Eşleşen kayıtların detayları.
        """
        if not telefon_listesi or not isinstance(telefon_listesi, list):
            return {'status': 'error', 'message': 'Telefon listesi gonderilmedi.'}

        # 1. ADIM: Gelen listeyi hash listesine çevir
        aranacak_hashler = []
        for tel in telefon_listesi:
            hash_val = self._compute_phone_hash(tel)
            if hash_val:
                aranacak_hashler.append(hash_val)

        # Eğer geçerli hiç numara yoksa boş dön
        if not aranacak_hashler:
            return {'status': 'success', 'count': 0, 'data': []}

        # 2. ADIM: Domaini Hash alanına göre kur
        # Veritabanındaki alan adınızın 'mobile_hash' olduğunu varsayıyoruz.
        domain = [('mobile_hash', 'in', aranacak_hashler)]

        # İstemciye dönecek alanlar
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
            'sorumlu_id'
        ]

        # Veritabanından çek (sudo() ile yetki sorunlarını aşar)
        contacts = request.env['res.partner'].sudo().search_read(domain, fields_to_read)

        bulunanlar = []
        for c in contacts:
            bulunanlar.append({
                'id': c['id'],
                'name': c['name'],
                # Uygulama tarafında kullanıcı ismini gördüğünde numarasını da görmek isteyebilir.
                # Veritabanında numara açıksa döneriz, yoksa boş döner.
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

            # 2. Renk Güvenliği
            gecerli_renkler = ['kirmizi', 'mavi', 'yesil', 'beyaz']
            if renk not in gecerli_renkler:
                return {'status': 'error', 'message': 'Gecersiz renk kodu.'}

            # 3. YAZMA İŞLEMİ
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