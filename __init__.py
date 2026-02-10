from . import models
from . import controllers
# from . import wizard

def post_init_hook(env):
    """Bordo değerlerini temizle"""
    # Bordo değerlerini temizle
    partners_with_bordo = env['res.partner'].search([('taraf', '=', 'bordo')])
    if partners_with_bordo:
        partners_with_bordo.write({'taraf': False})
        print(f"Bordo değerine sahip {len(partners_with_bordo)} kayıt temizlendi.")