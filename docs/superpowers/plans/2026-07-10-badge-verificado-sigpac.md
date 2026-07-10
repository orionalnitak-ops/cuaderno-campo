# Badge "Verificado con SIGPAC" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir un badge por parcela que contrasta la superficie declarada con la de SIGPAC (±5%) y la muestra en la lista y en la ficha, verificando al guardar y con un botón manual de re-verificación.

**Architecture:** Backend Flask/SQLite-Postgres: 2 columnas nuevas en `parcelas`, un helper puro que deriva el estado del badge, un helper que obtiene la superficie oficial vía GetFeatureInfo del GeoServer "SIGPAC en la Nube" (hubcloud), y un endpoint que verifica y persiste. Frontend React JSX: pill en la lista, badge + botón en la ficha, auto-verificación tras guardar.

**Tech Stack:** Python 3 + Flask, `requests`, SQLite/PostgreSQL (wrapper `db.py`), React JSX (Babel), sin framework de tests (se usa un script `python` plano para la lógica pura + verificación manual en navegador).

---

## Ficheros afectados

- **Modificar** `backend/db.py` — 2 columnas nuevas en el bloque `_add_col` de `parcelas`.
- **Modificar** `backend/helpers.py` — helper puro `estado_sigpac(parcela)`.
- **Crear** `backend/tests/test_estado_sigpac.py` — test plano (asserts) del helper puro.
- **Modificar** `backend/blueprints/sigpac.py` — helper `superficie_sigpac_parcela(...)` (fuente hubcloud).
- **Modificar** `backend/blueprints/parcelas.py` — endpoint `verificar-sigpac` + enriquecer GET lista y GET detalle.
- **Modificar** `frontend/screens_parcelas.jsx` — pill en lista, badge + botón re-verificar en ficha, auto-verificación tras guardar.
- **Modificar** `frontend/service-worker.js` — bump `CACHE_NAME`.

---

## Task 1: Columnas nuevas en la tabla `parcelas`

**Files:**
- Modify: `backend/db.py:333-344`

- [ ] **Step 1: Añadir las 2 columnas a la lista `_add_col` de parcelas**

En `backend/db.py`, dentro del `for col, typ in [...]` de la tabla `parcelas` (empieza en la línea 333), añade dos entradas antes del cierre `]:` (tras `('explotacion_id', 'INTEGER'),`):

```python
        ('explotacion_id', 'INTEGER'),
        ('sigpac_superficie_ha', 'REAL'),
        ('sigpac_verificado_en', 'TEXT'),
    ]:
        _add_col(c, 'parcelas', col, typ)
```

- [ ] **Step 2: Verificar la migración arrancando la app**

Run: `cd backend && python -c "import db; db.init_db(); c=db.get_db(); import sys; cols=[r[1] for r in c.execute('PRAGMA table_info(parcelas)').fetchall()]; print('sigpac_superficie_ha' in cols, 'sigpac_verificado_en' in cols); c.close()"`
Expected: `True True`

- [ ] **Step 3: Commit**

```bash
git add backend/db.py
git commit -m "feat(db): columnas sigpac_superficie_ha/sigpac_verificado_en en parcelas"
```

---

## Task 2: Helper puro `estado_sigpac` + test

**Files:**
- Create: `backend/tests/test_estado_sigpac.py`
- Modify: `backend/helpers.py` (añadir función al final)

- [ ] **Step 1: Escribir el test que falla**

Crea `backend/tests/test_estado_sigpac.py`:

```python
"""Test plano (sin pytest) del helper puro estado_sigpac.
Ejecutar: python backend/tests/test_estado_sigpac.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from helpers import estado_sigpac


def check(nombre, parcela, esperado_estado, esperado_diff):
    estado, diff = estado_sigpac(parcela)
    assert estado == esperado_estado, f"{nombre}: estado {estado!r} != {esperado_estado!r}"
    assert diff == esperado_diff, f"{nombre}: diff {diff!r} != {esperado_diff!r}"
    print(f"  OK {nombre}")


def run():
    check("sin_verificar",
          {'sigpac_verificado_en': None, 'sigpac_superficie_ha': None, 'superficie_ha': 10},
          'sin_verificar', None)
    check("no_encontrada",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': None, 'superficie_ha': 10},
          'no_encontrada', None)
    check("verde_igual",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': 10.0, 'superficie_ha': 10.0},
          'verde', 0.0)
    check("verde_dentro_5pct",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': 10.0, 'superficie_ha': 10.2},
          'verde', 2.0)
    check("verde_limite_5pct",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': 10.0, 'superficie_ha': 9.5},
          'verde', -5.0)
    check("ambar_fuera",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': 10.0, 'superficie_ha': 8.0},
          'ambar', -20.0)
    check("ambar_sin_declarada",
          {'sigpac_verificado_en': '2026-07-10', 'sigpac_superficie_ha': 10.0, 'superficie_ha': None},
          'ambar', None)
    print("TODOS OK")


if __name__ == '__main__':
    run()
```

- [ ] **Step 2: Ejecutar el test y ver que falla**

Run: `python backend/tests/test_estado_sigpac.py`
Expected: FALLA con `ImportError: cannot import name 'estado_sigpac' from 'helpers'`

- [ ] **Step 3: Implementar el helper**

Añade al final de `backend/helpers.py`:

```python
def estado_sigpac(parcela):
    """Deriva el estado del badge SIGPAC de una parcela (dict). Función pura, sin I/O.

    Devuelve (estado, diferencia_pct):
      - 'sin_verificar'  -> nunca se verificó (diferencia None)
      - 'no_encontrada'  -> verificada pero SIGPAC no dio superficie (diferencia None)
      - 'verde'          -> |declarada - sigpac| / sigpac <= 5%
      - 'ambar'          -> diferencia > 5% (o sin superficie declarada)
    diferencia_pct = (declarada - sigpac) / sigpac * 100, redondeada a 1 decimal.
    """
    if not parcela.get('sigpac_verificado_en'):
        return 'sin_verificar', None
    sig = parcela.get('sigpac_superficie_ha')
    if sig is None:
        return 'no_encontrada', None
    try:
        sig = float(sig)
    except (TypeError, ValueError):
        return 'no_encontrada', None
    if sig <= 0:
        return 'no_encontrada', None
    decl = parcela.get('superficie_ha')
    if decl in (None, ''):
        return 'ambar', None
    try:
        decl = float(decl)
    except (TypeError, ValueError):
        return 'ambar', None
    ratio = abs(decl - sig) / sig
    diff_pct = round((decl - sig) / sig * 100, 1)
    return ('verde' if ratio <= 0.05 else 'ambar'), diff_pct
```

- [ ] **Step 4: Ejecutar el test y ver que pasa**

Run: `python backend/tests/test_estado_sigpac.py`
Expected: imprime `OK ...` por cada caso y termina con `TODOS OK`

- [ ] **Step 5: Commit**

```bash
git add backend/helpers.py backend/tests/test_estado_sigpac.py
git commit -m "feat(sigpac): helper puro estado_sigpac + test"
```

---

## Task 3: Helper de superficie desde hubcloud (`superficie_sigpac_parcela`)

**Files:**
- Modify: `backend/blueprints/sigpac.py` (añadir tras el helper `_parcela_resuelve`, ~línea 111)

- [ ] **Step 1: Añadir el helper**

En `backend/blueprints/sigpac.py`, añade estas funciones justo después de `_parcela_resuelve` (línea 111). Usa `_sigpac_get`, `req_lib` y `logger`, ya presentes en el módulo:

```python
HUBCLOUD_FEATUREINFO = "https://sigpac-hubcloud.es/wms/ows"


def _recinto_bboxes(recintos_data):
    """Extrae [(num_recinto, (x1,y1,x2,y2)), ...] de la respuesta query/recintos (EPSG:4258)."""
    out = []
    for f in (recintos_data.get('features') or []):
        p = f.get('properties') or {}
        try:
            num = int(p.get('nombre'))
        except (TypeError, ValueError):
            continue
        bbox = (p.get('x1'), p.get('y1'), p.get('x2'), p.get('y2'))
        if all(v is not None for v in bbox):
            out.append((num, bbox))
    return out


def _superficie_featureinfo(prov, mun, pol, par, rec, bbox):
    """superficie_ha oficial de un recinto vía GetFeatureInfo en hubcloud, o None si falla."""
    x1, y1, x2, y2 = bbox
    cql = (f"provincia={prov} AND municipio={mun} AND poligono={pol} "
           f"AND parcela={par} AND recinto={rec}")
    params = {
        'service': 'WMS', 'version': '1.1.1', 'request': 'GetFeatureInfo',
        'layers': 'AU.Sigpac:recinto', 'query_layers': 'AU.Sigpac:recinto',
        'info_format': 'application/json', 'srs': 'EPSG:4258',
        'bbox': f"{x1},{y1},{x2},{y2}", 'width': 256, 'height': 256, 'x': 128, 'y': 128,
        'feature_count': 5, 'styles': '', 'CQL_FILTER': cql,
    }
    try:
        r = req_lib.get(HUBCLOUD_FEATUREINFO, params=params, timeout=10)
        r.raise_for_status()
        feats = (r.json() or {}).get('features') or []
        if not feats:
            return None
        val = (feats[0].get('properties') or {}).get('superficie_ha')
        return float(val) if val is not None else None
    except Exception as e:
        logger.warning("featureinfo %s/%s/%s/%s/%s: %s", prov, mun, pol, par, rec, e)
        return None


def superficie_sigpac_parcela(prov, mun, pol, par, recinto=None):
    """Superficie SIGPAC (ha) para el badge de verificación.

    - recinto informado -> superficie de ese recinto.
    - recinto vacío -> suma de todos los recintos del pol/par.

    Devuelve (superficie_ha|None, resultado) con resultado en:
      'ok'            -> superficie_ha es un float válido.
      'no_encontrada' -> el pol/par (o el recinto declarado) no existe en SIGPAC.
      'error'         -> fallo transitorio de FEGA (no se debe persistir).
    """
    # Validación defensiva: los identificadores van en URLs.
    for v in (prov, mun, pol, par):
        if not re.fullmatch(r'\d{1,6}', str(v or '')):
            return None, 'no_encontrada'

    data = _sigpac_get(f"{SIGPAC_BASE}/recintos/{prov}/{mun}/0/0/{pol}/{par}")
    if not isinstance(data, dict) or 'error' in data:
        return None, 'error'                      # FEGA caído / respuesta inválida
    bboxes = _recinto_bboxes(data)
    if not bboxes:
        return None, 'no_encontrada'              # pol/par no resuelve

    if recinto:
        try:
            rnum = int(recinto)
        except (TypeError, ValueError):
            return None, 'no_encontrada'
        objetivo = [(n, b) for (n, b) in bboxes if n == rnum]
        if not objetivo:
            return None, 'no_encontrada'          # recinto declarado inexistente
    else:
        objetivo = bboxes

    total = 0.0
    algun_ok = False
    for (n, b) in objetivo:
        ha = _superficie_featureinfo(prov, mun, pol, par, n, b)
        if ha is not None:
            total += ha
            algun_ok = True
    if not algun_ok:
        return None, 'error'                      # recintos existen pero FeatureInfo falló
    return round(total, 4), 'ok'
```

- [ ] **Step 2: Verificación manual contra SIGPAC real**

Con el venv del backend activo, ejecuta este snippet (parcela real de Manzanares 13/053/1/1, recinto 2 ≈ 2,992 ha):

Run:
```bash
cd backend && python -c "from blueprints.sigpac import superficie_sigpac_parcela; print(superficie_sigpac_parcela('13','053','1','1','2'))"
```
Expected: algo como `(2.992, 'ok')` (el valor exacto puede variar levemente). Un pol/par inexistente como `('13','053','1','9999',None)` debe dar `(None, 'no_encontrada')`.

- [ ] **Step 3: Commit**

```bash
git add backend/blueprints/sigpac.py
git commit -m "feat(sigpac): superficie oficial por recinto vía GetFeatureInfo hubcloud"
```

---

## Task 4: Endpoint `POST /api/parcelas/<id>/verificar-sigpac`

**Files:**
- Modify: `backend/blueprints/parcelas.py:4-10` (imports) y añadir ruta tras `manage_parcela` (~línea 156)

- [ ] **Step 1: Añadir imports**

En `backend/blueprints/parcelas.py`, amplía los imports de cabecera (líneas 4-10):

```python
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import login_required
from extensions import limiter
from db import get_db, one, dicts, is_pac_eligible
from helpers import get_uid, _to_real, get_active_explotacion_id, estado_sigpac
from blueprints.ia import _recalcular_patrones
from blueprints.sigpac import superficie_sigpac_parcela
```

- [ ] **Step 2: Añadir la ruta**

Añade esta función tras `manage_parcela` (después de la línea 155, antes de la ruta `/api/cultivos-campana`):

```python
@bp.route('/api/parcelas/<int:pid>/verificar-sigpac', methods=['POST'])
@login_required
@limiter.limit("60 per minute")
def verificar_sigpac(pid):
    """Contrasta la superficie de la parcela con SIGPAC y persiste el resultado."""
    uid = get_uid()
    conn = get_db()
    p = one(conn, "SELECT * FROM parcelas WHERE id=? AND user_id=?", (pid, uid))
    if not p:
        conn.close()
        return jsonify({"ok": False, "error": "Parcela no encontrada"}), 404

    prov, mun = p.get('provincia_cod'), p.get('municipio_cod')
    pol, par, rec = p.get('poligono'), p.get('parcela_num'), p.get('recinto')
    if not all([prov, mun, pol, par]):
        conn.close()
        return jsonify({"ok": False, "error": "La parcela no tiene datos SIGPAC completos"}), 400

    ha, resultado = superficie_sigpac_parcela(prov, mun, pol, par, rec)
    if resultado == 'error':
        conn.close()
        return jsonify({"ok": False, "error": "SIGPAC no disponible, inténtalo de nuevo"}), 503

    # resultado 'ok' (ha float) o 'no_encontrada' (ha None) -> ambos se persisten con timestamp.
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    conn.execute(
        "UPDATE parcelas SET sigpac_superficie_ha=?, sigpac_verificado_en=? WHERE id=? AND user_id=?",
        (ha, now, pid, uid),
    )
    conn.commit()
    row = one(conn, "SELECT * FROM parcelas WHERE id=? AND user_id=?", (pid, uid))
    conn.close()
    estado, diff = estado_sigpac(row)
    return jsonify({
        "ok": True, "estado": estado,
        "sigpac_superficie_ha": ha, "diferencia_pct": diff,
        "sigpac_verificado_en": now,
    })
```

- [ ] **Step 3: Verificación manual (servidor arrancado + sesión)**

Arranca el backend (`cd backend && python app.py`), abre la app, entra con un usuario y crea/ten una parcela con pol/par reales. Con el navegador logueado, en la consola del navegador (DevTools) ejecuta:

Run (en la consola del navegador, sustituye `<ID>` por el id de una parcela real):
```js
fetch('/api/parcelas/<ID>/verificar-sigpac', {method:'POST', credentials:'include'}).then(r=>r.json()).then(console.log)
```
Expected: `{ ok: true, estado: "verde"|"ambar"|"no_encontrada", sigpac_superficie_ha: <num|null>, diferencia_pct: <num|null>, ... }`

- [ ] **Step 4: Commit**

```bash
git add backend/blueprints/parcelas.py
git commit -m "feat(parcelas): endpoint verificar-sigpac (persiste superficie y estado)"
```

---

## Task 5: Enriquecer GET lista y GET detalle con el estado derivado

**Files:**
- Modify: `backend/blueprints/parcelas.py:48-55` (GET lista) y `:102-105` (GET detalle)

- [ ] **Step 1: Enriquecer el GET lista**

En `manage_parcelas`, sustituye el bloque GET (líneas 48-55) por:

```python
    if request.method == 'GET':
        exp_id = get_active_explotacion_id(conn)
        all_p = dicts(conn, "SELECT * FROM parcelas WHERE user_id=? AND explotacion_id=? AND activa=1 ORDER BY nombre_finca", (uid, exp_id))
        pac_only = request.args.get('pac_only', 'false').lower() == 'true'
        if pac_only:
            all_p = [p for p in all_p if is_pac_eligible(p.get('uso_sigpac', ''))]
        for p in all_p:
            estado, diff = estado_sigpac(p)
            p['sigpac_estado'] = estado
            p['sigpac_diferencia_pct'] = diff
        conn.close()
        return jsonify(all_p)
```

- [ ] **Step 2: Enriquecer el GET detalle**

En `manage_parcela`, sustituye el bloque GET (líneas 102-105) por:

```python
    if request.method == 'GET':
        row = one(conn, "SELECT * FROM parcelas WHERE id=? AND user_id=?", (pid, uid))
        conn.close()
        if row:
            estado, diff = estado_sigpac(row)
            row['sigpac_estado'] = estado
            row['sigpac_diferencia_pct'] = diff
        return jsonify(row or {})
```

- [ ] **Step 3: Verificación manual**

Run (consola del navegador logueado):
```js
fetch('/api/parcelas', {credentials:'include'}).then(r=>r.json()).then(d=>console.log(d.map(p=>[p.nombre_finca, p.sigpac_estado, p.sigpac_diferencia_pct])))
```
Expected: cada parcela muestra un `sigpac_estado` (`sin_verificar` si nunca se verificó) y `sigpac_diferencia_pct`.

- [ ] **Step 4: Commit**

```bash
git add backend/blueprints/parcelas.py
git commit -m "feat(parcelas): incluir sigpac_estado/diferencia_pct en GET lista y detalle"
```

---

## Task 6: Pill del badge en la lista de parcelas

**Files:**
- Modify: `frontend/screens_parcelas.jsx` (helper de badge a nivel módulo + uso en la tarjeta, ~línea 755)

- [ ] **Step 1: Añadir el helper de badge a nivel de módulo**

En `frontend/screens_parcelas.jsx`, justo antes de `function MapaSigpacModal` (línea 105), añade:

```javascript
// Pill de verificación SIGPAC. estado: 'verde'|'ambar'|'no_encontrada'|'sin_verificar'.
function sigpacBadge(estado) {
    const map = {
        verde:         { bg:'#dcfce7', fg:'#166534', bd:'#86efac', txt:'✓ Verificado' },
        ambar:         { bg:'#fef3c7', fg:'#92400e', bd:'#fde68a', txt:'⚠ Revisar' },
        no_encontrada: { bg:'#fef3c7', fg:'#92400e', bd:'#fde68a', txt:'⚠ No en SIGPAC' },
        sin_verificar: { bg:'#f3f4f6', fg:'#6b7280', bd:'#e5e7eb', txt:'Sin verificar' },
    };
    const s = map[estado];
    if (!s) return null;
    return (
        <span className="chip" style={{ background:s.bg, color:s.fg, border:`1px solid ${s.bd}`, fontSize:'0.7rem' }}>
            {s.txt}
        </span>
    );
}
```

- [ ] **Step 2: Mostrar el pill en la tarjeta de la lista**

En la fila de chips de la tarjeta (línea 755-764), añade el badge tras el chip de superficie. Sustituye el bloque:

```javascript
                                <div style={{ display:'flex', gap:6, marginTop:5, alignItems:'center', flexWrap:'wrap' }}>
                                    {pacLabel(p.uso_sigpac)}
                                    {p.superficie_ha ? <span className="chip chip-grey">{p.superficie_ha} ha</span> : null}
                                    {p.poligono && !p.uso_sigpac && (
                                        <span className="chip" style={{ background:'#fef3c7', color:'#92400e', border:'1px solid #fde68a', fontSize:'0.7rem' }}>⚠ Sin uso</span>
                                    )}
                                    {p.poligono && !p.superficie_ha && (
                                        <span className="chip" style={{ background:'#fef3c7', color:'#92400e', border:'1px solid #fde68a', fontSize:'0.7rem' }}>⚠ Sin sup.</span>
                                    )}
                                </div>
```

por (añade la última línea con `sigpacBadge`):

```javascript
                                <div style={{ display:'flex', gap:6, marginTop:5, alignItems:'center', flexWrap:'wrap' }}>
                                    {pacLabel(p.uso_sigpac)}
                                    {p.superficie_ha ? <span className="chip chip-grey">{p.superficie_ha} ha</span> : null}
                                    {p.poligono && !p.uso_sigpac && (
                                        <span className="chip" style={{ background:'#fef3c7', color:'#92400e', border:'1px solid #fde68a', fontSize:'0.7rem' }}>⚠ Sin uso</span>
                                    )}
                                    {p.poligono && !p.superficie_ha && (
                                        <span className="chip" style={{ background:'#fef3c7', color:'#92400e', border:'1px solid #fde68a', fontSize:'0.7rem' }}>⚠ Sin sup.</span>
                                    )}
                                    {p.poligono && sigpacBadge(p.sigpac_estado)}
                                </div>
```

- [ ] **Step 3: Compilar el JSX**

Run: `cd frontend && npm run build`
Expected: `Successfully compiled 15 files with Babel`

- [ ] **Step 4: Verificación manual**

Recarga la app (Ctrl+F5). En la lista de parcelas, cada parcela con datos SIGPAC muestra un pill "Sin verificar" (gris) mientras no se haya verificado.

- [ ] **Step 5: Commit**

```bash
git add frontend/screens_parcelas.jsx frontend/dist/screens_parcelas.js
git commit -m "feat(parcelas-ui): pill de verificación SIGPAC en la lista"
```

> Nota: `frontend/dist/` está en `.gitignore`; `git add` lo ignorará salvo que exista. No falla el commit si no se añade.

---

## Task 7: Badge + botón "Re-verificar" en la ficha

**Files:**
- Modify: `frontend/screens_parcelas.jsx` (estado nuevo cerca de `sigpacSyncing`; bloque UI en el tab 'parcela', ~línea 845)

- [ ] **Step 1: Añadir estado y handler de re-verificación**

Localiza la declaración de estado `sigpacSyncing` (búscala: `sigpacSyncing`). Junto a ella añade el estado de verificación:

```javascript
    const [verificando, setVerificando] = useState(false);
```

Y añade este handler junto a `syncSigpac` (misma zona de funciones del componente `ScreenParcelas`):

```javascript
    const reVerificarSigpac = async () => {
        if (!selected || !navigator.onLine) return;
        setVerificando(true);
        try {
            const r = await fetch(`/api/parcelas/${selected.id}/verificar-sigpac`, { method:'POST', credentials:'include' });
            const d = await r.json().catch(() => ({}));
            if (!r.ok || !d.ok) {
                showToast(`⚠️ ${d.error || 'No se pudo verificar con SIGPAC'}`);
            } else {
                setSelected(prev => prev ? { ...prev,
                    sigpac_superficie_ha: d.sigpac_superficie_ha,
                    sigpac_verificado_en: d.sigpac_verificado_en,
                    sigpac_estado: d.estado,
                    sigpac_diferencia_pct: d.diferencia_pct,
                } : prev);
                fetchParcelas();
            }
        } catch {
            showToast('⚠️ Error de conexión al verificar con SIGPAC');
        }
        setVerificando(false);
    };
```

- [ ] **Step 2: Añadir el bloque de badge en la ficha**

En el contenido del tab `parcela`, justo después del grid de campos (tras la línea 845, `</div>` que cierra el `.map(...)` grid, antes del botón "Ver mi parcela en el mapa" de la línea 846), inserta:

```javascript
                                {selected.poligono && selected.parcela_num && (
                                    <div style={{ background:'#f8f9fb', border:'1px solid #e5e7eb', borderRadius:10, padding:'12px 14px', marginBottom:12 }}>
                                        <div style={{ display:'flex', alignItems:'center', gap:8, flexWrap:'wrap' }}>
                                            <span style={{ fontSize:'0.7rem', fontWeight:700, color:'#6b7280', textTransform:'uppercase', letterSpacing:'0.05em' }}>Verificación SIGPAC</span>
                                            {sigpacBadge(selected.sigpac_estado)}
                                            <button onClick={reVerificarSigpac} disabled={verificando || !navigator.onLine}
                                                title={!navigator.onLine ? 'Necesitas conexión para verificar con SIGPAC' : ''}
                                                style={{ marginLeft:'auto', background:'#16a34a', border:'none', borderRadius:8, padding:'8px 12px', color:'#fff', cursor:(verificando||!navigator.onLine)?'default':'pointer', fontWeight:700, fontSize:'0.78rem', opacity:(verificando||!navigator.onLine)?0.6:1 }}>
                                                {verificando ? '…' : '↻ Re-verificar'}
                                            </button>
                                        </div>
                                        {selected.sigpac_superficie_ha != null && (
                                            <div style={{ fontSize:'0.78rem', color:'#374151', marginTop:8 }}>
                                                SIGPAC: <strong>{selected.sigpac_superficie_ha} ha</strong>
                                                {selected.superficie_ha ? <> · tu dato: {selected.superficie_ha} ha</> : null}
                                                {selected.sigpac_diferencia_pct != null ? <> ({selected.sigpac_diferencia_pct > 0 ? '+' : ''}{selected.sigpac_diferencia_pct}%)</> : null}
                                            </div>
                                        )}
                                        {selected.sigpac_estado === 'no_encontrada' && (
                                            <div style={{ fontSize:'0.78rem', color:'#92400e', marginTop:8 }}>
                                                SIGPAC no encuentra esta parcela. Revisa el polígono, la parcela y el recinto.
                                            </div>
                                        )}
                                    </div>
                                )}
```

- [ ] **Step 3: Compilar el JSX**

Run: `cd frontend && npm run build`
Expected: `Successfully compiled 15 files with Babel`

- [ ] **Step 4: Verificación manual**

Recarga (Ctrl+F5), abre una parcela con datos SIGPAC → aparece el bloque "Verificación SIGPAC" con el badge y el botón "↻ Re-verificar". Púlsalo: tras unos segundos el badge pasa a verde/ámbar/no_encontrada y aparece la línea "SIGPAC: X ha · tu dato: Y ha (±Z%)".

- [ ] **Step 5: Commit**

```bash
git add frontend/screens_parcelas.jsx frontend/dist/screens_parcelas.js
git commit -m "feat(parcelas-ui): badge y botón re-verificar SIGPAC en la ficha"
```

---

## Task 8: Auto-verificación tras guardar la parcela

**Files:**
- Modify: `frontend/screens_parcelas.jsx:640-669` (función `saveParcela`)

- [ ] **Step 1: Capturar el id y auto-verificar tras guardar**

Sustituye la función `saveParcela` (líneas 640-669) por esta versión (captura el id nuevo en POST y lanza la verificación tras guardar):

```javascript
    const saveParcela = async () => {
        if (!form.nombre_finca.trim()) {
            showToast('Escribe un nombre para la parcela');
            return;
        }
        setSaving(true);
        const method = editId ? 'PUT' : 'POST';
        const url = editId ? `/api/parcelas/${editId}` : '/api/parcelas';
        let savedId = editId;
        try {
            const res = await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(form), credentials: 'include' });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                showToast(`❌ Error al guardar: ${err.error || res.status}`);
                setSaving(false);
                return;
            }
            if (!editId) {
                const data = await res.json().catch(() => ({}));
                savedId = data.id;
            }
        } catch {
            showToast('❌ Error de conexión al guardar');
            setSaving(false);
            return;
        }
        showToast(editId ? '✅ Parcela actualizada' : '✅ Parcela añadida');
        setSaving(false); setShowForm(false);
        fetchParcelas();
        if (editId) {
            setSelected(prev => prev ? { ...prev, ...form, id: prev.id } : prev);
        } else {
            setSelected(null);
        }
        // Auto-verificación con SIGPAC (no bloquea; refresca badges al volver).
        if (savedId && form.poligono && form.parcela_num && navigator.onLine) {
            fetch(`/api/parcelas/${savedId}/verificar-sigpac`, { method:'POST', credentials:'include' })
                .then(() => fetchParcelas())
                .catch(() => {});
        }
    };
```

- [ ] **Step 2: Compilar el JSX**

Run: `cd frontend && npm run build`
Expected: `Successfully compiled 15 files with Babel`

- [ ] **Step 3: Verificación manual**

Recarga (Ctrl+F5). Crea una parcela nueva con pol/par reales y superficie. Al guardar, en unos segundos el pill de esa parcela en la lista pasa de "Sin verificar" a verde/ámbar automáticamente (sin pulsar nada).

- [ ] **Step 4: Commit**

```bash
git add frontend/screens_parcelas.jsx frontend/dist/screens_parcelas.js
git commit -m "feat(parcelas-ui): auto-verificar con SIGPAC tras guardar parcela"
```

---

## Task 9: Bump del service worker y verificación integral

**Files:**
- Modify: `frontend/service-worker.js:1`

- [ ] **Step 1: Subir CACHE_NAME**

En `frontend/service-worker.js`, línea 1, sube la versión a un valor **mayor** que el de `main` en el momento del merge. `main` está en `v31` y el PR #18 lo lleva a `v32`, así que usa `v33`:

```javascript
const CACHE_NAME = 'cuaderno-cache-v33';
```

Verifica antes el valor actual en `main`/PR #18 y usa el siguiente entero si difiere.

- [ ] **Step 2: Verificación integral de los 4 estados (navegador)**

Con el backend arrancado y la app recargada (Ctrl+F5):
1. **Verde:** parcela con superficie ≈ SIGPAC → tras guardar/re-verificar, pill verde "✓ Verificado" y línea con diferencia pequeña.
2. **Ámbar:** edita la superficie de una parcela a un valor > 5% distinto → re-verifica → pill "⚠ Revisar" con la diferencia.
3. **No encontrada:** parcela con un nº de parcela inexistente (p. ej. 9999) → re-verifica → "⚠ No en SIGPAC" y el texto de ayuda.
4. **Sin verificar / offline:** en DevTools pon la red en "Offline"; el badge sigue mostrando el último estado guardado y el botón "↻ Re-verificar" queda deshabilitado.

- [ ] **Step 3: Ejecutar el test del helper puro (regresión)**

Run: `python backend/tests/test_estado_sigpac.py`
Expected: `TODOS OK`

- [ ] **Step 4: Commit**

```bash
git add frontend/service-worker.js
git commit -m "chore(sw): bump CACHE_NAME a v33 (badge verificado SIGPAC)"
```

---

## Notas finales

- **Patrón BD:** todas las operaciones usan `get_db()` → operar → `commit()` → `close()` (sin context manager, `_PgConn` no lo soporta). Placeholders `?`.
- **PostgreSQL:** `_add_col` es idempotente (IF NOT EXISTS en PG / try-except en SQLite); el UPDATE del endpoint usa placeholders `?` (traducidos a `%s`). Tras deploy que toque `db.py`, exigir restart completo de gunicorn.
- **Compatibilidad SIEX:** cambios aditivos, superficie/uso de catálogos oficiales FEGA. Lenguaje UI "compatible con SIEX".
- **Fuera de alcance:** migrar el autorrelleno del formulario a la fuente hubcloud (PR posterior); contrastar uso/municipio; aviso multi-recinto → UHC (#6).
