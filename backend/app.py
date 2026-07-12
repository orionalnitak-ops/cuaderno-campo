import logging
import os
import warnings

from flask import Flask, jsonify, request
from flask_cors import CORS
from db import init_db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# INIT DB (ejecutar siempre al importar — gunicorn + flask run)
# ─────────────────────────────────────────────
init_db()

# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
app = Flask(__name__, static_folder=frontend_dir, static_url_path='')

_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    _is_prod = os.environ.get('FLASK_ENV') == 'production' or bool(os.environ.get('DATABASE_URL'))
    if _is_prod:
        raise RuntimeError("SECRET_KEY no está configurada. Establece la variable de entorno SECRET_KEY en producción.")
    warnings.warn("SECRET_KEY no configurada — usando clave de desarrollo insegura. NO usar en producción.")
    _secret_key = 'cuaderno_campo_DEV_ONLY_not_for_production'
app.secret_key = _secret_key

_is_prod = os.environ.get('FLASK_ENV') == 'production' or bool(os.environ.get('DATABASE_URL'))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE']   = _is_prod  # solo HTTPS en producción

# CORS: en producción restringir a los orígenes del dominio real vía ALLOWED_ORIGINS
_allowed_origins = os.environ.get('ALLOWED_ORIGINS', 'http://127.0.0.1:5000,http://localhost:5000').split(',')
CORS(app, origins=_allowed_origins, supports_credentials=True)

# Rate limiting — usa Redis si está disponible (compartido entre workers), si no memory por worker
def _probe_redis(url):
    try:
        import redis as _r
        _r.from_url(url, socket_connect_timeout=2).ping()
        return True
    except Exception:
        return False

_redis_url = os.environ.get('REDIS_URL')
_limiter_storage = _redis_url if (_redis_url and _probe_redis(_redis_url)) else 'memory://'
if _redis_url and _limiter_storage == 'memory://':
    app.logger.warning("REDIS_URL configurada pero Redis no responde — rate limiting en memoria por worker")

# Límite de tamaño de upload: 4 MB (xlsx de parcelas no supera 1 MB en la práctica)
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024

# ─────────────────────────────────────────────
# EXTENSIONS — limiter + login_manager
# ─────────────────────────────────────────────
app.config['RATELIMIT_STORAGE_URI'] = _limiter_storage

from extensions import limiter, login_manager  # noqa: E402

limiter.init_app(app)
login_manager.init_app(app)

# ─────────────────────────────────────────────
# BLUEPRINTS
# ─────────────────────────────────────────────
from blueprints.auth import bp as auth_bp  # noqa: E402
from blueprints.admin import bp as admin_bp  # noqa: E402
from blueprints.explotacion import bp as explotacion_bp  # noqa: E402
from blueprints.parcelas import bp as parcelas_bp  # noqa: E402
from blueprints.tratamientos import bp as tratamientos_bp  # noqa: E402
from blueprints.fertilizacion import bp as fertilizacion_bp  # noqa: E402
from blueprints.labores import bp as labores_bp  # noqa: E402
from blueprints.equipos import bp as equipos_bp  # noqa: E402
from blueprints.compras import bp as compras_bp  # noqa: E402
from blueprints.sigpac import bp as sigpac_bp  # noqa: E402
from blueprints.nlp import bp as nlp_bp  # noqa: E402
from blueprints.imports_exports import bp as imports_exports_bp  # noqa: E402
from blueprints.aemet import bp as aemet_bp  # noqa: E402
from blueprints.stripe_bp import bp as stripe_bp  # noqa: E402
from blueprints.push import bp as push_bp  # noqa: E402
from blueprints.uhc import bp as uhc_bp  # noqa: E402
from blueprints.ia import bp as ia_bp  # noqa: E402

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(explotacion_bp)
app.register_blueprint(parcelas_bp)
app.register_blueprint(tratamientos_bp)
app.register_blueprint(fertilizacion_bp)
app.register_blueprint(labores_bp)
app.register_blueprint(equipos_bp)
app.register_blueprint(compras_bp)
app.register_blueprint(sigpac_bp)
app.register_blueprint(nlp_bp)
app.register_blueprint(imports_exports_bp)
app.register_blueprint(aemet_bp)
app.register_blueprint(stripe_bp)
app.register_blueprint(push_bp)
app.register_blueprint(uhc_bp)
app.register_blueprint(ia_bp)

# ─────────────────────────────────────────────
# STATIC SERVING
# ─────────────────────────────────────────────
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

@app.route('/pago-completado')
def serve_pago_completado():
    return app.send_static_file('index.html')

@app.route('/privacidad')
def serve_privacidad():
    return app.send_static_file('privacidad.html')

@app.route('/<path:path>')
def serve_static(path):
    if path.startswith('api/'):
        return jsonify({"error": "Not found"}), 404
    try:
        return app.send_static_file(path)
    except Exception:
        return app.send_static_file('index.html')


# ─────────────────────────────────────────────
# SECURITY HEADERS + PLAN GUARD
# ─────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options']        = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy']        = 'strict-origin-when-cross-origin'
    # CSP — subconjunto seguro. NO se restringen script/style/img/connect porque
    # la app carga React/Leaflet de unpkg, fuentes de Google, estilos inline y el
    # mapa SIGPAC trae tiles de servidores externos: un script-src/img-src mal
    # ajustado dejaría el mapa o la app en blanco. Estas 3 directivas sí son
    # seguras (la app no usa <base>, ni plugins <object>/<embed>, ni se embebe en
    # iframes) y aportan defensa real (anti-clickjacking, anti base-tag injection,
    # anti plugin-XSS). El CSP completo de script-src/style-src queda pendiente de
    # ajustar y probar en staging (enumerar hosts de tiles + fuentes + unpkg).
    response.headers['Content-Security-Policy'] = (
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    # CSP completo en modo Report-Only: NO bloquea nada (solo reporta violaciones
    # en la consola del navegador), así que es seguro desplegarlo sin poder probar.
    # Enumera los hosts reales que usa la app: unpkg (React/Leaflet), fuentes de
    # Google, los 3 WMS del mapa (SIGPAC-hubcloud, Red Natura IEPNB, PNOA IGN) y
    # Open-Meteo. Cuando se verifique en producción que no hay violaciones
    # inesperadas en consola, se puede: (1) endurecer script-src sustituyendo
    # 'unsafe-inline' por el hash del <script> de registro del SW, y (2) mover
    # esta política a la cabecera Content-Security-Policy (enforcing).
    response.headers['Content-Security-Policy-Report-Only'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https://sigpac-hubcloud.es https://geoserver.iepnb.es https://www.ign.es; "
        "connect-src 'self' https://api.open-meteo.com https://geocoding-api.open-meteo.com; "
        "worker-src 'self'; manifest-src 'self'; "
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    if _is_prod:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


_PLAN_EXEMPT_PREFIXES = ('/api/auth/', '/api/admin/', '/api/stripe/')

@app.before_request
def guard_active_plan():
    """Bloquea escrituras si el trial ha caducado o la suscripción ha expirado."""
    from flask_login import current_user
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    if any(request.path.startswith(p) for p in _PLAN_EXEMPT_PREFIXES):
        return
    if not current_user.is_authenticated:
        return
    if not current_user.plan_is_active():
        return jsonify({
            "error": "subscription_required",
            "plan": current_user.plan_label(),
        }), 403


# ─────────────────────────────────────────────
# SCHEDULER — alertas push cada 30 min
# Redis SETNX en el job garantiza ejecución única entre workers Gunicorn
# ─────────────────────────────────────────────
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from blueprints.push import job_check_push_alertas
    import atexit
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(job_check_push_alertas, 'interval', minutes=30, id='push_alertas')
    _scheduler.start()
    atexit.register(lambda: _scheduler.shutdown(wait=False))
except Exception as _sch_err:
    logger.warning('APScheduler no arrancó: %s', _sch_err)


# ─────────────────────────────────────────────
# BOOT
# ─────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)  # nosec B104 — necesario para Docker
