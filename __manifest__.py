{
    'name': "Saha Operasyon",
    'summary': "Sadeleştirilmiş Müşteri Kartı ve Saha Takibi",
    'description': "Gereksiz alanlar gizlendi, saha analizleri ana sayfaya alındı.",
    'author': "Siz",
    'version': '1.0',
    'depends': ['base', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable': True,
    'application': True,
}