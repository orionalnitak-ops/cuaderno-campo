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
        fertilizacion: { icon: '🌱', title: 'Abono',                     color: '#4f46e5' },
        labor:         { icon: '🚜', title: 'Labor Agrícola',            color: '#1d4ed8' },
        cosecha:       { icon: '📦', title: 'Cosecha / Producción',      color: '#db2777' },
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

    const save = async () => {
        if (!f.parcela_id || !f.fecha_aplicacion || !f.producto_comercial) {
            alert('Rellena los campos obligatorios: parcela, fecha y producto'); return;
        }
        setSaving(true);
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/tratamientos/${record.id}` : '/api/tratamientos';
        await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        onClose('✅ Tratamiento guardado');
    };

    return (
        <div>
            <FieldGroup label="Parcela *">
                <ParcelSelect parcelas={parcelas} value={f.parcela_id} onChange={v => set('parcela_id', v)} />
            </FieldGroup>
            <div className="responsive-grid cols-2">
                <FieldGroup label="Fecha de aplicación *">
                    <input type="date" className="input-field" value={f.fecha_aplicacion} onChange={e => set('fecha_aplicacion', e.target.value)} />
                </FieldGroup>
                <FieldGroup label="Producto comercial *">
                    <input className="input-field" value={f.producto_comercial} onChange={e => set('producto_comercial', e.target.value)} placeholder="Nombre del producto" />
                </FieldGroup>
            </div>

            <MasCampos>
                <div className="responsive-grid cols-2">
                    <FieldGroup label="Plaga / Objetivo">
                        <input className="input-field" value={f.plaga_objetivo} onChange={e => set('plaga_objetivo', e.target.value)} placeholder="Repilo, Antracnosis…" />
                    </FieldGroup>
                    <FieldGroup label="Sustancia activa">
                        <input className="input-field" value={f.sustancia_activa} onChange={e => set('sustancia_activa', e.target.value)} placeholder="Cobre, Glifosato…" />
                    </FieldGroup>
                    <FieldGroup label="Nº Registro MAPA">
                        <input className="input-field" value={f.num_registro_mapa} onChange={e => set('num_registro_mapa', e.target.value)} placeholder="ES-00000-0" />
                    </FieldGroup>
                    <FieldGroup label="Dosis">
                        <div style={{ display: 'flex', gap: 8 }}>
                            <input type="number" step="0.01" className="input-field" value={f.dosis_valor} onChange={e => set('dosis_valor', e.target.value)} placeholder="2.5" style={{ flex: 2 }} />
                            <select className="input-field" value={f.dosis_unidad} onChange={e => set('dosis_unidad', e.target.value)} style={{ flex: 1 }}>
                                {['cc/ha', 'g/ha', 'kg/ha', 'L/100L', 'L/ha'].map(u => <option key={u}>{u}</option>)}
                            </select>
                        </div>
                    </FieldGroup>
                    <FieldGroup label="Volumen de caldo (L/ha)">
                        <input type="number" step="1" className="input-field" value={f.volumen_caldo} onChange={e => set('volumen_caldo', e.target.value)} placeholder="300" />
                    </FieldGroup>
                    <FieldGroup label="Condiciones meteorológicas">
                        <input className="input-field" value={f.condiciones_meteo} onChange={e => set('condiciones_meteo', e.target.value)} placeholder="T 22°C · V <3 m/s · HR 45%" />
                    </FieldGroup>
                    <FieldGroup label="Plazo de seguridad (días)">
                        <input type="number" min="0" className="input-field" value={f.plazo_seguridad_dias} onChange={e => set('plazo_seguridad_dias', e.target.value)} placeholder="15" />
                    </FieldGroup>
                    <FieldGroup label="Fecha mínima de cosecha">
                        <input type="date" className="input-field" value={f.fecha_recoleccion_minima} onChange={e => set('fecha_recoleccion_minima', e.target.value)} style={{ borderColor: plazoAlert ? '#ef4444' : undefined }} />
                    </FieldGroup>
                    <FieldGroup label="Equipo de aplicación">
                        <select className="input-field" value={f.equipo_id} onChange={e => set('equipo_id', e.target.value)}>
                            <option value="">Sin especificar</option>
                            {equipos.map(e => <option key={e.id} value={e.id}>{e.descripcion}</option>)}
                        </select>
                    </FieldGroup>
                    <FieldGroup label="Aplicador (ROPO)">
                        <select className="input-field" value={f.aplicador_id} onChange={e => set('aplicador_id', e.target.value)}>
                            <option value="">Sin especificar</option>
                            {aplicadores.map(a => <option key={a.id} value={a.id}>{a.nombre}{a.num_ropo ? ` (${a.num_ropo})` : ''}</option>)}
                        </select>
                    </FieldGroup>
                    <FieldGroup label="Eficacia observada">
                        <select className="input-field" value={f.eficacia} onChange={e => set('eficacia', e.target.value)}>
                            <option value="">Sin evaluar</option>
                            {['Alta', 'Media', 'Baja', 'Muy alta', 'Nula'].map(v => <option key={v}>{v}</option>)}
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
                    <textarea className="input-field" rows={3} value={f.notas} onChange={e => set('notas', e.target.value)} placeholder="Observaciones adicionales…" />
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
        await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        onClose('✅ Abono guardado');
    };

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
                    <input className="input-field" value={f.producto} onChange={e => set('producto', e.target.value)} placeholder="Urea, NPK, Estiércol…" />
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
                        <input className="input-field" value={f.riqueza_npk} onChange={e => set('riqueza_npk', e.target.value)} placeholder="27-0-0 · 8-15-15…" />
                    </FieldGroup>
                    <FieldGroup label="Dosis">
                        <div style={{ display: 'flex', gap: 8 }}>
                            <input type="number" step="0.01" className="input-field" value={f.dosis_valor} onChange={e => set('dosis_valor', e.target.value)} placeholder="200" style={{ flex: 2 }} />
                            <select className="input-field" value={f.dosis_unidad} onChange={e => set('dosis_unidad', e.target.value)} style={{ flex: 1 }}>
                                {['kg/árbol', 'kg/ha', 'L/árbol', 'L/ha', 't/ha'].map(u => <option key={u}>{u}</option>)}
                            </select>
                        </div>
                    </FieldGroup>
                    <FieldGroup label="Método de aplicación">
                        <select className="input-field" value={f.metodo_aplicacion} onChange={e => set('metodo_aplicacion', e.target.value)}>
                            <option value="">Seleccionar…</option>
                            {['Fertirrigación', 'Foliar', 'Incorporado', 'Inyectado', 'Localizado', 'Voleo'].map(m => <option key={m}>{m}</option>)}
                        </select>
                    </FieldGroup>
                </div>
                <FieldGroup label="Notas">
                    <textarea className="input-field" rows={3} value={f.notas} onChange={e => set('notas', e.target.value)} placeholder="Observaciones…" />
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
const _LABOR_TIPOS = ['Aclareo','Alzado','Arado','Desherbado','Escarda','Fresado','Gradeo','Laboreo del suelo','Limpieza','Plantación','Poda','Riego','Siembra','Subsolado','Triturado de restos','Vendimia','Otros'];
const _LABOR_MAP = {'arado':'Arado','are':'Arado','poda':'Poda','pode':'Poda','desherbado':'Desherbado','desyerbado':'Desherbado','desbroz':'Desherbado','siembra':'Siembra','sembrado':'Siembra','siembre':'Siembra','sembre':'Siembra','fresado':'Fresado','subsolado':'Subsolado','gradeo':'Gradeo','pase':'Gradeo','limpieza':'Limpieza','limpie':'Limpieza','laboreo':'Laboreo del suelo','labrado':'Laboreo del suelo','labor':'Laboreo del suelo','cultivado':'Laboreo del suelo','vendimia':'Vendimia','vendimiado':'Vendimia','escarda':'Escarda','cave':'Escarda','cavado':'Escarda','trilla':'Triturado de restos','trillado':'Triturado de restos','riego':'Riego','regado':'Riego'};
const normTipoLabor = (v) => { if (!v) return ''; if (_LABOR_TIPOS.includes(v)) return v; return _LABOR_MAP[(v||'').toLowerCase().trim()] || ''; };

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
        const method = isEdit ? 'PUT' : 'POST';
        const url = isEdit ? `/api/labores/${record.id}` : '/api/labores';
        await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
        onClose('✅ Labor guardada');
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
                        {['Aclareo', 'Alzado', 'Arado', 'Desherbado', 'Escarda', 'Fresado', 'Gradeo', 'Laboreo del suelo', 'Limpieza', 'Plantación', 'Poda', 'Riego', 'Siembra', 'Subsolado', 'Triturado de restos', 'Vendimia', 'Otros'].map(t => <option key={t}>{t}</option>)}
                    </select>
                </FieldGroup>
            </div>
            <FieldGroup label="Cultivo / Producto sembrado">
                <datalist id="labor-productos">
                    {['Trigo','Cebada','Avena','Centeno','Triticale','Maíz','Girasol','Colza',
                      'Yeros','Veza','Guisante','Garbanzo','Lenteja','Almorta','Soja',
                      'Alfalfa','Remolacha','Patata','Tomate','Pimiento','Cebolla','Ajo',
                      'Olivo','Vid','Almendro','Pistachero','Otros'].map(p =>
                        <option key={p} value={p} />
                    )}
                </datalist>
                <input list="labor-productos" className="input-field" value={f.producto}
                    onChange={e => set('producto', e.target.value)}
                    placeholder="Ej: Trigo, Cebada, Yeros… (o escribe el tuyo)" />
            </FieldGroup>

            <MasCampos>
                <div className="responsive-grid cols-2">
                    <FieldGroup label="Descripción">
                        <input className="input-field" value={f.descripcion} onChange={e => set('descripcion', e.target.value)} placeholder="Detalle de la operación…" />
                    </FieldGroup>
                    <FieldGroup label="Maquinaria">
                        <input className="input-field" value={f.maquinaria} onChange={e => set('maquinaria', e.target.value)} placeholder="Tractor, vibrador…" />
                    </FieldGroup>
                    <FieldGroup label="Horas trabajadas">
                        <input type="number" step="0.5" min="0" className="input-field" value={f.horas_trabajadas} onChange={e => set('horas_trabajadas', e.target.value)} placeholder="4.5" />
                    </FieldGroup>
                    <FieldGroup label="Operario / Empresa">
                        <input className="input-field" value={f.operario} onChange={e => set('operario', e.target.value)} placeholder="Nombre o empresa" />
                    </FieldGroup>
                </div>
                <FieldGroup label="Notas">
                    <textarea className="input-field" rows={3} value={f.notas} onChange={e => set('notas', e.target.value)} placeholder="Observaciones…" />
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
        await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f), credentials: 'include' });
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
                    <input className="input-field" value={f.cultivo} onChange={e => set('cultivo', e.target.value)} placeholder="Olivar, Viñedo, Cereal…" />
                </FieldGroup>
            </div>

            <MasCampos>
                <div className="responsive-grid cols-2">
                    <FieldGroup label="Fecha fin recolección">
                        <input type="date" className="input-field" value={f.fecha_fin} onChange={e => set('fecha_fin', e.target.value)} />
                    </FieldGroup>
                    <FieldGroup label="Variedad">
                        <input className="input-field" value={f.variedad} onChange={e => set('variedad', e.target.value)} placeholder="Picual, Tempranillo…" />
                    </FieldGroup>
                    <FieldGroup label="Superficie cosechada (ha)">
                        <input type="number" step="0.001" className="input-field" value={f.superficie_cosechada_ha} onChange={e => set('superficie_cosechada_ha', e.target.value)} placeholder="3.25" />
                    </FieldGroup>
                    <FieldGroup label={`Producción total${rendimiento ? ` → ${rendimiento}` : ''}`}>
                        <div style={{ display: 'flex', gap: 8 }}>
                            <input type="number" step="0.01" className="input-field" value={f.produccion_total_valor} onChange={e => set('produccion_total_valor', e.target.value)} placeholder="12500" style={{ flex: 2 }} />
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
                        <input className="input-field" value={f.comprador} onChange={e => set('comprador', e.target.value)} placeholder="Nombre de la cooperativa" />
                    </FieldGroup>
                    <FieldGroup label="Precio por unidad (€)">
                        <input type="number" step="0.001" className="input-field" value={f.precio_unidad} onChange={e => set('precio_unidad', e.target.value)} placeholder="0.350 €/kg" />
                    </FieldGroup>
                </div>
                <FieldGroup label="Notas">
                    <textarea className="input-field" rows={3} value={f.notas} onChange={e => set('notas', e.target.value)} placeholder="Observaciones…" />
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
