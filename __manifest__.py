{
    'name': "Saha Operasyon",
    'summary': "Sadeleştirilmiş Müşteri Kartı ve Saha Takibi",
    'description': "Gereksiz alanlar gizlendi, saha analizleri ana sayfaya alındı.",
    'author': "Siz",
    'version': '1.0',
    'depends': ['base', 'contacts', 'web', 'base_setup'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        # 'wizard/vault_fetch_wizard_view.xml',
        'views/views.xml',
        'views/res_config_settings_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}