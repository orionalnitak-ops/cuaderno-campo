import logging
import os
import warnings

from flask import Flask, jsonify, request
from flask_cors import CORS
from db import init_db, get_db, one

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# INIT DB (ejecutar siempre al importar — gunicorn + flask run)
# ─────────────────────────────────────────────
init_db()

# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
# static_url_path distinto de '' a propósito: si coincidiera con la raíz,
# Flask registraría su propia ruta automática con el mismo patrón que
# serve_static() más abajo, y como la suya se registra antes, ganaría siempre
# — dejando el fallback a index.html (necesario para las pantallas SPA como
# /recuperar) como código muerto. Nada sirve archivos por esa ruta interna;
# todo pasa por send_static_file() dentro de serve_static().
app = Flask(__name__, static_folder=frontend_dir, static_url_path='/__flask_static_no_usar')

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
from blueprints.asesores import bp as asesores_bp  # noqa: E402
from blueprints.compras import bp as compras_bp  # noqa: E402
from blueprints.sigpac import bp as sigpac_bp  # noqa: E402
from blueprints.nlp import bp as nlp_bp  # noqa: E402
from blueprints.imports_exports import bp as imports_exports_bp  # noqa: E402
from blueprints.aemet import bp as aemet_bp  # noqa: E402
from blueprints.stripe_bp import bp as stripe_bp  # noqa: E402
from blueprints.push import bp as push_bp  # noqa: E402
from blueprints.uhc import bp as uhc_bp  # noqa: E402
from blueprints.ia import bp as ia_bp  # noqa: E402
from blueprints.cumplimiento import bp as cumplimiento_bp  # noqa: E402
from blueprints.analisis import bp as analisis_bp  # noqa: E402

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(explotacion_bp)
app.register_blueprint(parcelas_bp)
app.register_blueprint(tratamientos_bp)
app.register_blueprint(fertilizacion_bp)
app.register_blueprint(labores_bp)
app.register_blueprint(equipos_bp)
app.register_blueprint(asesores_bp)
app.register_blueprint(compras_bp)
app.register_blueprint(sigpac_bp)
app.register_blueprint(nlp_bp)
app.register_blueprint(imports_exports_bp)
app.register_blueprint(aemet_bp)
app.register_blueprint(stripe_bp)
app.register_blueprint(push_bp)
app.register_blueprint(uhc_bp)
app.register_blueprint(ia_bp)
app.register_blueprint(cumplimiento_bp)
app.register_blueprint(analisis_bp)

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
    # CSP ENFORCING (bloqueante). Política completa verificada contra el código real:
    # enumera todos los hosts que la app usa y bloquea el resto.
    #   - script-src SIN 'unsafe-inline': el único <script> inline (registro del SW)
    #     se externalizó a /sw-register.js, así que un script inyectado por XSS NO se
    #     ejecuta (defensa real anti-XSS). unpkg = React/ReactDOM/Leaflet.
    #   - style-src mantiene 'unsafe-inline' a propósito: React aplica estilos vía
    #     style={{}} y hay un <style> grande en index.html. El riesgo style-based es
    #     mucho menor que el de script; endurecerlo rompería la UI.
    #   - img-src cubre los 3 WMS del mapa (PNOA IGN, SIGPAC-hubcloud, Red Natura
    #     IEPNB) + data:/blob: (marcadores Leaflet, iconos). Sin capa base OSM.
    #   - connect-src cubre Open-Meteo (el tiempo). El resto de fetch va a /api (self).
    #     unpkg se incluye para que el navegador pueda descargar los source maps
    #     (*.js.map) de React/Leaflet con DevTools abierto — solo afecta a depuración,
    #     el host ya es de confianza en script-src. La suscripción Web Push nativa
    #     (pushManager.subscribe) la gestiona el navegador y NO está sujeta a
    #     connect-src, así que las Alertas AEMET siguen funcionando.
    #   - object-src/base-uri/frame-ancestors: anti plugin-XSS, anti base-tag, anti
    #     clickjacking (la app no usa <base>, <object>/<embed>, ni se embebe en iframe).
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https://sigpac-hubcloud.es https://geoserver.iepnb.es https://www.ign.es; "
        "connect-src 'self' https://unpkg.com https://api.open-meteo.com https://geocoding-api.open-meteo.com; "
        "worker-src 'self'; manifest-src 'self'; "
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    if _is_prod:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


_PLAN_EXEMPT_PREFIXES = ('/api/auth/', '/api/admin/', '/api/stripe/')

# Endpoints POST que NO escriben datos del agricultor y por tanto no cuentan
# como "escribir" a efectos del corte por plan caducado.
#
# Cambiar de explotación activa solo guarda un id en la sesión. Es un POST por
# la forma del endpoint, no por lo que hace. Si el guard lo bloquea, un
# agricultor con varias fincas se queda consultando únicamente la que tuviera
# abierta al caducarle el plan, sin forma de llegar a las demás. Eso no es solo
# lectura: es media lectura.
#
# Se listan por NOMBRE DE ENDPOINT, no por trozo de URL: un `endswith('/activar')`
# dejaría entrar sin querer a cualquier ruta futura que acabe igual y sí escriba.
_PLAN_EXEMPT_ENDPOINTS = ('explotacion.activar_explotacion',)

# Endpoints que NUNCA se bloquean por el tope de explotaciones del plan (017).
#
# Los dos primeros son la salida del callejón: si marcar una finca como
# principal o cambiar de finca activa se bloqueara por el propio tope, quien
# baja de plan se quedaría encerrado en la finca equivocada sin forma de
# cambiarla. Crear una explotación se deja pasar porque ya tiene su propio
# control con un mensaje mucho mejor (`upgrade_required` / `limit_reached`).
_LIMITE_EXEMPT_ENDPOINTS = (
    'explotacion.activar_explotacion',
    'explotacion.principal_explotacion',
    'explotacion.explotaciones',
)


def _guard_limite_explotaciones():
    """403 si se intenta anotar en una explotación que el plan no cubre.

    Lo único que diferencia Básico de Pro es el número de explotaciones, y
    hasta ahora eso solo se comprobaba al CREAR una finca: quien bajaba de Pro
    a Básico seguía anotando en las cinco.

    Solo afecta a escribir. Leer no se toca: sus fincas las consulta todas.
    """
    from flask_login import current_user
    from helpers import get_uid, get_active_explotacion_id, explotaciones_escribibles

    if request.endpoint in _LIMITE_EXEMPT_ENDPOINTS:
        return
    # Hoy solo la llama `guard_active_plan`, que ya ha comprobado la sesión.
    # La guarda está por si mañana la llama alguien más: sobre un anónimo,
    # `explotaciones_limit()` reventaría. Se deja rastro, porque llegar aquí sin
    # sesión no es un caso normal: es un fallo de quien llama.
    if not current_user.is_authenticated:
        logger.warning('_guard_limite_explotaciones sin usuario autenticado en %s',
                       request.endpoint)
        return
    limit = current_user.explotaciones_limit()
    if limit is None:
        return      # admin, premium, súper usuarios: sin tope

    conn = get_db()
    try:
        escribibles = explotaciones_escribibles(conn, get_uid(), limit)
        activa = get_active_explotacion_id(conn)
    finally:
        conn.close()

    # Sin fincas todavía (onboarding), o la activa entra en el plan: adelante.
    if not escribibles or activa is None or activa in escribibles:
        return

    return jsonify({
        "error": "explotacion_solo_lectura",
        "feature": "multi_explotacion",
        "limit": limit,
        "message": (f"Tu plan cubre {limit} explotación{'es' if limit > 1 else ''}. "
                    "Esta está en solo lectura: puedes consultarla y, si quieres anotar "
                    "en ella, marcarla como principal desde el selector de explotación. "
                    "Con el plan Pro llevas hasta cinco a la vez."),
    }), 403


@app.before_request
def guard_active_plan():
    """Bloquea escrituras si el trial ha caducado o la suscripción ha expirado."""
    from flask_login import current_user
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    if any(request.path.startswith(p) for p in _PLAN_EXEMPT_PREFIXES):
        return
    if request.endpoint in _PLAN_EXEMPT_ENDPOINTS:
        return
    if not current_user.is_authenticated:
        return
    if current_user.plan_is_active():
        # El plan está al día. Queda comprobar que la finca en la que va a
        # anotar es una de las que cubre.
        return _guard_limite_explotaciones()

    # Va a denegar. Si es un plan de pago con la fecha vencida, puede que el
    # agricultor esté al corriente y lo que se haya perdido sea el webhook de
    # la renovación. Antes de cortarle el cuaderno, se le pregunta a Stripe.
    # Esto es el único punto donde se llama a Stripe fuera del checkout, y solo
    # ocurre en escrituras de cuentas ya vencidas: la respuesta se guarda en la
    # BD, así que no se repite en cada petición.
    if current_user.plan in ('basic', 'pro', 'premium') and current_user.subscription_ends_at:
        from blueprints.stripe_bp import reconciliar_suscripcion
        if reconciliar_suscripcion(current_user.id):
            return

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
    from blueprints.push import job_check_push_alertas, job_avisar_fin_de_trial
    import atexit
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(job_check_push_alertas, 'interval', minutes=30, id='push_alertas')
    _scheduler.add_job(job_avisar_fin_de_trial, 'cron', hour=9, minute=0,
                       id='avisar_fin_de_trial', replace_existing=True)
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
