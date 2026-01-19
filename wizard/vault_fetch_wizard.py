import requests
from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import UserError


class VaultFetchWizard(models.TransientModel):
    _name = 'vault.fetch.wizard'
    _description = 'Kasa Veri Sorgulama'

    vault_password = fields.Char(string='Oturum Şifresi', password=True)
    result_text = fields.Text(string='Sonuçlar', readonly=True)

    # Odoo 18 için compute alanın tanımı
    is_session_authenticated = fields.Boolean(compute='_compute_session_auth')

    @api.depends_context('uid')
    def _compute_session_auth(self):
        # Oturum bilgisini çek
        is_auth = request.session.get('vault_authenticated', False)
        for record in self:
            record.is_session_authenticated = is_auth

    def action_fetch_names(self):
        # 1. Oturum Kontrolü
        if not request.session.get('vault_authenticated', False):
            correct_pass = self.env['ir.config_parameter'].sudo().get_param('saha.vault_password')
            if not self.vault_password or self.vault_password != correct_pass:
                raise UserError("Şifre Yanlış!")

            # Oturumu doğrula ve kaydet
            request.session['vault_authenticated'] = True
            request.session.modified = True

        # 2. API Sorgusu (8070 Portu)
        VAULT_URL = "http://localhost:8070/api/vault/get_name"
        VAULT_TOKEN = "GIZLI_KASA_ANAHTARI_2026_XYZ"

        active_ids = self.env.context.get('active_ids', [])
        partners = self.env['res.partner'].browse(active_ids)

        results = []
        for p in partners:
            if p.sicil_no:
                try:
                    r = requests.post(VAULT_URL, json={
                        "jsonrpc": "2.0",
                        "params": {"api_token": VAULT_TOKEN, "sicil_no": p.sicil_no}
                    }, timeout=5).json()
                    res = r.get('result', {})
                    if res.get('status') == 'success':
                        results.append(f"{p.sicil_no}: {res.get('name')}")
                    else:
                        results.append(f"{p.sicil_no}: Bulunamadı")
                except:
                    results.append(f"{p.sicil_no}: Bağlantı Hatası")
            else:
                results.append(f"ID {p.id}: Sicil No Boş")

        self.result_text = "\n".join(results)

        # Ekranı yenile
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vault.fetch.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }