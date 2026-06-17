// ── Field Zoom Overlay — campo a pantalla grande para móvil ──
function FieldZoomOverlay({ label, value, type, inputMode, placeholder, multiline, onConfirm, onClose }) {
    const [val, setVal] = React.useState(value || '');
    const inputRef = React.useRef(null);

    React.useEffect(() => {
        setTimeout(() => { if (inputRef.current) inputRef.current.focus(); }, 80);
    }, []);

    const isDecimal = inputMode === 'decimal' || type === 'number';
    const confirm = () => {
        let v = typeof val === 'string' ? val.trim() : val;
        if (isDecimal) v = v.replace(',', '.');
        onConfirm(v);
    };

    const inputStyle = {
        width: '100%', boxSizing: 'border-box',
        fontSize: '1.25rem', fontFamily: 'Manrope, Work Sans, sans-serif',
        fontWeight: 600, padding: '16px 18px',
        border: '2px solid #1D9E75', borderRadius: 14,
        outline: 'none', background: '#f0fdf4', color: '#111827',
    };

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 999,
            background: 'rgba(0,0,0,0.65)',
            display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        }} onClick={onClose}>
            <div style={{
                background: '#fff', borderRadius: '0 0 24px 24px',
                width: '100%', maxWidth: 640,
                boxShadow: '0 8px 40px rgba(0,0,0,0.35)',
            }} onClick={e => e.stopPropagation()}>
                <div style={{ background: 'linear-gradient(135deg, #1D9E75, #00694c)', padding: '24px 20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <div style={{ fontSize: '0.68rem', color: 'rgba(255,255,255,0.6)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
                                Editando
                            </div>
                            <h2 style={{ fontFamily: 'Manrope', fontWeight: 800, color: '#fff', fontSize: '1.3rem', margin: 0 }}>
                                {label}
                            </h2>
                        </div>
                        <button onClick={onClose} style={{
                            background: 'rgba(255,255,255,0.15)', border: 'none', borderRadius: '50%',
                            width: 36, height: 36, color: '#fff', cursor: 'pointer', fontSize: 18,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>✕</button>
                    </div>
                </div>
                <div style={{ padding: '28px 20px 16px' }}>
                    {multiline ? (
                        <textarea
                            ref={inputRef}
                            value={val}
                            onChange={e => setVal(e.target.value)}
                            placeholder={placeholder}
                            rows={5}
                            style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.5 }}
                        />
                    ) : (
                        <input
                            ref={inputRef}
                            type="text"
                            inputMode={inputMode || (type === 'number' ? 'decimal' : undefined)}
                            value={val}
                            onChange={e => setVal(e.target.value)}
                            placeholder={placeholder}
                            onKeyDown={e => { if (e.key === 'Enter') confirm(); if (e.key === 'Escape') onClose(); }}
                            style={inputStyle}
                        />
                    )}
                </div>
                <div style={{ padding: '0 20px 28px' }}>
                    <button className="btn-primary" onClick={confirm} style={{ width: '100%', fontSize: '1rem', padding: '16px', minHeight: 52 }}>
                        ✓ Listo
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── ZoomInput — wrapper que abre FieldZoomOverlay al tocar ──
function ZoomInput({ label, value, type, inputMode, placeholder, multiline, style, onConfirm }) {
    const [open, setOpen] = React.useState(false);
    const sharedStyle = { cursor: 'pointer', ...(style || {}) };

    return (
        <>
            {multiline ? (
                <textarea
                    className="input-field"
                    value={value || ''}
                    readOnly
                    placeholder={placeholder}
                    rows={3}
                    onClick={() => setOpen(true)}
                    style={sharedStyle}
                />
            ) : (
                <input
                    type={type || 'text'}
                    inputMode={inputMode}
                    className="input-field"
                    value={value || ''}
                    readOnly
                    placeholder={placeholder}
                    onClick={() => setOpen(true)}
                    style={sharedStyle}
                />
            )}
            {open && (
                <FieldZoomOverlay
                    label={label}
                    value={value || ''}
                    type={type}
                    inputMode={inputMode}
                    placeholder={placeholder}
                    multiline={multiline}
                    onConfirm={val => { onConfirm(val); setOpen(false); }}
                    onClose={() => setOpen(false)}
                />
            )}
        </>
    );
}

// ── Screen: Forms — 4 módulos con campos progresivos ──
function ScreenForms({ modulo, record, campana, onClose }) {
    const { useState, useEffect } = React;

    const [parcelas, setParcelas] = useState([]);
    useEffect(() => {
        fetch('/api/parcelas?pac_only=false', { credentials: 'include' })
            .then(r => r.json()).then(d => setParcelas(Array.isArray(d) ? d : []));
    }, []);

    const isEdit = !!(record && record.id);

    const MODULE_CONFIG = {
        tratamiento:   { icon: '🌿', title: 'Tratamiento Fitosanitario', color: '#1D9E75' },
        fertilizacion: { icon: '🌱', title: 'Fertilización',              color: '#4f46e5' },
        labor:         { icon: '🚜', title: 'Labor Agrícola',            color: '#1d4ed8' },
        cosecha:       { icon: '📦', title: 'Cosecha / Producción',      color: '#db2777' },
        compra:        { icon: '🛒', title: 'Compras',                   color: '#b45309' },
        riego:         { icon: '💧', title: 'Riego',                    color: '#0ea5e9' },
        abonado:       { icon: '📋', title: 'Plan de abonado',           color: '#0d9488' },
    };
    const cfg = MODULE_CONFIG[modulo] || { icon: '📝', title: 'Registro', color: '#374151' };

    return (
        <div style={{ minHeight: '100vh', background: '#f8f9fb' }}>
            <div style={{ background: `linear-gradient(135deg, ${cfg.color}dd, ${cfg.color})`, padding: '52px 20px 24px' }}>
                <button className="back-btn" onClick={() => onClose()} style={{ marginBottom: 14 }}>←</button>
                <h1 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.4rem', color:'#fff', margin:'0 0 4px' }}>
                    {cfg.icon} {isEdit ? `Editar ${cfg.title}` : `Nuevo: ${cfg.title}`}
                </h1>
                <p style={{ color:'rgba(255,255,255,0.65)', fontSize:'0.82rem', margin:0 }}>
                    Campaña {campana}
                </p>
            </div>
            <div style={{ padding: '20px 16px', maxWidth: 720, margin: '0 auto' }}>
                {modulo === 'tratamiento'   && <FormTratamiento   parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
                {modulo === 'fertilizacion' && <FormFertilizacion parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
                {modulo === 'labor'         && <FormLabor         parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
                {modulo === 'cosecha'       && <FormCosecha       parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
                {modulo === 'compra'        && <FormCompra                            record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
                {modulo === 'riego'         && <FormRiego         parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
                {modulo === 'abonado'         && <FormAbonado         parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
                {modulo === 'cultivo_campana' && <FormCultivoCampana  parcelas={parcelas} record={record} campana={campana} onClose={onClose} isEdit={isEdit} />}
            </div>
        </div>
    );
}

// ── Selector de parcela — solo nombre ──
function ParcelSelect({ parcelas, value, onChange }) {
    return (
        <select className="input-field" value={value||''} onChange={e => onChange(e.target.value)}>
            <option value="">Seleccionar parcela…</option>
            {parcelas.map(p => (
                <option key={p.id} value={p.id}>{p.nombre_finca}</option>
            ))}
        </select>
    );
}

function FieldGroup({ label, children }) {
    return (
        <div style={{ marginBottom: 16 }}>
            <label className="field-label">{label}</label>
            {children}
        </div>
    );
}

function MasCampos({ children }) {
    return (
        <div style={{ marginBottom: 8, borderTop: '1px solid var(--outline-variant)', paddingTop: 16 }}>
            {children}
        </div>
    );
}

// ── 1. TRATAMIENTO FITOSANITARIO ──
function FormTratamiento({ parcelas, record, campana, onClose, isEdit }) {
    const today = new Date().toISOString().split('T')[0];
    const [equipos, setEquipos]         = React.useState([]);
    const [aplicadores, setAplicadores] = React.useState([]);
    const [saving, setSaving]           = React.useState(false);
    const [plazoAlert, setPlazoAlert]   = React.useState('');
    const [cultivo, setCultivo]         = React.useState({});
    const [showAddAplic, setShowAddAplic] = React.useState(false);
    const [newAplic, setNewAplic]         = React.useState({ nombre: '', num_ropo: '', nif: '' });

    const [f, setF] = React.useState({
        parcela_id:               record?.parcela_id || '',
        parcela_etiqueta:         record?.parcela_etiqueta || '',
        fecha_aplicacion:         record?.fecha_aplicacion || today,
        producto_comercial:       record?.producto_comercial || '',
        num_registro_mapa:        record?.num_registro_mapa || '',
        sustancia_activa:         record?.sustancia_activa || '',
        plaga_objetivo:           record?.plaga_objetivo || '',
        dosis_valor:              record?.dosis_valor || '',
        dosis_unidad:             record?.dosis_unidad || 'L/ha',
        volumen_caldo:            record?.volumen_caldo || '',
        equipo_id:                record?.equipo_id || '',
        condiciones_meteo:        record?.condiciones_meteo || '',
        plazo_seguridad_dias:     record?.plazo_seguridad_dias || '',
        fecha_recoleccion_minima: record?.fecha_recoleccion_minima || '',
        eficacia:                 record?.eficacia || '',
        aplicador_id:             record?.aplicador_id || '',
        notas:                    record?.notas || '',
        campana,
    });
    const set = (k, v) => setF(x => ({ ...x, [k]: v }));

    React.useEffect(() => {
        fetch('/api/equipos', { credentials: 'include' }).then(r => r.json()).then(d => setEquipos(Array.isArray(d) ? d : []));
        fetch('/api/aplicadores', { credentials: 'include' }).then(r => r.json()).then(d => setAplicadores(Array.isArray(d) ? d : []));
    }, []);

    React.useEffect(() => {
        const dias = parseInt(f.plazo_seguridad_dias);
        if (f.fecha_aplicacion && !isNaN(dias) && dias > 0) {
            const dt = new Date(f.fecha_aplicacion + 'T00:00:00');
            dt.setDate(dt.getDate() + dias);
            const minDate = dt.toISOString().split('T')[0];
            setF(x => ({ ...x, fecha_recoleccion_minima: minDate }));
            if (cultivo?.fecha_recoleccion_prevista && cultivo.fecha_recoleccion_prevista < minDate) {
                setPlazoAlert(`⚠️ La fecha prevista de cosecha (${cultivo.fecha_recoleccion_prevista}) es anterior al plazo de seguridad (${minDate})`);
            } else { setPlazoAlert(''); }
        }
    }, [f.plazo_seguridad_dias, f.fecha_aplicacion, cultivo]);

    React.useEffect(() => {
        if (!f.parcela_id) return;
        fetch(`/api/cultivos-campana?parcela_id=${f.parcela_id}&campana=${encodeURIComponent(campana)}`, { credentials: 'include' })
            .then(r => r.json()).then(d => setCultivo(Array.isArray(d) && d[0] ? d[0] : {}));
        const p = parcelas.find(x => String(x.id) === String(f.parcela_id));
        if (p) set('parcela_etiqueta', p.nombre_finca);
    }, [f.parcela_id]);

    const saveNuevoAplicador = async () => {
        if (!newAplic.nombre.trim()) { alert('El nombre del aplicador es obligatorio'); return; }
        const res = await fetch('/api/aplicadores', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newAplic), credentials: 'include'
        });
        if (!res.ok) { alert('Error al guardar el aplicador'); return; }
        const d = await res.json();
        const lista = await fetch('/api/aplicadores', { credentials: 'include' }).then(r => r.json());
        setAplicadores(Array.isArray(lista) ? lista : []);
        set('aplicador_id', String(d.id));
        setNewAplic({ nombre: '', num_ropo: '', nif: '' });
        setShowAddAplic(false);
    };

    const save = async () => {
        if (!f.parcela_id || !f.fecha_aplicacion || !f.aplicador_id || !f.producto_comercial ||
            !f.plaga_objetivo || !f.sustancia_activa || !f.num_registro_mapa || !f.dosis_valor ||
            !f.equipo_id || !f.plazo_seguridad_dias) {
            alert('Rellena todos los campos obligatorios (marcados con *)'); return;
        }
        setSaving(true);
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/tratamientos/${record.id}` : '/api/tratamientos';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar el tratamiento'); setSaving(false); return; }
        onClose('✅ Tratamiento guardado');
    };

    return (
        <div>
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
            </FieldGroup>
            <FieldGroup label="Fecha de aplicación *">
                <input type="date" className="input-field" value={f.fecha_aplicacion} onChange={e => set('fecha_aplicacion', e.target.value)} />
            </FieldGroup>
            <FieldGroup label="Aplicador (ROPO) *">
                {aplicadores.length > 0 ? (
                    <select className="input-field" value={f.aplicador_id} onChange={e => set('aplicador_id', e.target.value)}>
                        <option value="">-- Selecciona aplicador --</option>
                        {aplicadores.map(a => <option key={a.id} value={a.id}>{a.nombre}{a.num_ropo ? ` (${a.num_ropo})` : ''}</option>)}
                    </select>
                ) : (
                    <div style={{ padding: '10px 12px', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8 }}>
                        <p style={{ margin: '0 0 8px', fontSize: '0.85rem', color: '#c2410c', fontWeight: 600 }}>
                            No tienes aplicadores registrados. Es un campo obligatorio.
                        </p>
                        {!showAddAplic ? (
                            <button type="button" className="btn-primary" style={{ fontSize: '0.85rem', padding: '8px 16px' }}
                                onClick={() => setShowAddAplic(true)}>
                                + Añadir aplicador ahora
                            </button>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                <input className="input-field" placeholder="Nombre completo *" value={newAplic.nombre}
                                    onChange={e => setNewAplic(x => ({ ...x, nombre: e.target.value }))} />
                                <input className="input-field" placeholder="Nº ROPO (opcional)" value={newAplic.num_ropo}
                                    onChange={e => setNewAplic(x => ({ ...x, num_ropo: e.target.value }))} />
                                <input className="input-field" placeholder="NIF (opcional)" value={newAplic.nif}
                                    onChange={e => setNewAplic(x => ({ ...x, nif: e.target.value }))} />
                                <div style={{ display: 'flex', gap: 8 }}>
                                    <button type="button" className="btn-ghost" style={{ flex: 1, fontSize: '0.85rem' }}
                                        onClick={() => setShowAddAplic(false)}>Cancelar</button>
                                    <button type="button" className="btn-primary" style={{ flex: 2, fontSize: '0.85rem' }}
                                        onClick={saveNuevoAplicador}>Guardar aplicador</button>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </FieldGroup>
            <FieldGroup label="Producto comercial *">
                <ZoomInput label="Producto comercial" value={f.producto_comercial} placeholder="Nombre del producto"
                    onConfirm={v => set('producto_comercial', v)} />
            </FieldGroup>
            <FieldGroup label="Plaga / Objetivo *">
                <ZoomInput label="Plaga / Objetivo" value={f.plaga_objetivo} placeholder="Repilo, Antracnosis…"
                    onConfirm={v => set('plaga_objetivo', v)} />
            </FieldGroup>
            <div className="responsive-grid cols-2">
                <FieldGroup label="Sustancia activa *">
                    <ZoomInput label="Sustancia activa" value={f.sustancia_activa} placeholder="Cobre, Glifosato…"
                        onConfirm={v => set('sustancia_activa', v)} />
                </FieldGroup>
                <FieldGroup label="Nº Registro MAPA *">
                    <ZoomInput label="Nº Registro MAPA" value={f.num_registro_mapa} placeholder="ES-00000-0"
                        onConfirm={v => set('num_registro_mapa', v)} />
                </FieldGroup>
            </div>
            <FieldGroup label="Dosis *">
                <div style={{ display: 'flex', gap: 8 }}>
                    <ZoomInput label="Dosis" value={f.dosis_valor} placeholder="2.5" inputMode="decimal"
                        style={{ flex: 2 }} onConfirm={v => set('dosis_valor', v)} />
                    <select className="input-field" value={f.dosis_unidad} onChange={e => set('dosis_unidad', e.target.value)} style={{ flex: 1 }}>
                        {['cc/ha', 'g/ha', 'kg/ha', 'L/100L', 'L/ha'].map(u => <option key={u}>{u}</option>)}
                    </select>
                </div>
            </FieldGroup>
            <FieldGroup label="Equipo de aplicación *">
                <select className="input-field" value={f.equipo_id} onChange={e => set('equipo_id', e.target.value)}>
                    <option value="">-- Selecciona equipo --</option>
                    {equipos.map(e => <option key={e.id} value={e.id}>{e.descripcion}</option>)}
                </select>
            </FieldGroup>
            <FieldGroup label="Plazo de seguridad (días) *">
                <ZoomInput label="Plazo de seguridad (días)" value={f.plazo_seguridad_dias} placeholder="15" inputMode="numeric"
                    onConfirm={v => set('plazo_seguridad_dias', v)} />
            </FieldGroup>

            <MasCampos>
                <div className="responsive-grid cols-2">
                    <FieldGroup label="Volumen de caldo (L/ha)">
                        <ZoomInput label="Volumen de caldo (L/ha)" value={f.volumen_caldo} placeholder="300" inputMode="numeric"
                            onConfirm={v => set('volumen_caldo', v)} />
                    </FieldGroup>
                    <FieldGroup label="Condiciones meteorológicas">
                        <ZoomInput label="Condiciones meteorológicas" value={f.condiciones_meteo} placeholder="T 22°C · V <3 m/s · HR 45%"
                            onConfirm={v => set('condiciones_meteo', v)} />
                    </FieldGroup>
                    <FieldGroup label="Fecha mínima de cosecha">
                        <input type="date" className="input-field" value={f.fecha_recoleccion_minima} readOnly
                            style={{ borderColor: plazoAlert ? '#ef4444' : undefined, background: 'var(--surface-container-low)', color: 'var(--on-surface-variant)', cursor: 'not-allowed' }} />
                        <div style={{ fontSize: '0.72rem', color: 'var(--on-surface-variant)', marginTop: 3 }}>
                            Calculada automáticamente desde el plazo de seguridad
                        </div>
                    </FieldGroup>
                    <FieldGroup label="Eficacia observada">
                        <select className="input-field" value={f.eficacia} onChange={e => set('eficacia', e.target.value)}>
                            <option value="">Sin evaluar</option>
                            {['Alta', 'Baja', 'Media', 'Muy alta', 'Nula'].map(v => <option key={v}>{v}</option>)}
                        </select>
                    </FieldGroup>
                </div>
                {plazoAlert && (
                    <div className="alert-banner danger" style={{ marginBottom: 16 }}>
                        <span style={{ fontSize: 20 }}>⚠️</span>
                        <div style={{ fontSize: '0.85rem', color: '#991b1b', fontWeight: 600 }}>{plazoAlert}</div>
                    </div>
                )}
                <FieldGroup label="Notas">
                    <ZoomInput label="Notas" value={f.notas} placeholder="Observaciones adicionales…"
                        multiline onConfirm={v => set('notas', v)} />
                </FieldGroup>
            </MasCampos>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button className="btn-ghost" onClick={() => onClose()} style={{ flex: 1 }}>Cancelar</button>
                <button className="btn-primary" onClick={save} disabled={saving} style={{ flex: 2 }}>
                    {saving ? 'Guardando…' : (isEdit ? '💾 Actualizar' : '✓ Guardar tratamiento')}
                </button>
            </div>
        </div>
    );
}

// ── 2. FERTILIZACIÓN ──
function FormFertilizacion({ parcelas, record, campana, onClose, isEdit }) {
    const today = new Date().toISOString().split('T')[0];
    const [saving, setSaving] = React.useState(false);
    const [f, setF] = React.useState({
        parcela_id: record?.parcela_id || '', parcela_etiqueta: record?.parcela_etiqueta || '',
        fecha_aplicacion: record?.fecha_aplicacion || today,
        tipo_fertilizante: record?.tipo_fertilizante || '',
        producto: record?.producto || '', riqueza_npk: record?.riqueza_npk || '',
        dosis_valor: record?.dosis_valor || '', dosis_unidad: record?.dosis_unidad || 'kg/ha',
        densidad_g_ml: record?.densidad_g_ml || '',
        metodo_aplicacion: record?.metodo_aplicacion || '', notas: record?.notas || '',
        campana,
    });
    const set = (k, v) => setF(x => ({ ...x, [k]: v }));

    React.useEffect(() => {
        if (!f.parcela_id) return;
        const p = parcelas.find(x => String(x.id) === String(f.parcela_id));
        if (p) set('parcela_etiqueta', p.nombre_finca);
    }, [f.parcela_id]);

    const save = async () => {
        if (!f.parcela_id || !f.fecha_aplicacion) { alert('Rellena: parcela y fecha'); return; }
        setSaving(true);
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/fertilizacion/${record.id}` : '/api/fertilizacion';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar el abono'); setSaving(false); return; }
        onClose('✅ Fertilización guardada');
    };

    const isLiquid = (u) => u && (u.startsWith('L/') || u.toLowerCase().includes('litro'));

    const calcNPK = (riqueza, dosis, unidad, densidad) => {
        if (!riqueza || !dosis) return null;
        const m = riqueza.match(/(\d+\.?\d*)[^\d]+(\d+\.?\d*)[^\d]+(\d+\.?\d*)/);
        if (!m) return null;
        let d = parseFloat(String(dosis).replace(',', '.'));
        if (isNaN(d) || d <= 0) return null;
        if (isLiquid(unidad)) {
            const dens = parseFloat(String(densidad).replace(',', '.'));
            if (!dens || dens <= 0) return null;
            d = d * dens;
        }
        return {
            n: Math.round(parseFloat(m[1]) / 100 * d * 100) / 100,
            p: Math.round(parseFloat(m[2]) / 100 * d * 100) / 100,
            k: Math.round(parseFloat(m[3]) / 100 * d * 100) / 100,
        };
    };
    const npkPreview = calcNPK(f.riqueza_npk, f.dosis_valor, f.dosis_unidad, f.densidad_g_ml);

    return (
        <div>
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
            </FieldGroup>
            <div className="responsive-grid cols-2">
                <FieldGroup label="Fecha de aplicación *">
                    <input type="date" className="input-field" value={f.fecha_aplicacion} onChange={e => set('fecha_aplicacion', e.target.value)} />
                </FieldGroup>
                <FieldGroup label="Producto / Abono">
                    <ZoomInput label="Producto / Abono" value={f.producto} placeholder="Urea, NPK, Estiércol…"
                        onConfirm={v => set('producto', v)} />
                </FieldGroup>
            </div>

            <MasCampos>
                <div className="responsive-grid cols-2">
                    <FieldGroup label="Tipo de fertilizante">
                        <select className="input-field" value={f.tipo_fertilizante} onChange={e => set('tipo_fertilizante', e.target.value)}>
                            <option value="">Seleccionar…</option>
                            {['Enmienda cálcica', 'Enmienda orgánica', 'Foliar', 'Mineral complejo', 'Mineral simple', 'Organomineral', 'Orgánico', 'Otro'].map(t => <option key={t}>{t}</option>)}
                        </select>
                    </FieldGroup>
                    <FieldGroup label="Riqueza N-P-K">
                        <ZoomInput label="Riqueza N-P-K" value={f.riqueza_npk} placeholder="27-0-0 · 8-15-15…"
                            onConfirm={v => set('riqueza_npk', v)} />
                    </FieldGroup>
                    <FieldGroup label="Dosis">
                        <div style={{ display: 'flex', gap: 8 }}>
                            <ZoomInput label="Dosis" value={f.dosis_valor} placeholder="200" inputMode="decimal"
                                style={{ flex: 2 }} onConfirm={v => set('dosis_valor', v)} />
                            <select className="input-field" value={f.dosis_unidad} onChange={e => set('dosis_unidad', e.target.value)} style={{ flex: 1 }}>
                                {['kg/árbol', 'kg/ha', 'L/árbol', 'L/ha', 't/ha'].map(u => <option key={u}>{u}</option>)}
                            </select>
                        </div>
                    </FieldGroup>
                    {isLiquid(f.dosis_unidad) && (
                        <FieldGroup label="Densidad del fertilizante (g/mL) *">
                            <ZoomInput label="Densidad (g/mL)" value={f.densidad_g_ml} placeholder="1.2" inputMode="decimal"
                                onConfirm={v => set('densidad_g_ml', v)} />
                            <div style={{ fontSize:'0.72rem', color:'#6b7280', marginTop:4 }}>
                                Necesaria para calcular N/P/K en fertilizantes líquidos (ej. solución nitrogenada: 1.32 g/mL)
                            </div>
                        </FieldGroup>
                    )}
                    <FieldGroup label="Método de aplicación">
                        <select className="input-field" value={f.metodo_aplicacion} onChange={e => set('metodo_aplicacion', e.target.value)}>
                            <option value="">Seleccionar…</option>
                            {['Fertirrigación', 'Foliar', 'Incorporado', 'Inyectado', 'Localizado', 'Voleo'].map(m => <option key={m}>{m}</option>)}
                        </select>
                    </FieldGroup>
                    {npkPreview && (
                        <div style={{
                            gridColumn: '1 / -1',
                            background: 'linear-gradient(135deg, #f0f4ff, #e8edff)',
                            border: '1.5px solid #c7d2fe',
                            borderRadius: 'var(--radius-lg)',
                            padding: '10px 14px',
                            fontSize: '0.82rem',
                            color: '#3730a3',
                            fontWeight: 600,
                        }}>
                            🧪 Nutrientes calculados:&nbsp;
                            <span>N: {npkPreview.n} kg/ha</span>
                            <span style={{ margin: '0 8px', opacity: 0.4 }}>·</span>
                            <span>P₂O₅: {npkPreview.p} kg/ha</span>
                            <span style={{ margin: '0 8px', opacity: 0.4 }}>·</span>
                            <span>K₂O: {npkPreview.k} kg/ha</span>
                        </div>
                    )}
                </div>
                <FieldGroup label="Notas">
                    <ZoomInput label="Notas" value={f.notas} placeholder="Observaciones…"
                        multiline onConfirm={v => set('notas', v)} />
                </FieldGroup>
            </MasCampos>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button className="btn-ghost" onClick={() => onClose()} style={{ flex: 1 }}>Cancelar</button>
                <button className="btn-primary" onClick={save} disabled={saving} style={{ flex: 2 }}>
                    {saving ? 'Guardando…' : (isEdit ? '💾 Actualizar' : '✓ Guardar abono')}
                </button>
            </div>
        </div>
    );
}

// ── 3. LABOR AGRÍCOLA ──
const _LABOR_TIPOS = [
  ['Aclareo',                     'Aclareo (eliminar los brotes débiles frutales)'],
  ['Acordonar/Hilerar',           'Acordonar/Hilerar (amontonar poda)'],
  ['Alzado',                      'Alzado (arar con vertederas o arados de disco, laboreo superficial <30cm)'],
  ['Arado',                       'Arado'],
  ['Atado',                       'Atado'],
  ['Desherbado o Desbroce',       'Desherbado o Desbroce'],
  ['Despunte y Deshoje',          'Despunte y Deshoje'],
  ['Desvareto',                   'Desvareto'],
  ['Escarda',                     'Escarda'],
  ['Fresado',                     'Fresado'],
  ['Gradeo o Rastreo',            'Gradeo o Rastreo'],
  ['Guiado de brotes',            'Guiado de brotes'],
  ['Injertado',                   'Injertado'],
  ['Mantenimiento Instalaciones', 'Mantenimiento Instalaciones'],
  ['Mantenimiento Maquinaria',    'Mantenimiento Maquinaria'],
  ['Plantación',                  'Plantación'],
  ['Poda',                        'Poda'],
  ['Recolección',                 'Recolección'],
  ['Retirada de leña',            'Retirada de leña'],
  ['Riego',                       'Riego'],
  ['Ruleo',                       'Ruleo'],
  ['Siembra',                     'Siembra'],
  ['Subsolado',                   'Subsolado (laboreo profundo >30cm)'],
  ['Triturado de restos',         'Triturado de restos'],
  ['Otros',                       'Otros'],
];
const _LABOR_MAP = {
  'aclareo':'Aclareo','alzado':'Alzado','arado':'Arado','are':'Arado',
  'poda':'Poda','pode':'Poda',
  'desherbado':'Desherbado o Desbroce','desyerbado':'Desherbado o Desbroce','desbroz':'Desherbado o Desbroce',
  'siembra':'Siembra','sembrado':'Siembra','siembre':'Siembra','sembre':'Siembra',
  'fresado':'Fresado','subsolado':'Subsolado',
  'desvareto':'Desvareto','desvaretado':'Desvareto',
  'gradeo':'Gradeo o Rastreo','rastreo':'Gradeo o Rastreo','pase':'Gradeo o Rastreo',
  'laboreo':'Arado','labrado':'Arado','labor':'Arado','cultivado':'Arado',
  'vendimia':'Recolección','vendimiado':'Recolección',
  'escarda':'Escarda','cave':'Escarda','cavado':'Escarda',
  'trilla':'Triturado de restos','trillado':'Triturado de restos',
  'riego':'Riego','regado':'Riego','plantacion':'Plantación',
};
const normTipoLabor = (v) => { if (!v) return ''; if (_LABOR_TIPOS.some(([val]) => val === v)) return v; return _LABOR_MAP[(v||'').toLowerCase().trim()] || ''; };

function FormLabor({ parcelas, record, campana, onClose, isEdit }) {
    const today = new Date().toISOString().split('T')[0];
    const [saving, setSaving] = React.useState(false);
    const [f, setF] = React.useState({
        parcela_id: record?.parcela_id || '', parcela_etiqueta: record?.parcela_etiqueta || '',
        fecha: record?.fecha || today,
        tipo_labor: normTipoLabor(record?.tipo_labor),
        producto: record?.producto || '',
        descripcion: record?.descripcion || '', maquinaria: record?.maquinaria || '',
        horas_trabajadas: record?.horas_trabajadas || '', operario: record?.operario || '',
        notas: record?.notas || '', campana,
    });
    const set = (k, v) => setF(x => ({ ...x, [k]: v }));

    React.useEffect(() => {
        if (!f.parcela_id) return;
        const p = parcelas.find(x => String(x.id) === String(f.parcela_id));
        if (p) set('parcela_etiqueta', p.nombre_finca);
    }, [f.parcela_id]);

    const save = async () => {
        if (!f.parcela_id || !f.fecha) { alert('Rellena: parcela y fecha'); return; }
        setSaving(true);
        try {
            const method = isEdit ? 'PUT' : 'POST';
            const url = isEdit ? `/api/labores/${record.id}` : '/api/labores';
            const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
            if (!res.ok) { alert('Error al guardar. Inténtalo de nuevo.'); setSaving(false); return; }
            onClose('✅ Labor guardada');
        } catch { alert('Error de conexión'); setSaving(false); }
    };

    return (
        <div>
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
            </FieldGroup>
            <div className="responsive-grid cols-2">
                <FieldGroup label="Fecha *">
                    <input type="date" className="input-field" value={f.fecha} onChange={e => set('fecha', e.target.value)} />
                </FieldGroup>
                <FieldGroup label="Tipo de labor">
                    <select className="input-field" value={f.tipo_labor} onChange={e => set('tipo_labor', e.target.value)}>
                        <option value="">Seleccionar…</option>
                        {_LABOR_TIPOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </select>
                </FieldGroup>
            </div>
            <FieldGroup label="Cultivo / Producto sembrado">
                <ZoomInput label="Cultivo / Producto sembrado" value={f.producto}
                    placeholder="Ej: Trigo, Cebada, Yeros… (o escribe el tuyo)"
                    onConfirm={v => set('producto', v)} />
            </FieldGroup>

            <MasCampos>
                <div className="responsive-grid cols-2">
                    <FieldGroup label="Descripción">
                        <ZoomInput label="Descripción" value={f.descripcion} placeholder="Detalle de la operación…"
                            onConfirm={v => set('descripcion', v)} />
                    </FieldGroup>
                    <FieldGroup label="Maquinaria">
                        <ZoomInput label="Maquinaria" value={f.maquinaria} placeholder="Tractor, vibrador…"
                            onConfirm={v => set('maquinaria', v)} />
                    </FieldGroup>
                    <FieldGroup label="Horas trabajadas">
                        <ZoomInput label="Horas trabajadas" value={f.horas_trabajadas} placeholder="4.5" inputMode="decimal"
                            onConfirm={v => set('horas_trabajadas', v)} />
                    </FieldGroup>
                    <FieldGroup label="Operario / Empresa">
                        <ZoomInput label="Operario / Empresa" value={f.operario} placeholder="Nombre o empresa"
                            onConfirm={v => set('operario', v)} />
                    </FieldGroup>
                </div>
                <FieldGroup label="Notas">
                    <ZoomInput label="Notas" value={f.notas} placeholder="Observaciones…"
                        multiline onConfirm={v => set('notas', v)} />
                </FieldGroup>
            </MasCampos>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button className="btn-ghost" onClick={() => onClose()} style={{ flex: 1 }}>Cancelar</button>
                <button className="btn-primary" onClick={save} disabled={saving} style={{ flex: 2 }}>
                    {saving ? 'Guardando…' : (isEdit ? '💾 Actualizar' : '✓ Guardar labor')}
                </button>
            </div>
        </div>
    );
}

// ── 4. COSECHA / PRODUCCIÓN ──
function FormCosecha({ parcelas, record, campana, onClose, isEdit }) {
    const today = new Date().toISOString().split('T')[0];
    const [saving, setSaving]       = React.useState(false);
    const [rendimiento, setRendimiento] = React.useState('');
    const [f, setF] = React.useState({
        parcela_id: record?.parcela_id || '', parcela_etiqueta: record?.parcela_etiqueta || '',
        fecha_inicio: record?.fecha_inicio || today, fecha_fin: record?.fecha_fin || '',
        cultivo: record?.cultivo || '', variedad: record?.variedad || '',
        superficie_cosechada_ha: record?.superficie_cosechada_ha || '',
        produccion_total_valor: record?.produccion_total_valor || '',
        produccion_total_unidad: record?.produccion_total_unidad || 'kg',
        destino: record?.destino || '', comprador: record?.comprador || '',
        precio_unidad: record?.precio_unidad || '', notas: record?.notas || '',
        campana,
    });
    const set = (k, v) => setF(x => ({ ...x, [k]: v }));

    React.useEffect(() => {
        const prod = parseFloat(f.produccion_total_valor);
        const sup  = parseFloat(f.superficie_cosechada_ha);
        if (!isNaN(prod) && !isNaN(sup) && sup > 0 && f.produccion_total_unidad === 'kg') {
            setRendimiento((prod / sup).toFixed(0) + ' kg/ha');
        } else { setRendimiento(''); }
    }, [f.produccion_total_valor, f.superficie_cosechada_ha, f.produccion_total_unidad]);

    React.useEffect(() => {
        if (!f.parcela_id) return;
        const p = parcelas.find(x => String(x.id) === String(f.parcela_id));
        if (p) set('parcela_etiqueta', p.nombre_finca);
        fetch(`/api/cultivos-campana?parcela_id=${f.parcela_id}&campana=${encodeURIComponent(campana)}`, { credentials: 'include' })
            .then(r => r.json()).then(data => {
                const c = Array.isArray(data) && data[0] ? data[0] : null;
                if (c) setF(x => ({
                    ...x,
                    cultivo: x.cultivo || c.cultivo || '',
                    variedad: x.variedad || c.variedad || '',
                    superficie_cosechada_ha: x.superficie_cosechada_ha || c.superficie_cultivada_ha || '',
                }));
            });
    }, [f.parcela_id]);

    const save = async () => {
        if (!f.parcela_id || !f.fecha_inicio) { alert('Rellena: parcela y fecha de inicio'); return; }
        setSaving(true);
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/cosecha/${record.id}` : '/api/cosecha';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar la cosecha'); setSaving(false); return; }
        onClose('✅ Cosecha guardada');
    };

    return (
        <div>
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
            </FieldGroup>
            <div className="responsive-grid cols-2">
                <FieldGroup label="Fecha inicio *">
                    <input type="date" className="input-field" value={f.fecha_inicio} onChange={e => set('fecha_inicio', e.target.value)} />
                </FieldGroup>
                <FieldGroup label="Cultivo">
                    <ZoomInput label="Cultivo" value={f.cultivo} placeholder="Olivar, Viñedo, Cereal…"
                        onConfirm={v => set('cultivo', v)} />
                </FieldGroup>
            </div>

            <MasCampos>
                <div className="responsive-grid cols-2">
                    <FieldGroup label="Fecha fin recolección">
                        <input type="date" className="input-field" value={f.fecha_fin} onChange={e => set('fecha_fin', e.target.value)} />
                    </FieldGroup>
                    <FieldGroup label="Variedad">
                        <ZoomInput label="Variedad" value={f.variedad} placeholder="Picual, Tempranillo…"
                            onConfirm={v => set('variedad', v)} />
                    </FieldGroup>
                    <FieldGroup label="Superficie cosechada (ha)">
                        <ZoomInput label="Superficie cosechada (ha)" value={f.superficie_cosechada_ha} placeholder="3.25" inputMode="decimal"
                            onConfirm={v => set('superficie_cosechada_ha', v)} />
                    </FieldGroup>
                    <FieldGroup label={`Producción total${rendimiento ? ` → ${rendimiento}` : ''}`}>
                        <div style={{ display: 'flex', gap: 8 }}>
                            <ZoomInput label="Producción total" value={f.produccion_total_valor} placeholder="12500" inputMode="decimal"
                                style={{ flex: 2 }} onConfirm={v => set('produccion_total_valor', v)} />
                            <select className="input-field" value={f.produccion_total_unidad} onChange={e => set('produccion_total_unidad', e.target.value)} style={{ flex: 1 }}>
                                {['cajas', 'kg', 'L', 't', 'unidades'].map(u => <option key={u}>{u}</option>)}
                            </select>
                        </div>
                    </FieldGroup>
                    {rendimiento && (
                        <div style={{ gridColumn: '1/-1' }}>
                            <div style={{ background: '#d1fae5', borderRadius: 10, padding: '10px 14px', fontSize: '0.88rem', color: '#065f46', fontWeight: 700 }}>
                                📊 Rendimiento: {rendimiento}
                            </div>
                        </div>
                    )}
                    <FieldGroup label="Destino">
                        <select className="input-field" value={f.destino} onChange={e => set('destino', e.target.value)}>
                            <option value="">Seleccionar…</option>
                            {['Almazara propia', 'Autoconsumo', 'Bodega', 'Cooperativa', 'Exportación', 'Mercado en fresco', 'Otro'].map(d => <option key={d}>{d}</option>)}
                        </select>
                    </FieldGroup>
                    <FieldGroup label="Comprador / Destinatario">
                        <ZoomInput label="Comprador / Destinatario" value={f.comprador} placeholder="Nombre de la cooperativa"
                            onConfirm={v => set('comprador', v)} />
                    </FieldGroup>
                    <FieldGroup label="Precio por unidad (€)">
                        <ZoomInput label="Precio por unidad (€)" value={f.precio_unidad} placeholder="0.350 €/kg" inputMode="decimal"
                            onConfirm={v => set('precio_unidad', v)} />
                    </FieldGroup>
                </div>
                <FieldGroup label="Notas">
                    <ZoomInput label="Notas" value={f.notas} placeholder="Observaciones…"
                        multiline onConfirm={v => set('notas', v)} />
                </FieldGroup>
            </MasCampos>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button className="btn-ghost" onClick={() => onClose()} style={{ flex: 1 }}>Cancelar</button>
                <button className="btn-primary" onClick={save} disabled={saving} style={{ flex: 2 }}>
                    {saving ? 'Guardando…' : (isEdit ? '💾 Actualizar' : '✓ Guardar cosecha')}
                </button>
            </div>
        </div>
    );
}

// ── 5. COMPRA DE INSUMOS (Trazabilidad — Anexo III S5) ──
function FormCompra({ record, campana, onClose, isEdit }) {
    const today = new Date().toISOString().split('T')[0];
    const [saving, setSaving] = React.useState(false);
    const [error, setError]   = React.useState('');

    const [f, setF] = React.useState({
        fecha:             record?.fecha             || today,
        tipo_producto:     record?.tipo_producto     || '',
        producto:          record?.producto          || '',
        num_registro_mapa: record?.num_registro_mapa || '',
        sustancia_activa:  record?.sustancia_activa  || '',
        proveedor:         record?.proveedor         || '',
        cantidad_valor:    record?.cantidad_valor    || '',
        cantidad_unidad:   record?.cantidad_unidad   || 'kg',
        num_lote:          record?.num_lote          || '',
        num_factura:       record?.num_factura       || '',
        precio_total:      record?.precio_total      || '',
        notas:             record?.notas             || '',
        campana,
    });
    const set = (k, v) => setF(x => ({ ...x, [k]: v }));

    const save = async () => {
        setError('');
        setSaving(true);
        const url    = isEdit ? `/api/compras/${record.id}` : '/api/compras';
        const method = isEdit ? 'PUT' : 'POST';
        try {
            const res = await fetch(url, {
                method, credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(f),
            });
            const data = await res.json();
            if (!res.ok) { setError(data.error || 'Error al guardar'); setSaving(false); return; }
            onClose(isEdit ? 'Compra actualizada' : 'Compra registrada');
        } catch { setError('Error de conexión'); setSaving(false); }
    };

    return (
        <div>
            {error && (
                <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 10,
                    padding: '10px 14px', marginBottom: 16, color: '#991b1b', fontSize: '0.88rem', fontWeight: 600 }}>
                    ⚠️ {error}
                </div>
            )}

            <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10,
                padding: '10px 14px', marginBottom: 20, fontSize: '0.82rem', color: '#92400e' }}>
                📋 Obligatorio por RD 1311/2012 Anexo III S5 — Trazabilidad de insumos
            </div>

            <FieldGroup label="Fecha de compra *">
                <input type="date" className="input-field" value={f.fecha}
                    max={today} onChange={e => set('fecha', e.target.value)} />
            </FieldGroup>

            <FieldGroup label="Tipo de producto *">
                <select className="input-field" value={f.tipo_producto} onChange={e => set('tipo_producto', e.target.value)}>
                    <option value="">Seleccionar…</option>
                    <option value="combustible">Combustible</option>
                    <option value="fertilizante">Fertilizante / Abono</option>
                    <option value="fitosanitario">Fitosanitario</option>
                    <option value="otro">Otro insumo</option>
                    <option value="semilla">Semilla / Material vegetal</option>
                </select>
            </FieldGroup>

            <FieldGroup label="Nombre del producto *">
                <ZoomInput label="Nombre del producto" value={f.producto}
                    placeholder="Nombre comercial del producto"
                    onConfirm={v => set('producto', v)} />
            </FieldGroup>

            {f.tipo_producto === 'fitosanitario' && (<>
                <div style={{ background: '#fef3c7', border: '1px solid #fcd34d', borderRadius: 8,
                    padding: '8px 12px', marginBottom: 12, fontSize: '0.8rem', color: '#92400e' }}>
                    ⚖️ Campos obligatorios por ley para fitosanitarios (RD 1311/2012 Anexo III S5)
                </div>
                <FieldGroup label="Nº de registro MAPA *">
                    <ZoomInput label="Nº de registro MAPA" value={f.num_registro_mapa}
                        placeholder="ES-XXXXX-X"
                        onConfirm={v => set('num_registro_mapa', v)} />
                </FieldGroup>
                <FieldGroup label="Sustancia activa *">
                    <ZoomInput label="Sustancia activa" value={f.sustancia_activa}
                        placeholder="p.ej. glifosato, clorpirifos…"
                        onConfirm={v => set('sustancia_activa', v)} />
                </FieldGroup>
            </>)}

            <FieldGroup label="Proveedor / Vendedor">
                <ZoomInput label="Proveedor" value={f.proveedor}
                    placeholder="Cooperativa, almacén agrícola…"
                    onConfirm={v => set('proveedor', v)} />
            </FieldGroup>

            <div className="responsive-grid cols-2">
                <FieldGroup label="Cantidad">
                    <div style={{ display: 'flex', gap: 8 }}>
                        <ZoomInput label="Cantidad" value={f.cantidad_valor} placeholder="25" inputMode="decimal"
                            style={{ flex: 2 }} onConfirm={v => set('cantidad_valor', v)} />
                        <select className="input-field" value={f.cantidad_unidad}
                            onChange={e => set('cantidad_unidad', e.target.value)} style={{ flex: 1 }}>
                            {['kg', 'L', 'g', 't', 'sacos', 'envases', 'unidades'].map(u => <option key={u}>{u}</option>)}
                        </select>
                    </div>
                </FieldGroup>
                <FieldGroup label="Precio total (€)">
                    <ZoomInput label="Precio total (€)" value={f.precio_total} placeholder="142.50"
                        inputMode="decimal" onConfirm={v => set('precio_total', v)} />
                </FieldGroup>
                <FieldGroup label="Nº de lote">
                    <ZoomInput label="Nº de lote" value={f.num_lote} placeholder="L-2025-001"
                        onConfirm={v => set('num_lote', v)} />
                </FieldGroup>
                <FieldGroup label="Nº de factura / albarán">
                    <ZoomInput label="Nº de factura" value={f.num_factura} placeholder="FAC-2025-1234"
                        onConfirm={v => set('num_factura', v)} />
                </FieldGroup>
            </div>

            <FieldGroup label="Notas">
                <ZoomInput label="Notas" value={f.notas} placeholder="Observaciones…"
                    multiline onConfirm={v => set('notas', v)} />
            </FieldGroup>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button className="btn-ghost" onClick={() => onClose()} style={{ flex: 1 }}>Cancelar</button>
                <button className="btn-primary" onClick={save} disabled={saving} style={{ flex: 2 }}>
                    {saving ? 'Guardando…' : (isEdit ? '💾 Actualizar' : '✓ Registrar compra')}
                </button>
            </div>
        </div>
    );
}

function FormRiego({ parcelas, record, campana, onClose, isEdit }) {
    const today = new Date().toISOString().split('T')[0];
    const [saving, setSaving] = React.useState(false);
    const [f, setF] = React.useState({
        parcela_id:       record?.parcela_id       || '',
        parcela_etiqueta: record?.parcela_etiqueta  || '',
        fecha:            record?.fecha             || today,
        tipo_riego:       record?.tipo_riego        || '',
        volumen_m3:       record?.volumen_m3        || '',
        horas_riego:      record?.horas_riego       || '',
        fuente_agua:      record?.fuente_agua       || '',
        notas:            record?.notas             || '',
        campana,
    });
    const set = (k, v) => setF(x => ({ ...x, [k]: v }));

    React.useEffect(() => {
        if (!f.parcela_id) return;
        const p = parcelas.find(x => String(x.id) === String(f.parcela_id));
        if (p) set('parcela_etiqueta', p.nombre_finca);
    }, [f.parcela_id]);

    const save = async () => {
        if (!f.parcela_id || !f.fecha || !f.tipo_riego) {
            alert('Rellena: parcela, fecha y tipo de riego'); return;
        }
        if (!f.horas_riego && !f.volumen_m3) {
            alert('Indica al menos las horas de riego o el volumen en m³'); return;
        }
        setSaving(true);
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/riego/${record.id}` : '/api/riego';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar'); setSaving(false); return; }
        onClose('✅ Riego guardado');
    };

    return (
        <div>
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
            </FieldGroup>
            <div className="responsive-grid cols-2">
                <FieldGroup label="Fecha *">
                    <input type="date" className="input-field" value={f.fecha} onChange={e => set('fecha', e.target.value)} />
                </FieldGroup>
                <FieldGroup label="Tipo de riego *">
                    <select className="input-field" value={f.tipo_riego} onChange={e => set('tipo_riego', e.target.value)}>
                        <option value="">Seleccionar…</option>
                        {['Aspersión', 'Goteo', 'Gravedad', 'Otro', 'Pivot'].map(t => <option key={t}>{t}</option>)}
                    </select>
                </FieldGroup>
            </div>
            <div className="responsive-grid cols-2">
                <FieldGroup label="Horas de riego">
                    <ZoomInput label="Horas" value={f.horas_riego} placeholder="4.5" inputMode="decimal"
                        onConfirm={v => set('horas_riego', v)} />
                </FieldGroup>
                <FieldGroup label="Volumen (m³)">
                    <ZoomInput label="Volumen (m³)" value={f.volumen_m3} placeholder="150" inputMode="decimal"
                        onConfirm={v => set('volumen_m3', v)} />
                </FieldGroup>
            </div>
            <p style={{ fontSize: '0.74rem', color: 'var(--on-surface-variant)', margin: '-8px 0 12px', padding: '0 2px' }}>
                Rellena al menos uno de los dos campos de arriba.
            </p>

            <MasCampos>
                <FieldGroup label="Fuente de agua">
                    <select className="input-field" value={f.fuente_agua} onChange={e => set('fuente_agua', e.target.value)}>
                        <option value="">Seleccionar…</option>
                        {['Balsa', 'Comunidad de regantes', 'Otro', 'Pozo propio', 'Río'].map(s => <option key={s}>{s}</option>)}
                    </select>
                </FieldGroup>
                <FieldGroup label="Notas">
                    <ZoomInput label="Notas" value={f.notas} placeholder="Observaciones…"
                        multiline onConfirm={v => set('notas', v)} />
                </FieldGroup>
            </MasCampos>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button className="btn-ghost" onClick={() => onClose()} style={{ flex: 1 }}>Cancelar</button>
                <button className="btn-primary" onClick={save} disabled={saving} style={{ flex: 2 }}>
                    {saving ? 'Guardando…' : (isEdit ? 'Guardar cambios' : '💧 Guardar riego')}
                </button>
            </div>
        </div>
    );
}

function calcNpkAbonado(cultivo) {
    const c = (cultivo || '').toUpperCase();
    if (c.includes('TRIGO'))                                                        return { n: 120, p: 60,  k: 60  };
    if (c.includes('CEBADA'))                                                       return { n: 100, p: 50,  k: 50  };
    if (c.includes('GIRASOL'))                                                      return { n: 80,  p: 60,  k: 60  };
    if (c.includes('MAÍZ') || c.includes('MAIZ'))                                  return { n: 150, p: 80,  k: 100 };
    if (c.includes('OLIVAR'))                                                       return { n: 80,  p: 30,  k: 100 };
    if (c.includes('VIÑA') || c.includes('VID') || c.includes('VIÑEDO'))           return { n: 40,  p: 30,  k: 60  };
    if (c.includes('FRUTALES') || c.includes('FRUTAL'))                            return { n: 100, p: 50,  k: 150 };
    if (c.includes('YEROS') || c.includes('LEGUMINOSA') || c.includes('GUISANTE')
        || c.includes('GARBANZO') || c.includes('LENTEJA'))                        return { n: 20,  p: 40,  k: 40  };
    if (c.includes('BARBECHO'))                                                     return { n: 0,   p: 0,   k: 0   };
    return { n: 60, p: 40, k: 40 };
}

function FormAbonado({ parcelas, record, campana, onClose, isEdit }) {
    const today = new Date().toISOString().split('T')[0];
    const [saving, setSaving] = React.useState(false);
    const [f, setF] = React.useState({
        parcela_id:                  record?.parcela_id                  || '',
        parcela_etiqueta:            record?.parcela_etiqueta            || '',
        cultivo:                     record?.cultivo                     || '',
        cultivo_anterior:            record?.cultivo_anterior            || '',
        rendimiento_esperado_kg_ha:  record?.rendimiento_esperado_kg_ha  || '',
        fecha_preparacion:           record?.fecha_preparacion           || today,
        n_necesario_kg_ha:           record?.n_necesario_kg_ha           || '',
        p_necesario_kg_ha:           record?.p_necesario_kg_ha           || '',
        k_necesario_kg_ha:           record?.k_necesario_kg_ha           || '',
        datos_suelo:                 record?.datos_suelo                 || '',
        abono_recomendado:           record?.abono_recomendado           || '',
        dosis_recomendada_kg_ha:     record?.dosis_recomendada_kg_ha     || '',
        notas:                       record?.notas                       || '',
        campana,
    });
    const set = (k, v) => setF(x => ({ ...x, [k]: v }));

    React.useEffect(() => {
        if (!f.parcela_id) return;
        const p = parcelas.find(x => String(x.id) === String(f.parcela_id));
        if (p) set('parcela_etiqueta', p.nombre_finca);
    }, [f.parcela_id]);

    React.useEffect(() => {
        if (!f.cultivo) return;
        const { n, p, k } = calcNpkAbonado(f.cultivo);
        setF(x => ({ ...x, n_necesario_kg_ha: n, p_necesario_kg_ha: p, k_necesario_kg_ha: k }));
    }, [f.cultivo]);

    const save = async () => {
        if (!f.parcela_id || !f.cultivo || !f.cultivo_anterior || !f.rendimiento_esperado_kg_ha || !f.fecha_preparacion) {
            alert('Rellena: parcela, cultivo, cultivo anterior, rendimiento y fecha'); return;
        }
        setSaving(true);
        const method = isEdit ? 'PUT' : 'POST';
        const url    = isEdit ? `/api/abonado/${record.id}` : '/api/abonado';
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(f),
            credentials: 'include',
        });
        if (!res.ok) {
            const d = await res.json().catch(() => ({}));
            alert(d.error || 'Error al guardar');
            setSaving(false);
            return;
        }
        onClose('✅ Plan de abonado guardado');
    };

    const npkReady = f.n_necesario_kg_ha !== '' && f.n_necesario_kg_ha !== null;

    return (
        <div>
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
            </FieldGroup>

            <div className="responsive-grid cols-2">
                <FieldGroup label="Cultivo *">
                    <input type="text" className="input-field" value={f.cultivo}
                        placeholder="Ej: Trigo, Olivar, Viña…"
                        onChange={e => set('cultivo', e.target.value)} />
                </FieldGroup>
                <FieldGroup label="Cultivo anterior *">
                    <input type="text" className="input-field" value={f.cultivo_anterior}
                        placeholder="Ej: Cebada, Barbecho…"
                        onChange={e => set('cultivo_anterior', e.target.value)} />
                </FieldGroup>
            </div>

            <div className="responsive-grid cols-2">
                <FieldGroup label="Rendimiento esperado (kg/ha) *">
                    <ZoomInput label="Rendimiento (kg/ha)" value={f.rendimiento_esperado_kg_ha}
                        placeholder="Ej: 3500" inputMode="decimal"
                        onConfirm={v => set('rendimiento_esperado_kg_ha', v)} />
                </FieldGroup>
                <FieldGroup label="Fecha de preparación *">
                    <input type="date" className="input-field" value={f.fecha_preparacion}
                        onChange={e => set('fecha_preparacion', e.target.value)} />
                </FieldGroup>
            </div>

            {npkReady && (
                <div style={{ background: 'rgba(13,148,136,0.08)', border: '1px solid rgba(13,148,136,0.25)', borderRadius: 12, padding: '12px 14px', marginBottom: 16 }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0f766e', marginBottom: 8 }}>
                        🌱 Necesidades NPK calculadas
                    </div>
                    <div style={{ display: 'flex', gap: 10 }}>
                        {[['N', f.n_necesario_kg_ha, '#1d4ed8'], ['P₂O₅', f.p_necesario_kg_ha, '#b45309'], ['K₂O', f.k_necesario_kg_ha, '#0f766e']].map(([label, val, color]) => (
                            <div key={label} style={{ flex: 1, background: '#fff', borderRadius: 8, padding: '8px 4px', textAlign: 'center', border: `1px solid ${color}22` }}>
                                <div style={{ fontSize: '0.65rem', fontWeight: 700, color, textTransform: 'uppercase' }}>{label}</div>
                                <div style={{ fontSize: '1.1rem', fontWeight: 900, color }}>{val}</div>
                                <div style={{ fontSize: '0.6rem', color: 'var(--on-surface-variant)' }}>kg/ha</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <MasCampos>
                <FieldGroup label="Datos de suelo">
                    <ZoomInput label="Datos de suelo" value={f.datos_suelo}
                        placeholder="Ej: Análisis 2024 — pH 7.5, M.O. 1.2%, textura franca…"
                        multiline onConfirm={v => set('datos_suelo', v)} />
                </FieldGroup>
                <FieldGroup label="Abono recomendado">
                    <input type="text" className="input-field" value={f.abono_recomendado}
                        placeholder="Ej: Urea 46%, NPK 8-15-15…"
                        onChange={e => set('abono_recomendado', e.target.value)} />
                </FieldGroup>
                <FieldGroup label="Dosis recomendada (kg/ha)">
                    <ZoomInput label="Dosis (kg/ha)" value={f.dosis_recomendada_kg_ha}
                        placeholder="Ej: 250" inputMode="decimal"
                        onConfirm={v => set('dosis_recomendada_kg_ha', v)} />
                </FieldGroup>
                <FieldGroup label="Notas">
                    <ZoomInput label="Notas" value={f.notas} placeholder="Observaciones…"
                        multiline onConfirm={v => set('notas', v)} />
                </FieldGroup>
            </MasCampos>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <button className="btn-ghost" onClick={() => onClose()} style={{ flex: 1 }}>Cancelar</button>
                <button className="btn-primary" onClick={save} disabled={saving} style={{ flex: 2 }}>
                    {saving ? 'Guardando…' : (isEdit ? 'Guardar cambios' : '📋 Guardar plan')}
                </button>
            </div>
        </div>
    );
}

// ── FormCultivoCampana ──────────────────────────────────────────────────────
function FormCultivoCampana({ parcelas, record, campana, onClose, isEdit }) {
    const [saving, setSaving] = React.useState(false);
    const [parcela_id, setParcelaId] = React.useState(record?.parcela_id || '');
    const [parcelaHa, setParcelaHa] = React.useState(null);
    const [existingHa, setExistingHa] = React.useState(0);

    React.useEffect(() => {
        if (!parcela_id) { setParcelaHa(null); setExistingHa(0); return; }
        const p = parcelas.find(x => String(x.id) === String(parcela_id));
        setParcelaHa(p?.superficie_ha ?? null);
        fetch(`/api/cultivos-campana?parcela_id=${parcela_id}&campana=${encodeURIComponent(campana)}`, { credentials: 'include' })
            .then(r => r.json())
            .then(data => {
                if (!Array.isArray(data)) { setExistingHa(0); return; }
                let allocated = data.reduce((sum, cv) => sum + (parseFloat(cv.superficie_cultivada_ha) || 0), 0);
                if (isEdit && record?.id) {
                    const thisOne = data.find(cv => cv.id === record.id);
                    if (thisOne) allocated -= (parseFloat(thisOne.superficie_cultivada_ha) || 0);
                }
                setExistingHa(allocated);
            })
            .catch(() => setExistingHa(0));
    }, [parcela_id]);

    const emptyEntry = () => ({
        _key: Math.random(),
        _id: null,
        cultivo_iacs_cod: '',
        cultivo: '',
        variedad: '',
        fecha_siembra: '',
        fecha_recoleccion_prevista: '',
        superficie_cultivada_ha: '',
        kg_sembrados: '',
        precio_kg_compra: '',
        notas: '',
    });

    const [cultivos, setCultivos] = React.useState(() =>
        isEdit && record
            ? [{ ...emptyEntry(), _id: record.id, cultivo_iacs_cod: record.cultivo_iacs_cod || '',
                 cultivo: record.cultivo || '', variedad: record.variedad || '',
                 fecha_siembra: record.fecha_siembra || '',
                 fecha_recoleccion_prevista: record.fecha_recoleccion_prevista || '',
                 superficie_cultivada_ha: record.superficie_cultivada_ha || '',
                 kg_sembrados: record.kg_sembrados || '',
                 precio_kg_compra: record.precio_kg_compra || '',
                 notas: record.notas || '' }]
            : [emptyEntry()]
    );

    const setField = (idx, k, v) => setCultivos(prev => {
        const next = [...prev];
        next[idx] = { ...next[idx], [k]: v };
        return next;
    });

    const addEntry = () => setCultivos(prev => [...prev, emptyEntry()]);
    const removeEntry = (idx) => setCultivos(prev => prev.filter((_, i) => i !== idx));

    const cultivosPorGrupo = (typeof CULTIVOS_IACS !== 'undefined' ? CULTIVOS_IACS : []).reduce((acc, c) => {
        (acc[c.grupo] = acc[c.grupo] || []).push(c);
        return acc;
    }, {});

    const newHa = cultivos.reduce((sum, cv) => sum + (parseFloat(cv.superficie_cultivada_ha) || 0), 0);
    const totalUsedHa = existingHa + newHa;
    const haExceeded = parcelaHa !== null && parcelaHa > 0 && totalUsedHa > parcelaHa + 0.001;

    const save = async () => {
        if (!parcela_id) { alert('Selecciona una parcela'); return; }
        for (const cv of cultivos) {
            if (!cv.cultivo_iacs_cod) { alert('Selecciona el cultivo (código IACS) en todos los bloques'); return; }
        }
        if (haExceeded) {
            alert(`La superficie asignada (${totalUsedHa.toFixed(2)} ha) supera las ${parcelaHa.toFixed(2)} ha totales de la parcela`);
            return;
        }
        setSaving(true);
        try {
            for (const cv of cultivos) {
                const body = {
                    parcela_id, campana,
                    cultivo: cv.cultivo, cultivo_iacs_cod: cv.cultivo_iacs_cod,
                    variedad: cv.variedad, fecha_siembra: cv.fecha_siembra,
                    fecha_recoleccion_prevista: cv.fecha_recoleccion_prevista,
                    superficie_cultivada_ha: cv.superficie_cultivada_ha,
                    kg_sembrados: cv.kg_sembrados,
                    precio_kg_compra: cv.precio_kg_compra,
                    notas: cv.notas,
                };
                const url = (isEdit && cv._id) ? `/api/cultivos-campana/${cv._id}` : '/api/cultivos-campana';
                const method = (isEdit && cv._id) ? 'PUT' : 'POST';
                const res = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                    credentials: 'include',
                });
                if (!res.ok) {
                    const d = await res.json().catch(() => ({}));
                    alert(d.error || 'Error al guardar');
                    setSaving(false);
                    return;
                }
            }
            const msg = cultivos.length > 1 ? `✅ ${cultivos.length} cultivos guardados` : '✅ Cultivo guardado';
            onClose(msg);
        } catch (e) {
            alert('Error al guardar');
            setSaving(false);
        }
    };

    return (
        <div>
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={parcela_id} onChange={v => setParcelaId(v)} disabled={isEdit} />
            </FieldGroup>

            {parcelaHa !== null && parcelaHa > 0 && (
                <div style={{
                    background: haExceeded ? '#fef2f2' : (totalUsedHa > 0 ? '#f0fdf4' : '#f9fafb'),
                    border: `1px solid ${haExceeded ? '#fca5a5' : '#d1fae5'}`,
                    borderRadius: 8, padding: '8px 12px', marginBottom: 12,
                    fontSize: '0.82rem',
                    color: haExceeded ? '#dc2626' : '#166534',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                    <span>
                        {haExceeded ? '⚠️ ' : '📐 '}
                        <strong>{totalUsedHa.toFixed(2)} ha</strong> asignadas de <strong>{parcelaHa.toFixed(2)} ha</strong> totales
                        {existingHa > 0 && <span style={{ opacity: 0.75 }}> ({existingHa.toFixed(2)} ya registradas)</span>}
                    </span>
                    {haExceeded && <span style={{ fontWeight: 600 }}>¡Excede la parcela!</span>}
                </div>
            )}

            {cultivos.map((cv, idx) => (
                <div key={cv._key} style={{
                    border: '1px solid #e5e7eb', borderRadius: 10, padding: '14px 12px',
                    marginBottom: 12, background: '#fafafa', position: 'relative',
                }}>
                    {cultivos.length > 1 && (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                            <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#374151' }}>
                                Cultivo {idx + 1}
                            </span>
                            <button onClick={() => removeEntry(idx)}
                                style={{ background: 'none', border: 'none', color: '#dc2626', fontSize: '1.1rem', cursor: 'pointer', padding: '2px 6px' }}
                                title="Eliminar este cultivo">✕</button>
                        </div>
                    )}

                    <FieldGroup label="Cultivo (código IACS) *">
                        <select className="input-field" value={cv.cultivo_iacs_cod}
                            onChange={e => {
                                const cod = e.target.value;
                                const entry = (typeof CULTIVOS_IACS !== 'undefined' ? CULTIVOS_IACS : []).find(c => c.cod === cod);
                                setField(idx, 'cultivo_iacs_cod', cod);
                                setField(idx, 'cultivo', entry ? entry.nombre : cv.cultivo);
                            }}>
                            <option value="">Seleccionar cultivo…</option>
                            {Object.entries(cultivosPorGrupo).map(([grupo, items]) => (
                                <optgroup key={grupo} label={grupo}>
                                    {items.map(c => <option key={c.cod} value={c.cod}>{c.nombre}</option>)}
                                </optgroup>
                            ))}
                        </select>
                        {cv.cultivo_iacs_cod && (
                            <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: 4 }}>
                                Código IACS: <strong>{cv.cultivo_iacs_cod}</strong>
                            </div>
                        )}
                    </FieldGroup>

                    <div className="responsive-grid cols-2">
                        <FieldGroup label="Variedad">
                            <input type="text" className="input-field" placeholder="Picual, Tempranillo…"
                                value={cv.variedad} onChange={e => setField(idx, 'variedad', e.target.value)} />
                        </FieldGroup>
                        <FieldGroup label="Superficie cultivada (ha)">
                            <ZoomInput label="Superficie cultivada (ha)" type="number" inputMode="decimal"
                                value={cv.superficie_cultivada_ha} onConfirm={v => setField(idx, 'superficie_cultivada_ha', v)} />
                        </FieldGroup>
                        <FieldGroup label="Fecha de siembra">
                            <input type="date" className="input-field" value={cv.fecha_siembra}
                                onChange={e => setField(idx, 'fecha_siembra', e.target.value)} />
                        </FieldGroup>
                        <FieldGroup label="Fecha recolección prevista">
                            <input type="date" className="input-field" value={cv.fecha_recoleccion_prevista}
                                onChange={e => setField(idx, 'fecha_recoleccion_prevista', e.target.value)} />
                        </FieldGroup>
                        <FieldGroup label="Kg sembrados">
                            <ZoomInput label="Kg sembrados" type="number" inputMode="decimal"
                                value={cv.kg_sembrados} onConfirm={v => setField(idx, 'kg_sembrados', v)} />
                        </FieldGroup>
                        <FieldGroup label="Precio/kg compra (€)">
                            <ZoomInput label="Precio/kg compra (€)" type="number" inputMode="decimal"
                                value={cv.precio_kg_compra} onConfirm={v => setField(idx, 'precio_kg_compra', v)} />
                        </FieldGroup>
                    </div>

                    <FieldGroup label="Notas">
                        <textarea className="input-field" rows={2} value={cv.notas}
                            onChange={e => setField(idx, 'notas', e.target.value)} />
                    </FieldGroup>
                </div>
            ))}

            {!isEdit && (
                <button onClick={addEntry} style={{
                    width: '100%', padding: '10px', marginBottom: 14,
                    background: '#f0fdf4', border: '1px dashed #16a34a', borderRadius: 8,
                    color: '#16a34a', fontWeight: 600, fontSize: '0.9rem', cursor: 'pointer',
                }}>
                    + Añadir otro cultivo
                </button>
            )}

            <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                <button className="btn-ghost" onClick={() => onClose()} style={{ flex: 1 }}>Cancelar</button>
                <button className="btn-primary" onClick={save} disabled={saving} style={{ flex: 2 }}>
                    {saving ? 'Guardando…' : '🌾 Guardar cultivo' + (cultivos.length > 1 ? `s (${cultivos.length})` : '')}
                </button>
            </div>
        </div>
    );
}
