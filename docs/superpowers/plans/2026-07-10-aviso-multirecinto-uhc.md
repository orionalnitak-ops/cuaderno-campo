# Aviso multi-recinto → UHC — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Al dar de alta una parcela SIGPAC con 2+ recintos, permitir crear una parcela por recinto y agrupar los recintos del mismo uso en UHCs, con resumen confirmable en lenguaje llano y creación transaccional.

**Architecture:** Un validador puro en `helpers.py` (testeable sin Flask), un endpoint transaccional nuevo `POST /api/parcelas/alta-multirecinto` en `blueprints/parcelas.py` (commit único), y en el frontend una opción "Crear todas" en el picker de recintos existente que abre un modal de resumen confirmable antes de la única llamada al backend.

**Tech Stack:** Flask + capa `db.py` (SQLite/PG dual), React sin build en dev (JSX + Babel Standalone), tests planos en Python (sin pytest, patrón `backend/tests/test_estado_sigpac.py`).

**Spec:** `docs/superpowers/specs/2026-07-10-aviso-multirecinto-uhc-design.md`
**Rama:** `feat/aviso-multirecinto-uhc` (ya creada, contiene la spec)

**Reglas del proyecto que aplican aquí:**
- Placeholders `?` siempre; jamás f-strings en SQL.
- Patrón BD: `get_db()` → operaciones → `conn.commit()` → `conn.close()`. Sin `with conn:`.
- Rutas solo en blueprints, nunca en `app.py`.
- Toda query filtra por `user_id`.
- API: `{"ok": true, "data": ...}` / `{"ok": false, "error": "mensaje legible"}`.
- Tras editar JSX: `npm run build` en `frontend/`.
- Todo cambio de frontend: bump `CACHE_NAME` en `frontend/service-worker.js` (actual: `v33` → pasar a `v34`).
- Lenguaje UI: "compatible con SIEX", nunca "integración/subida a SIEX". Copy en lenguaje llano: "trozos" y "grupo" como palabras principales, "recinto"/"UHC" entre paréntesis.

---

### Task 1: Validador puro `validar_alta_multirecinto` en `helpers.py`

Valida y normaliza el payload del endpoint nuevo. Es una función pura (sin BD ni Flask) para poder testearla con un test plano.

**Files:**
- Modify: `backend/helpers.py` (añadir función al final)
- Create: `backend/tests/test_alta_multirecinto.py`

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_alta_multirecinto.py`:

```python
"""Test plano (sin pytest) del validador puro validar_alta_multirecinto.
Ejecutar: python backend/tests/test_alta_multirecinto.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from helpers import validar_alta_multirecinto


def check_ok(nombre, data, esperado):
    norm, err = validar_alta_multirecinto(data)
    assert err is None, f"{nombre}: error inesperado {err!r}"
    assert norm == esperado, f"{nombre}:\n  got  {norm!r}\n  want {esperado!r}"
    print(f"  OK {nombre}")


def check_err(nombre, data, fragmento):
    norm, err = validar_alta_multirecinto(data)
    assert norm is None, f"{nombre}: se esperaba error, llegó {norm!r}"
    assert fragmento in err, f"{nombre}: {fragmento!r} no está en {err!r}"
    print(f"  OK {nombre}")


def run():
    base = {
        'nombre_base': 'La Vega',
        'recintos': [
            {'num': 1, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': '1,2'},
            {'num': 2, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': 2.1},
            {'num': 3, 'uso_sigpac': 'PS-Pasto', 'superficie_ha': None},
        ],
        'uhcs': [{'nombre': 'Olivar — Pol 4 Par 12', 'cultivo': 'Olivar', 'recintos': [2, 1]}],
    }
    check_ok("payload_completo", base, {
        'nombre_base': 'La Vega', 'campana': '2025/2026',
        'recintos': [
            {'num': 1, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': 1.2},
            {'num': 2, 'uso_sigpac': 'OV-Olivar', 'superficie_ha': 2.1},
            {'num': 3, 'uso_sigpac': 'PS-Pasto', 'superficie_ha': None},
        ],
        'uhcs': [{'nombre': 'Olivar — Pol 4 Par 12', 'cultivo': 'Olivar', 'recintos': [1, 2]}],
    })
    check_ok("sin_uhcs", {'nombre_base': 'X', 'recintos': [{'num': 5, 'uso_sigpac': '', 'superficie_ha': ''}]},
             {'nombre_base': 'X', 'campana': '2025/2026',
              'recintos': [{'num': 5, 'uso_sigpac': '', 'superficie_ha': None}], 'uhcs': []})

    check_err("sin_nombre", {'nombre_base': '  ', 'recintos': [{'num': 1}]}, "nombre")
    check_err("sin_recintos", {'nombre_base': 'X', 'recintos': []}, "trozos")
    check_err("num_invalido", {'nombre_base': 'X', 'recintos': [{'num': 'a'}]}, "inválido")
    check_err("num_repetido", {'nombre_base': 'X', 'recintos': [{'num': 1}, {'num': 1}]}, "repetidos")
    check_err("superficie_negativa", {'nombre_base': 'X', 'recintos': [{'num': 1, 'superficie_ha': -1}]}, "mayor que cero")
    check_err("campana_mala", {'nombre_base': 'X', 'campana': '2025', 'recintos': [{'num': 1}]}, "YYYY/YYYY")
    check_err("uhc_sin_nombre", {'nombre_base': 'X', 'recintos': [{'num': 1}, {'num': 2}],
                                 'uhcs': [{'nombre': '', 'recintos': [1, 2]}]}, "nombre del grupo")
    check_err("uhc_un_solo_trozo", {'nombre_base': 'X', 'recintos': [{'num': 1}, {'num': 2}],
                                    'uhcs': [{'nombre': 'G', 'recintos': [1]}]}, "al menos 2")
    check_err("uhc_trozo_fantasma", {'nombre_base': 'X', 'recintos': [{'num': 1}, {'num': 2}],
                                     'uhcs': [{'nombre': 'G', 'recintos': [1, 9]}]}, "no se van a crear")
    print("TODOS OK")


if __name__ == '__main__':
    run()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "H:\Proyectos\Cuaderno ex app" ; python backend/tests/test_alta_multirecinto.py`
Expected: FAIL con `ImportError: cannot import name 'validar_alta_multirecinto'`

- [ ] **Step 3: Write minimal implementation**

Añadir al final de `backend/helpers.py` (comprobar que el módulo ya tiene `import re` arriba; si no, añadirlo junto a los demás imports):

```python
_CAMPANA_RE = re.compile(r'^\d{4}/\d{4}$')


def validar_alta_multirecinto(data):
    """Valida y normaliza el payload de POST /api/parcelas/alta-multirecinto.

    Devuelve (norm, None) si es válido o (None, "mensaje legible") si no.
    norm: {nombre_base, campana, recintos:[{num:int, uso_sigpac:str, superficie_ha:float|None}],
           uhcs:[{nombre:str, cultivo:str, recintos:[int]}]}
    """
    data = data or {}
    nombre_base = (data.get('nombre_base') or '').strip()
    if not nombre_base:
        return None, "El nombre de la finca es obligatorio"

    campana = str(data.get('campana') or '2025/2026')
    if not _CAMPANA_RE.match(campana):
        return None, "La campaña debe tener formato YYYY/YYYY (ej: 2025/2026)"

    raw = data.get('recintos')
    if not isinstance(raw, list) or not raw:
        return None, "Hacen falta los trozos (recintos) que se van a crear"

    recintos, vistos = [], set()
    for r in raw:
        r = r or {}
        try:
            num = int(r.get('num'))
        except (TypeError, ValueError):
            return None, "Número de trozo (recinto) inválido"
        if num <= 0:
            return None, "Número de trozo (recinto) inválido"
        if num in vistos:
            return None, "Hay trozos (recintos) repetidos"
        vistos.add(num)
        sup = r.get('superficie_ha')
        if sup is None or sup == '':
            sup = None
        else:
            try:
                sup = float(str(sup).replace(',', '.'))
            except (TypeError, ValueError):
                return None, f"Superficie inválida en el trozo {num}"
            if sup <= 0:
                return None, f"La superficie del trozo {num} debe ser mayor que cero"
        recintos.append({'num': num, 'uso_sigpac': (r.get('uso_sigpac') or '').strip(),
                         'superficie_ha': sup})

    uhcs = []
    for u in (data.get('uhcs') or []):
        u = u or {}
        nombre = (u.get('nombre') or '').strip()
        if not nombre:
            return None, "El nombre del grupo es obligatorio"
        try:
            nums = sorted({int(n) for n in (u.get('recintos') or [])})
        except (TypeError, ValueError):
            return None, f"El grupo '{nombre}' tiene trozos inválidos"
        if len(nums) < 2:
            return None, f"El grupo '{nombre}' necesita al menos 2 trozos"
        if not set(nums) <= vistos:
            return None, f"El grupo '{nombre}' incluye trozos que no se van a crear"
        uhcs.append({'nombre': nombre, 'cultivo': (u.get('cultivo') or '').strip(),
                     'recintos': nums})

    return {'nombre_base': nombre_base, 'campana': campana,
            'recintos': recintos, 'uhcs': uhcs}, None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python backend/tests/test_alta_multirecinto.py`
Expected: `TODOS OK`

También regresión del test existente: `python backend/tests/test_estado_sigpac.py` → `TODOS OK`

- [ ] **Step 5: Commit**

```bash
git add backend/helpers.py backend/tests/test_alta_multirecinto.py
git commit -m "feat(parcelas): validador puro del alta multi-recinto (Bloque 2 #6)"
```

---

### Task 2: Endpoint transaccional `POST /api/parcelas/alta-multirecinto`

**Files:**
- Modify: `backend/blueprints/parcelas.py` (añadir ruta después de `verificar_sigpac`, ~línea 207)

- [ ] **Step 1: Añadir el import del validador**

En `backend/blueprints/parcelas.py`, la línea de imports de helpers (línea 11) pasa a:

```python
from helpers import get_uid, _to_real, get_active_explotacion_id, estado_sigpac, validar_alta_multirecinto
```

- [ ] **Step 2: Implementar la ruta**

Añadir después de la función `verificar_sigpac` (antes de `@bp.route('/api/cultivos-campana', ...)`):

```python
@bp.route('/api/parcelas/alta-multirecinto', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def alta_multirecinto():
    """Crea una parcela por recinto y las UHC aceptadas, todo o nada (commit único)."""
    data = request.json or {}
    norm, err = validar_alta_multirecinto(data)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    poligono = str(data.get('poligono') or '').strip()
    parcela_num = str(data.get('parcela_num') or '').strip()
    if not poligono or not parcela_num:
        return jsonify({"ok": False, "error": "Faltan el polígono y la parcela SIGPAC"}), 400

    uid = get_uid()
    conn = get_db()
    try:
        exp_id = get_active_explotacion_id(conn)

        # Duplicados: si ya existe alguno de los recintos, no se crea nada.
        for r in norm['recintos']:
            ya = one(conn, """SELECT id FROM parcelas
                              WHERE user_id=? AND explotacion_id=? AND poligono=?
                                AND parcela_num=? AND recinto=? AND activa=1""",
                     (uid, exp_id, poligono, parcela_num, str(r['num'])))
            if ya:
                return jsonify({"ok": False,
                                "error": f"Ya tienes registrado el trozo {r['num']} de esa parcela"}), 400

        c = conn.cursor()
        ids_por_num = {}
        for r in norm['recintos']:
            c.execute('''
                INSERT INTO parcelas (
                    user_id, explotacion_id, comunidad, provincia_cod, provincia_nombre,
                    municipio_cod, municipio_nombre, nombre_finca,
                    poligono, parcela_num, recinto, superficie_ha, uso_sigpac, referencia_cat,
                    sistema_explotacion, masa_agua_cercana, notas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                uid, exp_id, data.get('comunidad'), data.get('provincia_cod'), data.get('provincia_nombre'),
                data.get('municipio_cod'), data.get('municipio_nombre'),
                f"{norm['nombre_base']} — R{r['num']}",
                poligono, parcela_num, str(r['num']),
                r['superficie_ha'], r['uso_sigpac'], '',
                data.get('sistema_explotacion', 'Secano'), 0, '',
            ))
            ids_por_num[r['num']] = c.lastrowid

        for u in norm['uhcs']:
            c.execute(
                "INSERT INTO unidades_homogeneas (user_id, nombre, cultivo, campana, notas) VALUES (?,?,?,?,?)",
                (uid, u['nombre'], u['cultivo'], norm['campana'], '')
            )
            uhc_id = c.lastrowid
            for num in u['recintos']:
                c.execute(
                    "INSERT OR IGNORE INTO uhc_parcelas (uhc_id, parcela_id) VALUES (?,?)",
                    (uhc_id, ids_por_num[num])
                )

        conn.commit()
        return jsonify({"ok": True, "data": {"parcelas": len(norm['recintos']),
                                             "uhcs": len(norm['uhcs'])}}), 201
    finally:
        conn.close()
```

Notas para el implementador:
- El `try/finally` con `conn.close()` garantiza el cierre; al no hacer `commit()` si algo lanza, la transacción se descarta (rollback implícito) — es exactamente el "todo o nada" de la spec.
- `INSERT OR IGNORE` en `uhc_parcelas` replica el patrón ya existente en `blueprints/uhc.py:63`.
- No usar `with conn:` (la capa `_PgConn` no lo implementa).

- [ ] **Step 3: Smoke test manual del endpoint**

Arrancar el servidor (`cd backend ; python app.py`) y comprobar que arranca sin errores de import. Con la app abierta en `http://127.0.0.1:5000` y sesión iniciada, en la consola del navegador:

```js
fetch('/api/parcelas/alta-multirecinto', {
  method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'include',
  body: JSON.stringify({
    nombre_base: 'PRUEBA MULTI', poligono: '999', parcela_num: '999',
    provincia_cod: '13', municipio_cod: '034',
    recintos: [{num: 1, uso_sigpac: 'OV-Olivar', superficie_ha: 1.2},
               {num: 2, uso_sigpac: 'OV-Olivar', superficie_ha: 2.1}],
    uhcs: [{nombre: 'PRUEBA GRUPO', cultivo: 'Olivar', recintos: [1, 2]}]
  })
}).then(r => r.json()).then(console.log)
```

Expected: `{ok: true, data: {parcelas: 2, uhcs: 1}}`. Repetir la misma llamada → `{ok: false, error: "Ya tienes registrado el trozo 1 de esa parcela"}` (status 400). Después borrar las 2 parcelas de prueba y el grupo desde la UI.

- [ ] **Step 4: Commit**

```bash
git add backend/blueprints/parcelas.py
git commit -m "feat(parcelas): endpoint transaccional POST /api/parcelas/alta-multirecinto"
```

---

### Task 3: Frontend — opción "Crear todas" en el picker + estado del resumen

**Files:**
- Modify: `frontend/screens_parcelas.jsx`

- [ ] **Step 1: Añadir estado y helpers**

Justo después de la línea 418 (`// null | { mode:'detail'|'form', ... }`), añadir:

```jsx
    const [resumenMulti, setResumenMulti] = useState(null);
    // null | { ctx, recs, grupos:[{uso, nums, nombre, aceptado}], creando:bool }

    // "OV-Olivar" → "Olivar" (mismo criterio que el picker, línea ~1383)
    const usoLabel = u => ((u || '').split('-').slice(1).join('-').trim() || u || '');

    // Agrupa recintos por uso SIGPAC; solo grupos de 2+ generan UHC propuesta.
    const abrirResumenMulti = () => {
        const ctx = recintosPicker;
        const recs = ctx.recintos || [];
        const by = new Map();
        recs.forEach(r => {
            const uso = (r.uso_sigpac || '').trim();
            if (!uso) return;
            if (!by.has(uso)) by.set(uso, []);
            by.get(uso).push(r.num);
        });
        const grupos = [...by.entries()]
            .filter(([, nums]) => nums.length >= 2)
            .map(([uso, nums]) => ({
                uso, nums,
                nombre: `${usoLabel(uso)} — Pol ${ctx.poligono} Par ${ctx.parcela}`,
                aceptado: true,
            }));
        setRecintosPicker(null);
        setResumenMulti({ ctx, recs, grupos, creando: false });
    };

    const confirmarMultirecinto = async () => {
        const rm = resumenMulti;
        if (rm.grupos.some(g => g.aceptado && !g.nombre.trim())) {
            showToast('Ponle un nombre a cada grupo (o desmárcalo)');
            return;
        }
        setResumenMulti(r => ({ ...r, creando: true }));
        const body = {
            nombre_base: (form.nombre_finca || '').trim() || `Pol ${rm.ctx.poligono} Par ${rm.ctx.parcela}`,
            comunidad: form.comunidad,
            provincia_cod: rm.ctx.provCod, provincia_nombre: form.provincia_nombre,
            municipio_cod: rm.ctx.munCod, municipio_nombre: form.municipio_nombre,
            poligono: rm.ctx.poligono, parcela_num: rm.ctx.parcela,
            sistema_explotacion: form.sistema_explotacion || 'Secano',
            recintos: rm.recs.map(r => ({ num: r.num, uso_sigpac: r.uso_sigpac || '', superficie_ha: r.superficie_ha })),
            uhcs: rm.grupos.filter(g => g.aceptado)
                .map(g => ({ nombre: g.nombre.trim(), cultivo: usoLabel(g.uso), recintos: g.nums })),
        };
        try {
            const res = await fetch('/api/parcelas/alta-multirecinto', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body), credentials: 'include',
            });
            const d = await res.json().catch(() => ({}));
            if (!res.ok || !d.ok) {
                showToast(`⚠️ ${d.error || 'No se pudieron crear las parcelas'}`);
                setResumenMulti(r => r ? { ...r, creando: false } : r);
                return;
            }
            setResumenMulti(null);
            setShowForm(false);
            fetchParcelas();
            const np = d.data?.parcelas || 0, ng = d.data?.uhcs || 0;
            showToast(`✅ Creadas ${np} parcelas${ng ? ` y ${ng} grupo${ng > 1 ? 's' : ''}` : ''}`);
        } catch {
            showToast('Error de conexión');
            setResumenMulti(r => r ? { ...r, creando: false } : r);
        }
    };
```

- [ ] **Step 2: Añadir el botón "Crear todas" al picker**

En el modal del picker (línea ~1390), justo ANTES del bloque `{!supIndividual && (` que muestra la nota de superficie, insertar (solo en modo `form`):

```jsx
                            {recintosPicker.mode === 'form' && recs.length > 1 && (
                                <button onClick={abrirResumenMulti} style={{
                                    width:'100%', padding:'14px 20px', marginBottom:12,
                                    background:'#00694c', border:'none', borderRadius:12,
                                    color:'#fff', fontWeight:800, fontSize:'1rem', cursor:'pointer',
                                }}>
                                    ➕ Crear todas ({recs.length} trozos)
                                </button>
                            )}
```

- [ ] **Step 3: Verificar sintaxis compilando**

Run: `cd frontend ; npm run build`
Expected: build sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/screens_parcelas.jsx
git commit -m "feat(parcelas): opción 'Crear todas' en el picker de recintos (alta multi-recinto)"
```

---

### Task 4: Frontend — modal de resumen confirmable (lenguaje llano)

**Files:**
- Modify: `frontend/screens_parcelas.jsx`

- [ ] **Step 1: Añadir el modal del resumen**

Justo DESPUÉS del bloque completo del picker `{recintosPicker && (() => { ... })()}` (que termina en la línea ~1406), añadir al mismo nivel:

```jsx
            {resumenMulti && (() => {
                const rm = resumenMulti;
                const fmtSup = s => s != null ? (s >= 1 ? `${s.toFixed(4)} ha` : `${Math.round(s * 10000)} m²`) : '—';
                const sinGrupos = rm.grupos.length === 0;
                const setGrupo = (i, patch) => setResumenMulti(r => ({
                    ...r, grupos: r.grupos.map((g, j) => j === i ? { ...g, ...patch } : g),
                }));
                return (
                    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.55)', zIndex:9999,
                        display:'flex', alignItems:'flex-end', justifyContent:'center' }}
                        onClick={() => !rm.creando && setResumenMulti(null)}>
                        <div style={{ background:'#fff', borderRadius:'20px 20px 0 0', padding:'24px 20px 32px',
                            width:'100%', maxWidth:480, maxHeight:'88vh', overflowY:'auto' }}
                            onClick={e => e.stopPropagation()}>

                            <div style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', color:'#1a2e1a', textAlign:'center' }}>
                                Vamos a crear {rm.recs.length} parcelas
                            </div>
                            <div style={{ color:'#6b7280', fontSize:'0.83rem', textAlign:'center', marginTop:4, marginBottom:14 }}>
                                Pol {rm.ctx.poligono} / Par {rm.ctx.parcela} — una parcela por cada trozo (recinto)
                            </div>

                            <div style={{ display:'flex', flexDirection:'column', gap:6, marginBottom:16 }}>
                                {rm.recs.map(r => (
                                    <div key={r.num} style={{ display:'flex', justifyContent:'space-between',
                                        padding:'10px 14px', background:'#f9fafb', borderRadius:10, fontSize:'0.9rem' }}>
                                        <span style={{ fontWeight:700, color:'#1a2e1a' }}>Trozo {r.num}</span>
                                        <span style={{ color:'#6b7280' }}>
                                            {usoLabel(r.uso_sigpac) || 'Sin uso conocido'} · {fmtSup(r.superficie_ha)}
                                        </span>
                                    </div>
                                ))}
                            </div>

                            {sinGrupos ? (
                                <div style={{ background:'#f0fdf4', borderRadius:12, padding:'14px 16px',
                                    fontSize:'0.85rem', color:'#374151', lineHeight:1.5, marginBottom:16 }}>
                                    Cada trozo tiene un cultivo distinto, así que no hay nada que agrupar.
                                    Se crearán las {rm.recs.length} parcelas por separado.
                                </div>
                            ) : (
                                <div style={{ background:'#f0fdf4', borderRadius:12, padding:'16px', marginBottom:16 }}>
                                    <div style={{ fontWeight:800, fontSize:'1rem', color:'#1a2e1a', marginBottom:8 }}>
                                        ¿Juntamos los trozos que se trabajan igual?
                                    </div>
                                    <div style={{ fontSize:'0.83rem', color:'#374151', lineHeight:1.55 }}>
                                        <p style={{ margin:'0 0 8px' }}>
                                            Los trozos que tienen <b>el mismo cultivo</b> puedes juntarlos en un <b>grupo</b>.
                                            <b> ¿Qué ganas con eso?</b> Que las faenas se apuntan <b>una sola vez</b>:
                                        </p>
                                        <ul style={{ margin:'0 0 8px', paddingLeft:18 }}>
                                            <li>Si sulfatas el olivar, apuntas el tratamiento <b>una vez</b> y queda
                                                registrado en todos los trozos del grupo a la vez. Sin grupo, tendrías
                                                que apuntarlo trozo por trozo.</li>
                                            <li>Lo mismo con el abonado y las labores: una anotación vale para todo el grupo.</li>
                                            <li>Tu cuaderno queda igual de completo y correcto ante una inspección:
                                                cada trozo tiene sus datos, solo que tú escribes menos.</li>
                                        </ul>
                                        <p style={{ margin:0 }}>
                                            A ese grupo la administración lo llama "Unidad Homogénea de Cultivo (UHC)".
                                            Para ti es, simplemente, un grupo de trozos que se trabajan igual. Tú decides:
                                            agrúpalos ahora o déjalos sueltos (podrás agruparlos más adelante desde la
                                            pantalla de Grupos).
                                        </p>
                                    </div>
                                </div>
                            )}

                            {rm.grupos.map((g, i) => (
                                <div key={g.uso} style={{ border:'2px solid ' + (g.aceptado ? '#00694c' : '#e5e7eb'),
                                    borderRadius:12, padding:'14px 16px', marginBottom:12 }}>
                                    <div style={{ fontSize:'0.8rem', color:'#6b7280', marginBottom:6 }}>
                                        Junta los trozos {g.nums.join(', ')} ({usoLabel(g.uso)})
                                    </div>
                                    <input value={g.nombre} disabled={!g.aceptado || rm.creando}
                                        onChange={e => setGrupo(i, { nombre: e.target.value })}
                                        style={{ width:'100%', padding:'12px', borderRadius:8, fontSize:'1rem',
                                            border:'1px solid #d1d5db', marginBottom:10, boxSizing:'border-box' }} />
                                    <div style={{ display:'flex', gap:8 }}>
                                        <button onClick={() => setGrupo(i, { aceptado: true })} style={{
                                            flex:1, padding:'12px', borderRadius:10, fontWeight:700, cursor:'pointer',
                                            border:'2px solid #00694c', fontSize:'0.9rem',
                                            background: g.aceptado ? '#00694c' : '#fff',
                                            color: g.aceptado ? '#fff' : '#00694c' }}>
                                            Sí, agrupar
                                        </button>
                                        <button onClick={() => setGrupo(i, { aceptado: false })} style={{
                                            flex:1, padding:'12px', borderRadius:10, fontWeight:700, cursor:'pointer',
                                            border:'2px solid ' + (!g.aceptado ? '#6b7280' : '#e5e7eb'), fontSize:'0.9rem',
                                            background: !g.aceptado ? '#6b7280' : '#fff',
                                            color: !g.aceptado ? '#fff' : '#9ca3af' }}>
                                            No, dejar sueltos
                                        </button>
                                    </div>
                                </div>
                            ))}

                            <button onClick={confirmarMultirecinto} disabled={rm.creando} style={{
                                width:'100%', padding:'15px', background: rm.creando ? '#9ca3af' : '#00694c',
                                border:'none', borderRadius:12, color:'#fff', fontWeight:800,
                                fontSize:'1.05rem', cursor: rm.creando ? 'wait' : 'pointer', marginBottom:10 }}>
                                {rm.creando ? 'Creando…' : '✓ Confirmar y crear'}
                            </button>
                            <button onClick={() => setResumenMulti(null)} disabled={rm.creando} style={{
                                width:'100%', padding:'13px', background:'#f3f4f6', border:'none',
                                borderRadius:10, color:'#6b7280', fontWeight:600, cursor:'pointer', fontSize:'0.9rem' }}>
                                Cancelar
                            </button>
                        </div>
                    </div>
                );
            })()}
```

- [ ] **Step 2: Compilar**

Run: `cd frontend ; npm run build`
Expected: build sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/screens_parcelas.jsx
git commit -m "feat(parcelas): resumen confirmable multi-recinto con grupos UHC en lenguaje llano"
```

---

### Task 5: Bump del service worker

**Files:**
- Modify: `frontend/service-worker.js:1`

- [ ] **Step 1: Subir la versión de caché**

```js
const CACHE_NAME = 'cuaderno-cache-v34';
```

(era `v33`; regla dura del proyecto: todo cambio de frontend sube `CACHE_NAME` o la PWA sirve el bundle viejo)

- [ ] **Step 2: Commit**

```bash
git add frontend/service-worker.js
git commit -m "chore(sw): bump CACHE_NAME a v34 (alta multi-recinto)"
```

---

### Task 6: Verificación manual end-to-end y PR

- [ ] **Step 1: Prueba manual del flujo completo**

Con el servidor local corriendo (`cd backend ; python app.py`, abrir `http://127.0.0.1:5000`):

1. Nueva parcela → rellenar provincia/municipio/polígono/parcela de una parcela real multi-recinto (usar una de la finca de Lourdes) → "Buscar en SIGPAC".
2. El picker muestra los recintos + el botón "➕ Crear todas (N trozos)".
3. Pulsar "Crear todas" → aparece el resumen: tabla de trozos, explicación, grupos propuestos por uso con nombre editable.
4. Editar el nombre de un grupo, desmarcar otro grupo ("No, dejar sueltos") → Confirmar.
5. Verificar: toast de éxito, la lista muestra las N parcelas nuevas (`{nombre} — R{num}`), y en la pantalla de UHC/Grupos aparece el grupo aceptado con sus parcelas.
6. Repetir el alta con la misma parcela → error legible "Ya tienes registrado el trozo…", nada creado.
7. Regresión: alta de una parcela mono-recinto (flujo directo sin picker) y elección de un recinto individual en el picker → igual que antes.
8. Regresión: `python backend/tests/test_alta_multirecinto.py` y `python backend/tests/test_estado_sigpac.py` → `TODOS OK`.

- [ ] **Step 2: Limpiar datos de prueba** (borrar parcelas y grupos creados en la prueba desde la UI)

- [ ] **Step 3: Push y PR**

```bash
git push -u origin feat/aviso-multirecinto-uhc
gh pr create --title "feat(parcelas): alta multi-recinto con grupos UHC (Bloque 2 #6)" --body "..."
```

El body del PR debe resumir: qué hace, decisiones de la spec, cómo se probó, y terminar con la línea `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Esperar CI (lint + bandit) + security review antes de merge.
