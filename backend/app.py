import logging
import os
import warnings

from flask import Flask, jsonify, request
from flask_cors import CORS
from db import get_db, init_db, one

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
from blueprints.auth import bp as auth_bp
from blueprints.admin import bp as admin_bp
from blueprints.explotacion import bp as explotacion_bp
from blueprints.parcelas import bp as parcelas_bp
from blueprints.tratamientos import bp as tratamientos_bp
from blueprints.fertilizacion import bp as fertilizacion_bp
from blueprints.labores import bp as labores_bp
from blueprints.equipos import bp as equipos_bp
from blueprints.compras import bp as compras_bp
from blueprints.sigpac import bp as sigpac_bp
from blueprints.nlp import bp as nlp_bp
from blueprints.imports_exports import bp as imports_exports_bp
from blueprints.aemet import bp as aemet_bp
from blueprints.stripe_bp import bp as stripe_bp

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

# ─────────────────────────────────────────────
# STATIC SERVING
# ─────────────────────────────────────────────
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

@app.route('/pago-completado')
def serve_pago_completado():
    return app.send_static_file('index.html')

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
# BOOT
# ─────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)
