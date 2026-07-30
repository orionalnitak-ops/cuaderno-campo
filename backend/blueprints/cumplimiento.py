"""
blueprints/cumplimiento.py — "Revisión del cuaderno": semáforo de cumplimiento.

Pantalla de SOLO LECTURA. No pide ni un dato nuevo al agricultor: todo se deriva
de lo que ya anotó. El motor no escribe nada en la BD.

Ver spec/features/011-revision-cuaderno/spec.md.

Dos reglas de este módulo que conviene no romper:

  1. `evaluar_cumplimiento()` recibe la conexión y la fecha, y no toca Flask.
     Es lo que permite testearlo contra sqlite3.connect(':memory:'), igual que
     `_check_asesor` en tratamientos.py.
  2. Este módulo importa SOLO de `db` y `helpers`. `compras.py` ya importa de
     `ia.py`, así que cualquier import cruzado de más abre un ciclo.
"""
import datetime
import logging
import re
import unicodedata

from flask import Blueprint, jsonify
from flask_login import login_required

from db import get_db, dicts, one
from helpers import get_uid

bp = Blueprint('cumplimiento', __name__)
logger = logging.getLogger(__name__)


# ── Configuración ──────────────────────────────────────────────────────────────

ITEAF_PERIODICIDAD_ANIOS = 3   # RD 1702/2011: cada 3 años desde 2020 (antes 5)
ITEAF_AVISO_DIAS         = 60  # margen razonable para pedir cita en la estación

# Umbrales compartidos con `_generar_alertas` de ia.py, que los importa de aquí.
# Si divergen, Inicio y el semáforo se contradicen delante del agricultor.
DIAS_SIN_REGISTRO    = 30
DIAS_PLAZO_SEGURIDAD = 7

# Equipos no sujetos a inspección ITEAF ni a inscripción ROMA. `tipo` y
# `descripcion` son texto libre, así que esto es best-effort a propósito:
# excluir de más solo silencia un aviso; incluir de más marca en rojo algo que
# el agricultor no puede arreglar, y eso sí quema la confianza en la pantalla.
# 'externo'/'contratado'/'empresa' cubren el equipo semilla "Empresa externa /
# Contratado" que crea _seed_if_needed en db.py: no es una máquina propia, es
# una marca de "lo hizo otro", así que exigirle ITEAF o ROMA es un falso
# positivo que el agricultor no puede resolver.
EQUIPOS_EXENTOS_KEYWORDS = ('mochila', 'manual', 'lanza', 'espalda', 'carretilla',
                            'externo', 'externa', 'contratado', 'empresa')

MAX_ITEMS = 20  # con 50+ parcelas el JSON no puede crecer linealmente

# Fragmento SQL LITERAL, constante de módulo. Se interpola con f-string en tres
# consultas, así que la regla es dura: NUNCA construir esta cadena a partir de
# input ni de datos de la BD. La campaña viaja siempre como parámetro por los
# dos `?`, jamás dentro del texto. Vive aquí arriba, y no como variable local,
# precisamente para que se lea como constante y nadie la convierta en dinámica.
#
# Motivo de existir: `tratamientos.campana` se añadió con _add_col y hay
# registros antiguos con NULL o vacío. Filtrar `campana = ?` a secas los sacaría
# del universo e inflaría el porcentaje, que es fallar hacia el lado optimista.
_CAMPANA_SQL = "COALESCE(NULLIF(TRIM(campana), ''), ?) = ?"

DESCARGO = ("Orientativo. Repasa lo que te marcamos, pero no sustituye a la "
            "revisión oficial de un inspector.")


# ── Utilidades puras ───────────────────────────────────────────────────────────

def _norm(s):
    """Clave de comparación de productos.

    Se normaliza en Python y NO en SQL a propósito: UPPER() en SQLite solo
    mayusculiza ASCII y en PostgreSQL es Unicode, así que 'Añejo' daría
    resultados distintos en local y en producción.

    'ES-25.123 ' y 'es25123' -> 'ES25123'

    No se intenta quitar prefijos como "Nº": distinguir una etiqueta escrita a
    mano de un código que empieza por letra no se puede hacer sin corromper
    códigos legítimos. Ante la duda, el producto sale listado — un falso aviso
    es recuperable, dar por bueno un producto sin respaldo no lo es.
    """
    if not s:
        return ''
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^A-Za-z0-9]', '', s).upper()


def _parse_fecha(v):
    """Fecha tolerante -> date o None. Nunca lanza.

    `equipos.fecha_iteaf` no se valida en el backend (equipos.py:22), así que
    puede llegar vacía, con formato español o con basura.
    """
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        pass
    try:
        return datetime.datetime.strptime(s, '%d/%m/%Y').date()
    except (ValueError, TypeError):
        return None


def _suma_anios(f, anios):
    """f + N años, a prueba de bisiestos (replace(year=) revienta con 29-feb)."""
    try:
        return f.replace(year=f.year + anios)
    except ValueError:
        return f.replace(year=f.year + anios, day=28)


def _estado_iteaf(fecha_iteaf, hoy):
    """Estado de la inspección ITEAF a partir de la única fecha que guardamos.

    Devuelve (estado, caducidad_o_None). Nunca lanza.

    Ante una fecha ausente o ilegible devuelve un aviso, nunca 'caducada':
    afirmar que está caducada cuando no lo sabemos sería falso.
    """
    f = _parse_fecha(fecha_iteaf)
    if f is None:
        return ('sin_fecha' if not str(fecha_iteaf or '').strip() else 'no_valida'), None
    if f > hoy:
        return 'fecha_futura', None
    caducidad = _suma_anios(f, ITEAF_PERIODICIDAD_ANIOS)
    if caducidad < hoy:
        return 'caducada', caducidad
    if (caducidad - hoy).days <= ITEAF_AVISO_DIAS:
        return 'proxima', caducidad
    return 'ok', caducidad


def _es_exento(equipo):
    """True si el equipo no está sujeto a ITEAF/ROMA (mochila, equipo manual…)."""
    texto = f"{equipo.get('tipo') or ''} {equipo.get('descripcion') or ''}".lower()
    return any(k in texto for k in EQUIPOS_EXENTOS_KEYWORDS)


def _color(pct, criticos):
    """El color mide GRAVEDAD; el porcentaje mide CUÁNTO falta. Dos ejes
    distintos a propósito.

    Rojo significa "tienes algo que te puede costar una sanción", no "te faltan
    muchas cosas". Atarlo al porcentaje daba un semáforo incoherente: un
    cuaderno a medio rellenar salía en rojo mientras la propia pantalla decía
    "importantes: 0". Ahora el número ya dice cuánto queda; el color dice si es
    grave.
    """
    if criticos:
        return 'rojo'
    if pct >= 90:
        return 'verde'
    return 'naranja'


def _fmt(f):
    """date -> 'DD/MM/YYYY' para enseñárselo al agricultor."""
    return f.strftime('%d/%m/%Y') if f else '—'


def _plural(n, singular, plural):
    return singular if n == 1 else plural


def _bloque(bid, titulo, peso, universo, afectados, items, mensaje,
            por_que='', accion='', destino=None, informativo=False):
    """Construye un bloque del semáforo y su puntuación.

    Un bloque con universo 0 es 'no_aplica' y queda FUERA del denominador: quien
    no tiene equipos no puede tener la ITEAF caducada, y si contara tendría un
    techo de porcentaje que no podría subir haga lo que haga.
    """
    if universo == 0:
        estado, puntos = 'no_aplica', 0.0
    elif afectados == 0:
        estado, puntos = 'ok', float(peso)
    else:
        hay_critico = any(i.get('severidad') == 'critico' for i in items)
        estado = 'critico' if hay_critico else 'aviso'
        puntos = peso * (1 - afectados / universo)

    return {
        'id': bid, 'titulo': titulo, 'estado': estado, 'informativo': informativo,
        'peso': peso, 'puntos': round(puntos, 3),
        'universo': universo, 'afectados': afectados,
        'mensaje': mensaje, 'por_que': por_que, 'accion': accion,
        'destino': destino or {},
        'items': items[:MAX_ITEMS],
        'items_truncados': max(0, len(items) - MAX_ITEMS),
    }


# ── Motor ──────────────────────────────────────────────────────────────────────

def evaluar_cumplimiento(conn, uid, hoy=None, campana=None):
    """Evalúa el estado del cuaderno. Función pura: no abre/cierra la conexión,
    no toca Flask y no escribe nada.

    Hace un número FIJO de consultas (11), independiente del número de parcelas.
    `_generar_alertas` de ia.py hace 1+3·N y con 50 parcelas son ~151 consultas
    dentro del login; ese patrón no se replica aquí. Todos los cruces por parcela
    se resuelven con sets/dicts en Python sobre resultados ya agregados.
    """
    hoy = hoy or datetime.date.today()

    # 1. campaña activa
    if not campana:
        expl = one(conn, "SELECT campana_activa FROM explotacion WHERE user_id=?", (uid,))
        campana = (expl or {}).get('campana_activa') or '2025/2026'

    # 2. parcelas activas (para etiquetar y como universo de cultivo_campana)
    parcelas = dicts(conn,
        "SELECT id, nombre_finca FROM parcelas WHERE user_id=? AND activa=1", (uid,))
    nombre_parcela = {p['id']: (p.get('nombre_finca') or f"Parcela {p['id']}") for p in parcelas}

    camp_sql = _CAMPANA_SQL          # constante de módulo, ver arriba
    camp_par = (campana, campana)    # la campaña va por parámetro, no en el texto

    bloques = []

    # ── ITEAF y ROMA (una sola consulta para los dos bloques) ──
    # 3. uso agregado: qué equipos y qué personas firman tratamientos esta campaña
    # Una sola consulta da los dos horizontes: "usado esta campaña" (marca la
    # severidad) y "usado alguna vez" (distingue un equipo real de una fila de
    # plantilla que nadie tocó).
    uso = dicts(conn, f"""
        SELECT equipo_id, aplicador_id, asesor_id,
               COUNT(*) AS veces,
               SUM(CASE WHEN {camp_sql} THEN 1 ELSE 0 END) AS veces_campana
        FROM tratamientos
        WHERE user_id=? AND deleted_at IS NULL
        GROUP BY equipo_id, aplicador_id, asesor_id
    """, camp_par + (uid,))
    equipos_usados     = {u['equipo_id']    for u in uso if u.get('equipo_id') and u['veces_campana']}
    aplicadores_usados = {u['aplicador_id'] for u in uso if u.get('aplicador_id') and u['veces_campana']}
    asesores_usados    = {u['asesor_id']    for u in uso if u.get('asesor_id') and u['veces_campana']}
    equipos_usados_alguna_vez = {u['equipo_id'] for u in uso if u.get('equipo_id')}

    # 4. equipos
    equipos = dicts(conn, """
        SELECT id, descripcion, tipo, marca, modelo, num_registro_roma, fecha_iteaf
        FROM equipos WHERE user_id=?
    """, (uid,))
    def _es_plantilla(e):
        """Fila de equipo que nadie ha rellenado ni usado jamás.

        `_seed_if_needed` en db.py crea tres al dar de alta la cuenta, del tipo
        "Pulverizador terrestre (completar marca y modelo)". Suspender al
        agricultor por una fila que le puso la app sola y que nunca ha tocado es
        un falso positivo caro: se lleva 7 de los 16 puntos y tiñe de rojo un
        cuaderno sin ningún incumplimiento.

        Se autocorrige: en cuanto anota el ROMA, la fecha ITEAF o usa el equipo
        en un tratamiento, deja de ser plantilla y vuelve a contar. Y usarlo sin
        ROMA ya lo bloquea el POST de tratamientos, que es donde importa.
        """
        return (e['id'] not in equipos_usados_alguna_vez
                and not (e.get('num_registro_roma') or '').strip()
                and not str(e.get('fecha_iteaf') or '').strip())

    equipos = [e for e in equipos if not _es_exento(e) and not _es_plantilla(e)]

    def _etiqueta_equipo(e):
        return (e.get('descripcion') or ' '.join(
            filter(None, [e.get('tipo'), e.get('marca'), e.get('modelo')]))
            or f"Equipo {e['id']}")

    def _severidad_equipo(e, base='critico'):
        """Un equipo que ya no se usa no puede exigirse en rojo: `equipos` no
        tiene baja lógica y borrarlo rompería las referencias de tratamientos."""
        if e['id'] in equipos_usados:
            return base, ''
        return 'aviso', ' · No lo has usado esta campaña; si ya no lo tienes, bórralo en Ajustes → Equipos'

    items_iteaf, items_roma = [], []
    for e in equipos:
        estado, caducidad = _estado_iteaf(e.get('fecha_iteaf'), hoy)
        if estado != 'ok':
            sev, nota = _severidad_equipo(e, 'critico' if estado == 'caducada' else 'aviso')
            detalle = {
                'caducada':     f"Caducó el {_fmt(caducidad)}",
                'proxima':      f"Caduca el {_fmt(caducidad)}",
                'sin_fecha':    "No has anotado la fecha de la última inspección",
                'no_valida':    "La fecha anotada no se entiende",
                'fecha_futura': "La fecha anotada es posterior a hoy",
            }.get(estado, estado)
            items_iteaf.append({
                'clave': f"eq-{e['id']}", 'etiqueta': _etiqueta_equipo(e),
                'detalle': detalle + nota, 'severidad': sev,
            })
        if not (e.get('num_registro_roma') or '').strip():
            sev, nota = _severidad_equipo(e)
            items_roma.append({
                'clave': f"eq-{e['id']}", 'etiqueta': _etiqueta_equipo(e),
                'detalle': "Sin nº de registro ROMA" + nota, 'severidad': sev,
            })

    n_eq = len(equipos)
    bloques.append(_bloque(
        'iteaf', 'Inspección ITEAF de los equipos', 4, n_eq, len(items_iteaf), items_iteaf,
        mensaje=(f"{len(items_iteaf)} de tus {n_eq} {_plural(n_eq, 'equipo', 'equipos')} "
                 f"{_plural(len(items_iteaf), 'necesita', 'necesitan')} revisión"
                 if items_iteaf else "Tus equipos tienen la inspección al día"),
        por_que="RD 1702/2011: los equipos de aplicación se inspeccionan cada 3 años.",
        accion="Anota la fecha de la última inspección ITEAF del equipo",
        destino={'screen': 'mas', 'section': 'equipos'}))

    bloques.append(_bloque(
        'roma', 'Registro ROMA de los equipos', 3, n_eq, len(items_roma), items_roma,
        mensaje=(f"{len(items_roma)} {_plural(len(items_roma), 'equipo', 'equipos')} "
                 f"sin nº de registro ROMA"
                 if items_roma else "Todos tus equipos tienen nº ROMA"),
        por_que="RD 1702/2011: los equipos de aplicación deben estar inscritos en el ROMA.",
        accion="Anota el nº de registro ROMA del equipo",
        destino={'screen': 'mas', 'section': 'equipos'}))

    # ── Trazabilidad: producto aplicado del que no consta compra ──
    # 5. compras de TODAS las campañas: puedes aplicar en 2025/26 algo comprado
    #    en 2024/25, y filtrar por campaña generaría falsos positivos masivos.
    compras = dicts(conn,
        "SELECT producto, num_registro_mapa FROM compras WHERE user_id=? AND deleted_at IS NULL",
        (uid,))
    # 6. productos realmente aplicados, ya agrupados (no una fila por tratamiento)
    aplicados = dicts(conn, f"""
        SELECT producto_comercial, num_registro_mapa,
               COUNT(*) AS veces, MAX(fecha_aplicacion) AS ultima
        FROM tratamientos
        WHERE user_id=? AND deleted_at IS NULL AND {camp_sql}
          AND COALESCE(TRIM(producto_comercial), '') <> ''
        GROUP BY producto_comercial, num_registro_mapa
        ORDER BY COUNT(*) DESC
    """, (uid,) + camp_par)

    if not compras:
        # Salvaguarda crítica para la adopción: sin esto, quien no use el módulo
        # de compras abre la pantalla y ve el 100% de sus productos en rojo el
        # primer día, el semáforo sale rojo de entrada y no vuelve.
        bloques.append(_bloque(
            'trazabilidad_compras', 'Respaldo de compra de los productos', 4, 0, 0, [],
            mensaje="Aún no usas el módulo de compras. Regístralas y podremos cruzarlas con tus tratamientos.",
            por_que="RD 1311/2012 Anexo III S5: hay que poder justificar la procedencia del producto aplicado.",
            accion="Anota tus facturas de compra de fitosanitarios",
            destino={'form': 'compra'}))
    else:
        regs    = {_norm(c.get('num_registro_mapa')) for c in compras} - {''}
        nombres = {_norm(c.get('producto')) for c in compras} - {''}
        items_traz = []
        for t in aplicados:
            # Vale cualquiera de las dos vías: nº de registro MAPA (identificador
            # fuerte) o nombre comercial. En cascada y no excluyente a propósito:
            # `compras` acepta un registro como 'ES-25.123' pero `tratamientos`
            # lo exige numérico, así que el mismo producto puede tener registros
            # que no casan y solo coincidir por nombre. Ante la duda preferimos
            # NO marcarlo: un falso positivo aquí sale caro en confianza.
            respaldado = (_norm(t.get('num_registro_mapa')) in regs
                          or _norm(t.get('producto_comercial')) in nombres)
            if not respaldado:
                veces = t.get('veces') or 0
                items_traz.append({
                    'clave': f"prod-{_norm(t.get('num_registro_mapa')) or _norm(t.get('producto_comercial'))}",
                    'etiqueta': t.get('producto_comercial') or '(sin nombre)',
                    'detalle': (f"Aplicado {veces} {_plural(veces, 'vez', 'veces')}"
                                f" · no consta la compra"),
                    'severidad': 'critico',
                })
        n_ap = len(aplicados)
        bloques.append(_bloque(
            'trazabilidad_compras', 'Respaldo de compra de los productos', 4,
            n_ap, len(items_traz), items_traz,
            mensaje=(f"{len(items_traz)} "
                     f"{_plural(len(items_traz), 'producto que has aplicado no consta comprado', 'productos que has aplicado no constan comprados')}"
                     if items_traz else "Todos los productos que has aplicado constan comprados"),
            por_que="RD 1311/2012 Anexo III S5: hay que poder justificar la procedencia del producto aplicado.",
            accion="Anota la factura de compra de ese producto",
            destino={'form': 'compra'}))

    # ── ROPO de las personas que firman tus tratamientos ──
    # 7. fichas activas de aplicadores y asesores
    personas = dicts(conn, """
        SELECT 'aplicador' AS rol, id, nombre, num_ropo FROM aplicadores
         WHERE user_id=? AND activo=1
        UNION ALL
        SELECT 'asesor' AS rol, id, nombre, num_ropo FROM asesores
         WHERE user_id=? AND activo=1
    """, (uid, uid))
    # 8. asesor antiguo escrito a mano: sin ficha, luego sin ROPO por definición
    legacy = dicts(conn, f"""
        SELECT TRIM(asesor) AS nombre, COUNT(*) AS veces
        FROM tratamientos
        WHERE user_id=? AND deleted_at IS NULL AND {camp_sql}
          AND asesor_id IS NULL AND COALESCE(TRIM(asesor), '') <> ''
        GROUP BY TRIM(asesor)
    """, (uid,) + camp_par)

    items_ropo = []
    for p in personas:
        if (p.get('num_ropo') or '').strip():
            continue
        usados = aplicadores_usados if p['rol'] == 'aplicador' else asesores_usados
        firma = p['id'] in usados
        items_ropo.append({
            'clave': f"{p['rol']}-{p['id']}",
            'etiqueta': f"{p['rol'].capitalize()}: {p.get('nombre') or '(sin nombre)'}",
            'detalle': ("Sin nº ROPO" if firma else
                        "Sin nº ROPO · todavía no ha firmado ningún tratamiento"),
            'severidad': 'critico' if firma else 'aviso',
        })
    for l in legacy:
        veces = l.get('veces') or 0
        items_ropo.append({
            'clave': f"legacy-{_norm(l.get('nombre'))}",
            'etiqueta': f"Asesor: {l.get('nombre')}",
            'detalle': (f"Escrito a mano en {veces} {_plural(veces, 'tratamiento', 'tratamientos')}"
                        f" · sin ficha, así que sin nº ROPO"),
            'severidad': 'critico',
        })

    n_pers = len(personas) + len(legacy)
    bloques.append(_bloque(
        'ropo', 'Nº ROPO de aplicadores y asesores', 3, n_pers, len(items_ropo), items_ropo,
        mensaje=(f"{len(items_ropo)} {_plural(len(items_ropo), 'persona', 'personas')} sin nº ROPO"
                 if items_ropo else "Todas las personas de tus tratamientos tienen ROPO"),
        por_que="RD 1311/2012 art. 12 y Orden APA/204/2023: quien aplica y quien asesora "
                "deben estar inscritos en el ROPO.",
        accion="Anota el nº ROPO en su ficha",
        destino={'screen': 'mas', 'section': 'aplicadores'}))

    # ── Cultivo de campaña por parcela ──
    # 9. parcelas con cultivo declarado esta campaña
    con_cultivo = {r['parcela_id'] for r in dicts(conn, """
        SELECT DISTINCT cc.parcela_id
        FROM cultivos_campana cc
        JOIN parcelas p ON p.id = cc.parcela_id
        WHERE p.user_id=? AND cc.campana=?
    """, (uid, campana))}
    items_cult = [{
        'clave': f"parc-{pid}", 'etiqueta': nombre,
        'detalle': f"Sin cultivo declarado en {campana}", 'severidad': 'aviso',
    } for pid, nombre in nombre_parcela.items() if pid not in con_cultivo]

    bloques.append(_bloque(
        'cultivo_campana', 'Cultivo declarado por parcela', 2,
        len(parcelas), len(items_cult), items_cult,
        mensaje=(f"{len(items_cult)} de tus {len(parcelas)} parcelas no tienen cultivo declarado"
                 if items_cult else "Todas tus parcelas tienen cultivo declarado"),
        por_que="El cuaderno debe reflejar qué se cultiva en cada parcela y campaña.",
        accion="Asigna el cultivo de la campaña a la parcela",
        destino={'screen': 'parcelas'}))

    # ── Informativos: no puntúan (peso 0) ──
    # Un plazo de seguridad que vence en 5 días no es un defecto, es información:
    # si restara, el porcentaje empeoraría justo cuando se hacen las cosas bien.
    # Y los 30 días sin registrar son criterio nuestro, no obligación legal.

    # 10. plazos de seguridad que vencen en los próximos días (ISO se compara
    #     lexicográficamente, válido en ambos motores)
    plazos = dicts(conn, """
        SELECT parcela_id, producto_comercial, fecha_recoleccion_minima
        FROM tratamientos
        WHERE user_id=? AND deleted_at IS NULL
          AND fecha_recoleccion_minima >= ? AND fecha_recoleccion_minima <= ?
        ORDER BY fecha_recoleccion_minima
    """, (uid, hoy.isoformat(),
          (hoy + datetime.timedelta(days=DIAS_PLAZO_SEGURIDAD)).isoformat()))
    items_plazo = [{
        'clave': f"plazo-{p.get('parcela_id')}-{_norm(p.get('producto_comercial'))}",
        'etiqueta': p.get('producto_comercial') or '(sin nombre)',
        'detalle': (f"{nombre_parcela.get(p.get('parcela_id'), 'Parcela')} · "
                    f"no recolectar antes del {_fmt(_parse_fecha(p.get('fecha_recoleccion_minima')))}"),
        'severidad': 'aviso',
    } for p in plazos]
    bloques.append(_bloque(
        'plazo_seguridad', 'Plazos de seguridad en curso', 0,
        len(items_plazo), len(items_plazo), items_plazo,
        mensaje=(f"{len(items_plazo)} {_plural(len(items_plazo), 'plazo', 'plazos')} de "
                 f"seguridad {_plural(len(items_plazo), 'vence', 'vencen')} en los próximos "
                 f"{DIAS_PLAZO_SEGURIDAD} días"
                 if items_plazo else "Ningún plazo de seguridad a punto de vencer"),
        por_que="Entre la aplicación y la recolección debe pasar el plazo de seguridad del producto.",
        accion="Espera a la fecha indicada antes de recolectar",
        destino={'screen': 'historial'}, informativo=True))

    # 11. última fecha registrada por parcela (solo parcelas con historial)
    ultimos = dicts(conn, """
        SELECT parcela_id, MAX(fecha_aplicacion) AS ultima
        FROM tratamientos
        WHERE user_id=? AND deleted_at IS NULL AND parcela_id IS NOT NULL
        GROUP BY parcela_id
    """, (uid,))
    items_reg = []
    for r in ultimos:
        f = _parse_fecha(r.get('ultima'))
        if not f or r['parcela_id'] not in nombre_parcela:
            continue
        dias = (hoy - f).days
        if dias > DIAS_SIN_REGISTRO:
            items_reg.append({
                'clave': f"reg-{r['parcela_id']}",
                'etiqueta': nombre_parcela[r['parcela_id']],
                'detalle': f"Último tratamiento hace {dias} días ({_fmt(f)})",
                'severidad': 'aviso',
            })
    bloques.append(_bloque(
        'registro_reciente', 'Parcelas sin movimiento reciente', 0,
        len(items_reg), len(items_reg), items_reg,
        mensaje=(f"{len(items_reg)} {_plural(len(items_reg), 'parcela lleva', 'parcelas llevan')} "
                 f"más de {DIAS_SIN_REGISTRO} días sin registros"
                 if items_reg else "Tus parcelas tienen registros recientes"),
        por_que="No es una obligación legal: es un recordatorio para que no se te "
                "quede nada sin anotar.",
        accion="Repasa si te falta anotar algo en esa parcela",
        destino={'screen': 'historial'}, informativo=True))

    # ── Puntuación ──
    puntuables = [b for b in bloques if not b['informativo']]
    totales   = sum(b['peso'] for b in puntuables if b['estado'] != 'no_aplica')
    obtenidos = sum(b['puntos'] for b in puntuables if b['estado'] != 'no_aplica')
    pct = round(100 * obtenidos / totales) if totales else 100

    criticos = sum(1 for b in puntuables for i in b['items'] if i['severidad'] == 'critico')
    avisos   = sum(1 for b in puntuables for i in b['items'] if i['severidad'] == 'aviso')
    color = _color(pct, criticos)

    pendientes = criticos + avisos
    if pendientes == 0:
        titulo, subtitulo = "Todo en orden", "No hemos encontrado nada pendiente"
    else:
        # Los títulos siguen al color, que ahora habla de gravedad y no de
        # cantidad: el rojo nombra lo importante, no "lo mucho que falta".
        titulo = {'verde':   "Casi todo en orden",
                  'naranja': "Te faltan cosas por completar",
                  'rojo':    "Tienes algo importante pendiente"}[color]
        subtitulo = f"{pendientes} {_plural(pendientes, 'cosa pendiente', 'cosas pendientes')}"
        if criticos:
            subtitulo += (f", {criticos} "
                          f"{_plural(criticos, 'importante', 'importantes')}")

    return {
        'generado_en': datetime.datetime.now().isoformat(timespec='seconds'),
        'campana': campana,
        'porcentaje': pct, 'color': color,
        'titulo': titulo, 'subtitulo': subtitulo,
        'descargo': DESCARGO,
        'resumen': {
            'criticos': criticos, 'avisos': avisos,
            'bloques_ok': sum(1 for b in puntuables if b['estado'] == 'ok'),
            'bloques_no_aplica': sum(1 for b in puntuables if b['estado'] == 'no_aplica'),
        },
        'puntuacion': {'obtenidos': round(obtenidos, 2), 'totales': totales},
        'bloques': bloques,
    }


# ── Endpoint ───────────────────────────────────────────────────────────────────

@bp.route('/api/cumplimiento', methods=['GET'])
@login_required
def get_cumplimiento():
    # get_uid() y no current_user.id: si no, el admin impersonando vería su
    # propio semáforo en lugar del agricultor al que está dando soporte.
    conn = get_db()
    try:
        return jsonify({"ok": True, "data": evaluar_cumplimiento(conn, get_uid())})
    except Exception:
        logger.exception("Error calculando cumplimiento")
        return jsonify({"ok": False,
                        "error": "No se pudo calcular el estado del cuaderno"}), 500
    finally:
        conn.close()
