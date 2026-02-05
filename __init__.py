from . import models
from . import controllers
# from . import wizard

def post_init_hook(env):
    """Modül yüklendikten sonra tüm partner kayıtlarının sicil_no_int değerini hesapla"""
    # Tüm res.partner kayıtlarını al ve compute field'ı tetikle
    partners = env['res.partner'].with_context(active_test=False).search([])
    # Compute field'ı tetiklemek için kayıtları zorla yeniden hesaplat
    partners._compute_sicil_no_int()
    # Veritabanına kaydet
    env.cr.commit()