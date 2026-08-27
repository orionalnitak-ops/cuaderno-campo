// ── Field Zoom Overlay — campo individual a pantalla grande para móvil ──
function FieldZoomOverlay({ label, value, type, placeholder, onConfirm, onClose }) {
    const [val, setVal] = React.useState(value || '');
    const inputRef = React.useRef(null);

    React.useEffect(() => {
        setTimeout(() => { if (inputRef.current) inputRef.current.focus(); }, 80);
    }, []);

    const confirm = () => onConfirm(val.trim());

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
                <div style={{
                    background: 'linear-gradient(135deg, #1D9E75, #00694c)',
                    padding: '24px 20px',
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <div style={{ fontSize: '0.68rem', color: 'rgba(255,255,255,0.6)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
                                Editando
                            </div>
                            <h2 style={{ fontFamily: 'Manrope', fontWeight: 800, color: '#fff', fontSize: '1.4rem', margin: 0 }}>
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
                    <input
                        ref={inputRef}
                        type={type || 'text'}
                        value={val}
                        onChange={e => setVal(e.target.value)}
                        placeholder={placeholder}
                        onKeyDown={e => { if (e.key === 'Enter') confirm(); if (e.key === 'Escape') onClose(); }}
                        style={{
                            width: '100%', boxSizing: 'border-box',
                            fontSize: '1.35rem', fontFamily: 'Manrope, Work Sans, sans-serif',
                            fontWeight: 600, padding: '16px 18px',
                            border: '2px solid #1D9E75', borderRadius: 14,
                            outline: 'none', background: '#f0fdf4', color: '#111827',
                        }}
                    />
                </div>
                {/* multiline no se usa en settings pero se deja por consistencia */}
                <div style={{ padding: '0 20px 28px' }}>
                    <button className="btn-primary" onClick={confirm} style={{ width: '100%', fontSize: '1rem', padding: '16px', minHeight: 52 }}>
                        ✓ Listo
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Explotación modal (position:fixed → teclado Android funciona) ──
function ExplotacionModal({ data, onSave, onClose }) {
    const { useState } = React;
    const [form, setForm] = useState(data || {});
    const [saving, setSaving] = useState(false);
    const [zoomField, setZoomField] = useState(null);

    const save = async () => {
        setSaving(true);
        await fetch('/api/explotacion', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(form),
        });
        onSave(form);
        setSaving(false);
    };

    const FIELDS = [
        ['nombre_corto','Nombre corto','text','Ej: Juan, Dolores, Francisco…', 'Etiqueta breve para distinguir esta explotación en el selector superior.'],
        ['titular','Titular','text','Nombre completo'],
        ['nif','NIF / CIF','text','12345678A'],
        ['rega','Código REGA','text','ej: ES-CM-12345', 'Número de Registro de Explotaciones Agrícolas. Lo facilita la Consejería de Agricultura de tu comunidad autónoma.'],
        ['municipio','Municipio','text','Santa Cruz de Mudela'],
        ['provincia','Provincia','text','Ciudad Real'],
        ['cp','Código postal','text','13730'],
        ['telefono','Teléfono','tel','600 000 000'],
        ['email','Email','email','titular@explotacion.es'],
        ['campana_activa','Campaña activa','text','2025/2026'],
    ];

    return (
        <>
        <div className="overlay" onClick={onClose}>
            <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom: 40 }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                    <h3 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', margin:0 }}>🏡 Datos de la Explotación</h3>
                    <button onClick={onClose} style={{ background:'none', border:'none', fontSize:22, cursor:'pointer', color:'#6b7280' }}>✕</button>
                </div>
                {FIELDS.map(([k,l,t,ph,help]) => (
                    <div key={k} style={{ marginBottom:14 }}>
                        <label className="field-label">{l}</label>
                        <input type={t} className="input-field" value={form[k]||''} readOnly placeholder={ph}
                            onClick={() => setZoomField({ key:k, label:l, type:t, placeholder:ph })}
                            style={{ cursor:'pointer' }} />
                        {help && <p style={{ fontSize:'0.75rem', color:'#6b7280', marginTop:4, marginBottom:0 }}>{help}</p>}
                    </div>
                ))}
                <button className="btn-primary" style={{ width:'100%', marginTop:8 }} onClick={save} disabled={saving}>
                    {saving ? 'Guardando…' : '💾 Guardar datos'}
                </button>
            </div>
        </div>
        {zoomField && (
            <FieldZoomOverlay
                label={zoomField.label}
                value={form[zoomField.key] || ''}
                type={zoomField.type}
                placeholder={zoomField.placeholder}
                onConfirm={val => { setForm(f => ({ ...f, [zoomField.key]: val })); setZoomField(null); }}
                onClose={() => setZoomField(null)}
            />
        )}
        </>
    );
}

// ── Explotación section — muestra resumen + botón editar (modal) ──
function ExplotacionSection({ showToast, onCampana }) {
    const { useState, useEffect } = React;
    const [data, setData]     = useState(null);
    const [showModal, setShowModal] = useState(false);

    useEffect(() => {
        fetch('/api/explotacion').then(r => r.json()).then(d => setData(d || {}));
    }, []);

    const handleSave = (form) => {
        setData(form);
        if (form.campana_activa) onCampana(form.campana_activa);
        showToast('Datos guardados correctamente');
        setShowModal(false);
    };

    const row = (label, value) => value ? (
        <div style={{ display:'flex', gap:8, fontSize:'0.85rem', padding:'6px 0', borderBottom:'1px solid #f3f4f6' }}>
            <span style={{ color:'#6b7280', minWidth:130 }}>{label}</span>
            <span style={{ color:'#111827', fontWeight:600 }}>{value}</span>
        </div>
    ) : null;

    return (
        <div>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                <h2 className="section-title" style={{ margin:0 }}>Datos de la Explotación</h2>
                <button className="btn-primary" style={{ padding:'10px 16px', fontSize:'0.85rem' }}
                    onClick={() => setShowModal(true)}>
                    ✏️ Editar
                </button>
            </div>
            {data === null ? (
                <p style={{ color:'#9ca3af' }}>Cargando…</p>
            ) : (
                <div className="card card-p">
                    {row('Titular', data.titular)}
                    {row('NIF / CIF', data.nif)}
                    {row('Municipio', data.municipio)}
                    {row('Provincia', data.provincia)}
                    {row('Código postal', data.cp)}
                    {row('Teléfono', data.telefono)}
                    {row('Email', data.email)}
                    {row('Campaña activa', data.campana_activa)}
                    {!data.titular && (
                        <p style={{ color:'#9ca3af', fontSize:'0.85rem', margin:0 }}>
                            Pulsa "Editar" para rellenar los datos de tu explotación.
                        </p>
                    )}
                </div>
            )}
            {showModal && data !== null && (
                <ExplotacionModal
                    data={data}
                    onSave={handleSave}
                    onClose={() => setShowModal(false)}
                />
            )}
        </div>
    );
}

// ── Equipo form modal ──
function EquipoModal({ equipo, onSave, onClose }) {
    const { useState } = React;
    const [form, setForm] = useState(equipo || {});
    const [zoomField, setZoomField] = useState(null);
    const EQ_FIELDS = [
        ['descripcion','Descripción / nombre','text'],
        ['tipo','Tipo','text'],
        ['marca','Marca','text'],
        ['modelo','Modelo','text'],
        ['num_registro_roma','Nº Registro ROMA','text'],
        ['fecha_iteaf','Fecha ITEAF','date'],
    ];
    return (
        <>
        <div className="overlay" onClick={onClose}>
            <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom: 40 }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                    <h3 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', margin:0 }}>
                        🚜 {equipo && equipo.id ? 'Editar equipo' : 'Nuevo equipo'}
                    </h3>
                    <button onClick={onClose} style={{ background:'none', border:'none', fontSize:22, cursor:'pointer', color:'#6b7280' }}>✕</button>
                </div>
                {EQ_FIELDS.map(([k,l,t]) => (
                    <div key={k} style={{ marginBottom:14 }}>
                        <label className="field-label">{l}</label>
                        <input type={t} className="input-field" value={form[k]||''} readOnly
                            onClick={() => setZoomField({ key:k, label:l, type:t, placeholder:'' })}
                            style={{ cursor:'pointer' }} />
                    </div>
                ))}
                {/* feature 022 (bloque 5/8 SIEX): equipo propio o ajeno — la mayoría
                    de equipos registrados hoy son del propio agricultor, así que
                    "sin especificar" se trata como propio. Si se marca ajeno, pide
                    el NIF del propietario; si se vuelve a marcar propio, se limpia
                    (mismo bug ya corregido en cosecha con los datos de cliente). */}
                <div style={{ marginBottom:14 }}>
                    <label className="field-label">¿Equipo propio?</label>
                    <select className="input-field" value={form.propio === false ? 'no' : 'si'}
                        onChange={e => {
                            const propio = e.target.value !== 'no';
                            setForm(f => ({ ...f, propio, nif_propietario: propio ? '' : f.nif_propietario }));
                        }}>
                        <option value="si">Sí</option>
                        <option value="no">No (equipo ajeno)</option>
                    </select>
                </div>
                {form.propio === false && (
                    <div style={{ marginBottom:14 }}>
                        <label className="field-label">NIF del propietario</label>
                        <input type="text" className="input-field" value={form.nif_propietario||''} readOnly
                            onClick={() => setZoomField({ key:'nif_propietario', label:'NIF del propietario', type:'text', placeholder:'' })}
                            style={{ cursor:'pointer' }} />
                    </div>
                )}
                <button className="btn-primary" style={{ width:'100%', marginTop:8 }} onClick={() => onSave(form)}>
                    {equipo && equipo.id ? 'Actualizar equipo' : 'Añadir equipo'}
                </button>
            </div>
        </div>
        {zoomField && (
            <FieldZoomOverlay
                label={zoomField.label}
                value={form[zoomField.key] || ''}
                type={zoomField.type}
                placeholder={zoomField.placeholder}
                onConfirm={val => { setForm(f => ({ ...f, [zoomField.key]: val })); setZoomField(null); }}
                onClose={() => setZoomField(null)}
            />
        )}
        </>
    );
}

// ── Aplicador form modal ──
function AplicadorModal({ aplicador, onSave, onClose }) {
    const { useState } = React;
    const [form, setForm] = useState(aplicador || {});
    const [zoomField, setZoomField] = useState(null);
    const AP_FIELDS = [
        ['nombre','Nombre completo','text'],
        ['nif','NIF','text'],
        ['num_ropo','Nº ROPO','text'],
    ];
    return (
        <>
        <div className="overlay" onClick={onClose}>
            <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom: 40 }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                    <h3 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', margin:0 }}>
                        👤 {aplicador && aplicador.id ? 'Editar aplicador' : 'Nuevo aplicador'}
                    </h3>
                    <button onClick={onClose} style={{ background:'none', border:'none', fontSize:22, cursor:'pointer', color:'#6b7280' }}>✕</button>
                </div>
                {AP_FIELDS.map(([k,l,t]) => (
                    <div key={k} style={{ marginBottom:14 }}>
                        <label className="field-label">{l}</label>
                        <input type={t} className="input-field" value={form[k]||''} readOnly
                            onClick={() => setZoomField({ key:k, label:l, type:t, placeholder:'' })}
                            style={{ cursor:'pointer' }} />
                    </div>
                ))}
                <button className="btn-primary" style={{ width:'100%', marginTop:8 }} onClick={() => onSave(form)}>
                    {aplicador && aplicador.id ? 'Actualizar aplicador' : 'Añadir aplicador'}
                </button>
            </div>
        </div>
        {zoomField && (
            <FieldZoomOverlay
                label={zoomField.label}
                value={form[zoomField.key] || ''}
                type={zoomField.type}
                placeholder={zoomField.placeholder}
                onConfirm={val => { setForm(f => ({ ...f, [zoomField.key]: val })); setZoomField(null); }}
                onClose={() => setZoomField(null)}
            />
        )}
        </>
    );
}

// ── Asesor form modal ──
// Asesor fitosanitario (Orden APA/204/2023). El nº ROPO es de la sección "asesor"
// del carnet, distinta de la de aplicador, y aquí NO es bloqueante.
function AsesorModal({ asesor, onSave, onClose }) {
    const { useState } = React;
    const [form, setForm] = useState(asesor || {});
    const [zoomField, setZoomField] = useState(null);
    const AS_FIELDS = [
        ['nombre','Nombre completo','text'],
        ['nif','NIF','text'],
        ['num_ropo','Nº ROPO (sección asesor)','text'],
        ['titulacion','Titulación / nº colegiado','text'],
        ['empresa','Empresa asesora','text'],
        ['telefono','Teléfono','text'],
        ['email','Email','text'],
    ];
    return (
        <>
        <div className="overlay" onClick={onClose}>
            <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom: 40 }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                    <h3 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', margin:0 }}>
                        🎓 {asesor && asesor.id ? 'Editar asesor' : 'Nuevo asesor'}
                    </h3>
                    <button onClick={onClose} style={{ background:'none', border:'none', fontSize:22, cursor:'pointer', color:'#6b7280' }}>✕</button>
                </div>
                {AS_FIELDS.map(([k,l,t]) => (
                    <div key={k} style={{ marginBottom:14 }}>
                        <label className="field-label">{l}</label>
                        <input type={t} className="input-field" value={form[k]||''} readOnly
                            onClick={() => setZoomField({ key:k, label:l, type:t, placeholder:'' })}
                            style={{ cursor:'pointer' }} />
                    </div>
                ))}
                <button className="btn-primary" style={{ width:'100%', marginTop:8 }} onClick={() => onSave(form)}>
                    {asesor && asesor.id ? 'Actualizar asesor' : 'Añadir asesor'}
                </button>
            </div>
        </div>
        {zoomField && (
            <FieldZoomOverlay
                label={zoomField.label}
                value={form[zoomField.key] || ''}
                type={zoomField.type}
                placeholder={zoomField.placeholder}
                onConfirm={val => { setForm(f => ({ ...f, [zoomField.key]: val })); setZoomField(null); }}
                onClose={() => setZoomField(null)}
            />
        )}
        </>
    );
}

// ── Screen: Ajustes / Más ──
function ScreenSettings({ campana, onCampana, showToast, currentUser, onLogout, onNavigate, initialSection }) {
    const { useState, useEffect } = React;
    // initialSection lo manda la "Revisión del cuaderno" al pulsar "Arreglar
    // ahora", para aterrizar donde está el problema y no en la portada.
    const [section, setSection] = useState(initialSection || 'explotacion');
    const [equipos, setEquipos] = useState([]);
    const [aplicadores, setAplicadores] = useState([]);
    const [asesores, setAsesores] = useState([]);

    const [showEqModal, setShowEqModal]   = useState(false);
    const [showApModal, setShowApModal]   = useState(false);
    const [showAsModal, setShowAsModal]   = useState(false);
    const [editingAs, setEditingAs] = useState(null);
    const [editingEq, setEditingEq] = useState(null);
    const [editingAp, setEditingAp] = useState(null);
    const [showQuickStart, setShowQuickStart] = useState(false);

    useEffect(() => {
        fetch('/api/equipos', { credentials: 'include' }).then(r => r.json()).then(d => setEquipos(Array.isArray(d) ? d : []));
        fetch('/api/aplicadores', { credentials: 'include' }).then(r => r.json()).then(d => setAplicadores(Array.isArray(d) ? d : []));
        fetch('/api/asesores', { credentials: 'include' }).then(r => r.json()).then(d => setAsesores(Array.isArray(d) ? d : []));
    }, []);

    const saveEquipo = async (form) => {
        const method = editingEq ? 'PUT' : 'POST';
        const url = editingEq ? `/api/equipos/${editingEq}` : '/api/equipos';
        await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(form), credentials: 'include' });
        showToast(editingEq ? 'Equipo actualizado' : 'Equipo añadido');
        fetch('/api/equipos', { credentials: 'include' }).then(r => r.json()).then(d => setEquipos(Array.isArray(d) ? d : []));
        setShowEqModal(false); setEditingEq(null);
    };

    const deleteEquipo = async (id) => {
        if (!confirm('¿Eliminar este equipo?')) return;
        await fetch(`/api/equipos/${id}`, { method:'DELETE', credentials: 'include' });
        showToast('Equipo eliminado');
        setEquipos(e => e.filter(x => x.id !== id));
    };

    const saveAplicador = async (form) => {
        const method = editingAp ? 'PUT' : 'POST';
        const url = editingAp ? `/api/aplicadores/${editingAp}` : '/api/aplicadores';
        await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(form), credentials: 'include' });
        showToast(editingAp ? 'Aplicador actualizado' : 'Aplicador añadido');
        fetch('/api/aplicadores', { credentials: 'include' }).then(r => r.json()).then(d => setAplicadores(Array.isArray(d) ? d : []));
        setShowApModal(false); setEditingAp(null);
    };

    const deleteAplicador = async (id) => {
        if (!confirm('¿Eliminar este aplicador?')) return;
        await fetch(`/api/aplicadores/${id}`, { method:'DELETE', credentials: 'include' });
        showToast('Aplicador eliminado');
        setAplicadores(a => a.filter(x => x.id !== id));
    };

    const saveAsesor = async (form) => {
        if (!(form.nombre || '').trim()) { showToast('El nombre del asesor es obligatorio'); return; }
        const method = editingAs ? 'PUT' : 'POST';
        const url = editingAs ? `/api/asesores/${editingAs}` : '/api/asesores';
        const res = await fetch(url, { method, headers:{'Content-Type':'application/json'},
            body: JSON.stringify(form), credentials:'include' });
        if (!res.ok) { showToast('Error al guardar el asesor'); return; }
        showToast(editingAs ? 'Asesor actualizado' : 'Asesor añadido');
        fetch('/api/asesores', { credentials:'include' }).then(r => r.json()).then(d => setAsesores(Array.isArray(d) ? d : []));
        setShowAsModal(false); setEditingAs(null);
    };

    const deleteAsesor = async (id) => {
        if (!confirm('¿Eliminar este asesor? Los tratamientos ya registrados conservarán su nombre.')) return;
        await fetch(`/api/asesores/${id}`, { method:'DELETE', credentials:'include' });
        showToast('Asesor eliminado');
        setAsesores(a => a.filter(x => x.id !== id));
    };

    const isAdmin = currentUser?.role === 'admin';

    const SECTIONS = [
        { id: 'explotacion',  icon: '🏡', label: 'Explotación' },
        { id: 'equipos',      icon: '🚜', label: 'Equipos' },
        { id: 'aplicadores',  icon: '👤', label: 'Aplicadores' },
        { id: 'asesores',     icon: '🎓', label: 'Asesores' },
        { id: 'datos',        icon: '💾', label: 'Datos y exportación' },
        { id: 'cuenta',       icon: '🔑', label: 'Mi cuenta' },
        ...(!isAdmin ? [{ id: 'suscripcion', icon: '💳', label: 'Suscripción' }] : []),
        { id: 'legal',        icon: '📄', label: 'Legal y privacidad' },
    ];

    return (
        <div style={{ paddingBottom: 32 }}>
            <div style={{ background:'linear-gradient(135deg,#111827,#1f2937)', padding:'52px 20px 20px' }}>
                <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
                    <h1 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.4rem', color:'#fff', margin:0 }}>
                        ⚙️ Ajustes
                    </h1>
                    <HelpButton screenId="mas" />
                </div>
            </div>

            <div style={{ background:'#fff', borderBottom:'1px solid #f3f4f6', display:'flex', gap:0, overflowX:'auto' }}>
                {SECTIONS.map(s => (
                    <button key={s.id} onClick={() => setSection(s.id)} style={{
                        background:'none', border:'none', borderBottom: section===s.id ? '2px solid #1D9E75' : '2px solid transparent',
                        padding:'14px 16px', cursor:'pointer', whiteSpace:'nowrap',
                        color: section===s.id ? '#1D9E75' : '#6b7280',
                        fontWeight: section===s.id ? 700 : 500,
                        fontSize:'0.82rem', fontFamily:'Work Sans',
                        transition:'all 0.15s',
                    }}>
                        {s.icon} {s.label}
                    </button>
                ))}
            </div>

            {/* ── Revisión del cuaderno ── */}
            <div style={{ padding: '16px 16px 0' }}>
                <CumplTarjeta onNavigate={onNavigate} />
            </div>

            {/* ── Botones soporte + ayuda permanentes ── */}
            <div style={{ padding: '12px 16px 0', display: 'flex', flexDirection: 'column', gap: 8 }}>
                <button
                    onClick={() => setShowQuickStart(true)}
                    style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        background: 'linear-gradient(135deg,#eff6ff,#dbeafe)',
                        border: '1.5px solid #93c5fd',
                        borderRadius: 12, padding: '10px 14px',
                        color: '#1e40af', fontSize: '0.85rem', fontWeight: 600,
                        cursor: 'pointer', textAlign: 'left', width: '100%',
                    }}
                >
                    <span style={{ fontSize: 20 }}>📖</span>
                    <span style={{ flex: 1 }}>Ver guía de inicio</span>
                    <span style={{ fontSize: 16, opacity: 0.6 }}>→</span>
                </button>
                <a
                    href={`mailto:soporte@tualiado.es?subject=${encodeURIComponent('[Cuaderno] Problema — ' + (currentUser?.nombre || currentUser?.email || ''))}&body=${encodeURIComponent('Hola,\n\nTengo un problema con...\n\n\n--- Datos técnicos (no borres) ---\nUsuario: ' + (currentUser?.email || '') + '\nPlan: ' + (currentUser?.plan || 'trial') + '\nFecha: ' + new Date().toLocaleDateString('es-ES'))}`}
                    style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        background: 'linear-gradient(135deg,#f0fdf4,#dcfce7)',
                        border: '1.5px solid #86efac',
                        borderRadius: 12, padding: '10px 14px',
                        textDecoration: 'none', color: '#166534',
                        fontSize: '0.85rem', fontWeight: 600,
                    }}
                >
                    <span style={{ fontSize: 20 }}>🆘</span>
                    <span style={{ flex: 1 }}>¿Tienes un problema? Escríbenos</span>
                    <span style={{ fontSize: 16, opacity: 0.6 }}>→</span>
                </a>
            </div>

            <div style={{ padding: '24px 16px' }}>

                {section === 'explotacion' && (
                    <ExplotacionSection showToast={showToast} onCampana={onCampana} />
                )}

                {section === 'equipos' && (
                    <div>
                        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                            <h2 className="section-title" style={{ margin:0 }}>Equipos de Aplicación</h2>
                            <button className="btn-primary" style={{ padding:'10px 16px', fontSize:'0.85rem' }}
                                onClick={() => { setEditingEq(null); setShowEqModal(true); }}>
                                + Añadir equipo
                            </button>
                        </div>
                        {equipos.length === 0 ? (
                            <div style={{ textAlign:'center', padding:'40px 0', color:'#9ca3af' }}>
                                <div style={{ fontSize:40, marginBottom:8 }}>🚜</div>
                                <p>Sin equipos registrados</p>
                            </div>
                        ) : equipos.map(eq => (
                            <div key={eq.id} className="card card-p" style={{ marginBottom:10, display:'flex', alignItems:'center', gap:12 }}>
                                <div style={{ flex:1 }}>
                                    <div style={{ fontWeight:700, color:'#111827', fontSize:'0.95rem' }}>{eq.descripcion}</div>
                                    <div style={{ fontSize:'0.78rem', color:'#6b7280', marginTop:3 }}>
                                        {[eq.marca, eq.modelo, eq.num_registro_roma].filter(Boolean).join(' · ')}
                                        {eq.fecha_iteaf && <span> · ITEAF: {eq.fecha_iteaf}</span>}
                                    </div>
                                </div>
                                <button onClick={() => { setEditingEq(eq.id); setShowEqModal(true); }}
                                    style={{ background:'none', border:'none', cursor:'pointer', color:'#6b7280', fontSize:18 }}>✏️</button>
                                <button onClick={() => deleteEquipo(eq.id)}
                                    style={{ background:'none', border:'none', cursor:'pointer', color:'#d1d5db', fontSize:18 }}
                                    onMouseEnter={e=>e.currentTarget.style.color='#ef4444'}
                                    onMouseLeave={e=>e.currentTarget.style.color='#d1d5db'}>🗑</button>
                            </div>
                        ))}
                    </div>
                )}

                {section === 'aplicadores' && (
                    <div>
                        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                            <h2 className="section-title" style={{ margin:0 }}>Aplicadores ROPO</h2>
                            <button className="btn-primary" style={{ padding:'10px 16px', fontSize:'0.85rem' }}
                                onClick={() => { setEditingAp(null); setShowApModal(true); }}>
                                + Añadir aplicador
                            </button>
                        </div>
                        {aplicadores.length === 0 ? (
                            <div style={{ textAlign:'center', padding:'40px 0', color:'#9ca3af' }}>
                                <div style={{ fontSize:40, marginBottom:8 }}>👤</div>
                                <p>Sin aplicadores registrados</p>
                            </div>
                        ) : aplicadores.map(ap => (
                            <div key={ap.id} className="card card-p" style={{ marginBottom:10, display:'flex', alignItems:'center', gap:12 }}>
                                <div style={{ flex:1 }}>
                                    <div style={{ fontWeight:700, color:'#111827' }}>{ap.nombre}</div>
                                    <div style={{ fontSize:'0.78rem', color:'#6b7280', marginTop:3 }}>
                                        {[ap.nif, ap.num_ropo ? `ROPO: ${ap.num_ropo}` : ''].filter(Boolean).join(' · ')}
                                    </div>
                                </div>
                                <button onClick={() => { setEditingAp(ap.id); setShowApModal(true); }}
                                    style={{ background:'none', border:'none', cursor:'pointer', color:'#6b7280', fontSize:18 }}>✏️</button>
                                <button onClick={() => deleteAplicador(ap.id)}
                                    style={{ background:'none', border:'none', cursor:'pointer', color:'#d1d5db', fontSize:18 }}
                                    onMouseEnter={e=>e.currentTarget.style.color='#ef4444'}
                                    onMouseLeave={e=>e.currentTarget.style.color='#d1d5db'}>🗑</button>
                            </div>
                        ))}
                    </div>
                )}

                {section === 'asesores' && (
                    <div>
                        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
                            <h2 className="section-title" style={{ margin:0 }}>Asesores fitosanitarios</h2>
                            <button className="btn-primary" style={{ padding:'10px 16px', fontSize:'0.85rem' }}
                                onClick={() => { setEditingAs(null); setShowAsModal(true); }}>
                                + Añadir asesor
                            </button>
                        </div>
                        <p style={{ fontSize:'0.8rem', color:'#6b7280', margin:'0 0 20px' }}>
                            El técnico que te asesora en los tratamientos. Lo guardas una vez y lo
                            eliges en cada tratamiento, sin volver a escribirlo. Exigido por la Orden APA/204/2023.
                        </p>
                        {asesores.length === 0 ? (
                            <div style={{ textAlign:'center', padding:'40px 0', color:'#9ca3af' }}>
                                <div style={{ fontSize:40, marginBottom:8 }}>🎓</div>
                                <p>Sin asesores registrados</p>
                            </div>
                        ) : asesores.map(as => (
                            <div key={as.id} className="card card-p" style={{ marginBottom:10, display:'flex', alignItems:'center', gap:12 }}>
                                <div style={{ flex:1 }}>
                                    <div style={{ fontWeight:700, color:'#111827' }}>{as.nombre}</div>
                                    <div style={{ fontSize:'0.78rem', color:'#6b7280', marginTop:3 }}>
                                        {[as.nif, as.num_ropo ? `ROPO: ${as.num_ropo}` : '', as.empresa]
                                            .filter(Boolean).join(' · ')}
                                    </div>
                                    {!(as.num_ropo || '').trim() && (
                                        <div style={{ fontSize:'0.75rem', color:'#92400e', marginTop:4 }}>
                                            ⚠️ Sin nº ROPO — puedes usarlo igualmente, pero añádelo cuando lo tengas
                                        </div>
                                    )}
                                </div>
                                <button onClick={() => { setEditingAs(as.id); setShowAsModal(true); }}
                                    style={{ background:'none', border:'none', cursor:'pointer', color:'#6b7280', fontSize:18 }}>✏️</button>
                                <button onClick={() => deleteAsesor(as.id)}
                                    style={{ background:'none', border:'none', cursor:'pointer', color:'#d1d5db', fontSize:18 }}
                                    onMouseEnter={e=>e.currentTarget.style.color='#ef4444'}
                                    onMouseLeave={e=>e.currentTarget.style.color='#d1d5db'}>🗑</button>
                            </div>
                        ))}
                    </div>
                )}

                {section === 'datos' && (
                    <div>
                        <h2 className="section-title" style={{ marginBottom: 20 }}>Datos y Exportación</h2>
                        <div className="card card-p" style={{ marginBottom:12 }}>
                            <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 8px' }}>📄 Exportar PDF oficial</h3>
                            <p style={{ fontSize:'0.82rem', color:'#6b7280', margin:'0 0 14px' }}>
                                Genera el Cuaderno de Explotación en formato PDF oficial (A4): portada, parcelas SIGPAC, tratamientos fitosanitarios, abono, labores y cosecha. Válido conforme a RD 1311/2012 Anexo III.
                            </p>
                            <button className="btn-primary" style={{ background:'linear-gradient(135deg,#1a4731,#00694c)' }}
                                onClick={() => window.open(`/api/export/pdf?campana=${encodeURIComponent(campana)}`)}>
                                ⬇ Descargar PDF (campaña {campana})
                            </button>
                        </div>
                        <div className="card card-p" style={{ marginBottom:12 }}>
                            <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 8px' }}>📊 Exportar cuaderno Excel</h3>
                            <p style={{ fontSize:'0.82rem', color:'#6b7280', margin:'0 0 14px' }}>
                                Genera un fichero .xlsx con 7 hojas: portada, parcelas, cultivos por campaña, tratamientos, abono, labores y cosecha.
                            </p>
                            <button className="btn-primary" onClick={() => window.open(`/api/export/excel?campana=${encodeURIComponent(campana)}`)}>
                                ⬇ Descargar Excel (campaña {campana})
                            </button>
                        </div>
                        {currentUser && currentUser.role === 'admin' && (
                        <div className="card card-p" style={{ marginBottom:12 }}>
                            <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 8px' }}>💾 Copia de seguridad (solo admin)</h3>
                            <p style={{ fontSize:'0.82rem', color:'#6b7280', margin:'0 0 14px' }}>
                                Descarga la base de datos completa (.db) para hacer una copia de seguridad.
                            </p>
                            <button className="btn-ghost" onClick={() => window.open('/api/backup/export')}>
                                ⬇ Descargar base de datos
                            </button>
                        </div>
                        )}
                        {currentUser && currentUser.role === 'admin' && (
                        <div className="card card-p">
                            <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 8px' }}>📥 Restaurar copia de seguridad (solo admin)</h3>
                            <p style={{ fontSize:'0.82rem', color:'#6b7280', margin:'0 0 14px' }}>
                                Sube una copia de seguridad (.db) para restaurar todos los datos. <strong>Atención:</strong> sobreescribirá los datos actuales.
                            </p>
                            <input type="file" accept=".db" style={{ fontSize:'0.85rem', color:'#374151' }}
                                onChange={async (e) => {
                                    const file = e.target.files[0];
                                    if (!file) return;
                                    if (!confirm('¿Restaurar la copia de seguridad? Se sobrescribirán TODOS los datos actuales.')) return;
                                    const fd = new FormData(); fd.append('file', file);
                                    await fetch('/api/backup/import', { method: 'POST', body: fd });
                                    showToast('Base de datos restaurada. Recargando…');
                                    setTimeout(() => window.location.reload(), 2000);
                                }} />
                        </div>
                        )}
                    </div>
                )}

                {section === 'cuenta' && (
                    <div>
                        <h2 className="section-title" style={{ marginBottom: 20 }}>Mi cuenta</h2>
                        {currentUser && (
                            <div className="card card-p" style={{ marginBottom:12 }}>
                                <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 12px' }}>👤 Datos de acceso</h3>
                                <div style={{ fontSize:'0.85rem', color:'#374151', lineHeight:2 }}>
                                    <div><strong>Email:</strong> {currentUser.email}</div>
                                    <div><strong>Nombre:</strong> {currentUser.nombre || '—'}</div>
                                    <div><strong>Rol:</strong> {currentUser.role === 'admin' ? '👑 Administrador' : '🌾 Agricultor'}</div>
                                </div>
                            </div>
                        )}
                        <ChangePwCard showToast={showToast} />
                        <div className="card card-p">
                            <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 8px' }}>🚪 Cerrar sesión</h3>
                            <p style={{ fontSize:'0.82rem', color:'#6b7280', margin:'0 0 14px' }}>
                                Cierra la sesión actual. Deberás iniciar sesión de nuevo para acceder al cuaderno.
                            </p>
                            <button className="btn-ghost" style={{ color:'var(--tertiary)', borderColor:'rgba(153,63,58,0.3)' }}
                                onClick={onLogout}>
                                🚪 Cerrar sesión
                            </button>
                        </div>
                    </div>
                )}

                {section === 'suscripcion' && !isAdmin && (
                    <div>
                        <h2 className="section-title" style={{ marginBottom: 20 }}>Suscripción</h2>
                        {currentUser && (
                            <div className="card card-p" style={{ marginBottom: 12 }}>
                                <h3 style={{ fontFamily: 'Manrope', fontWeight: 700, fontSize: '0.95rem', margin: '0 0 10px' }}>
                                    💳 Plan actual
                                </h3>
                                {currentUser.plan_active === false ? (
                                    <p style={{ fontSize: '0.85rem', color: '#991b1b', margin: '0 0 14px', fontWeight: 600 }}>
                                        ⏰ Tu período de prueba ha terminado. Suscríbete para seguir usando el cuaderno.
                                    </p>
                                ) : currentUser.plan === 'basic' || currentUser.plan === 'pro' ? (
                                    <p style={{ fontSize: '0.85rem', color: '#166534', margin: '0 0 14px', fontWeight: 600 }}>
                                        ✅ Plan {currentUser.plan === 'basic' ? 'Básico' : 'Pro'} activo.
                                    </p>
                                ) : (
                                    <p style={{ fontSize: '0.85rem', color: '#374151', margin: '0 0 14px' }}>
                                        Estás en el período de prueba gratuito.
                                    </p>
                                )}
                                <button
                                    className="btn-primary"
                                    style={{ background: 'linear-gradient(135deg, #00694c, #008560)' }}
                                    onClick={() => onNavigate && onNavigate('planes')}
                                >
                                    💳 Ver planes y suscripción →
                                </button>
                            </div>
                        )}
                    </div>
                )}

                {section === 'legal' && (
                    <div>
                        <h2 className="section-title" style={{ marginBottom: 20 }}>Legal y Privacidad</h2>
                        <div className="card card-p" style={{ marginBottom:12 }}>
                            <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 8px' }}>📄 Normativa aplicable</h3>
                            <ul style={{ fontSize:'0.85rem', color:'#374151', lineHeight:1.9, margin:0, paddingLeft:20 }}>
                                <li>Real Decreto 1311/2012 — Uso sostenible de productos fitosanitarios</li>
                                <li>Reglamento (UE) 2016/679 (RGPD)</li>
                                <li>Ley Orgánica 3/2018 (LOPDGDD)</li>
                                <li>Reglamento (UE) 2021/2115 — PAC 2023-2027</li>
                            </ul>
                        </div>
                        <div className="card card-p" style={{ marginBottom:12 }}>
                            <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 8px' }}>🔒 Protección de datos</h3>
                            <p style={{ fontSize:'0.84rem', color:'#374151', lineHeight:1.75, margin:'0 0 14px' }}>
                                Todos los datos se almacenan localmente en el servidor de esta aplicación. No se transmiten a terceros.
                                Puede restablecer su aceptación de la política de privacidad limpiando el almacenamiento local del navegador.
                            </p>
                            <button className="btn-ghost" onClick={() => {
                                if (!confirm('¿Restablecer la aceptación de privacidad? Volverás a ver la pantalla de bienvenida.')) return;
                                if (currentUser) localStorage.removeItem(`lopd_accepted_${currentUser.id}`);
                                window.location.reload();
                            }}>
                                Restablecer aceptación LOPD
                            </button>
                        </div>
                        <div className="card card-p">
                            <div style={{ fontSize:'0.8rem', color:'#9ca3af', lineHeight:1.7 }}>
                                <div><strong style={{ color:'#374151' }}>Cuaderno de Campo</strong> v2.0</div>
                                <div>Cumple con RD 1311/2012 · RGPD · LOPDGDD</div>
                            </div>
                        </div>
                    </div>
                )}

            </div>

            {showEqModal && (
                <EquipoModal
                    equipo={editingEq ? equipos.find(e => e.id === editingEq) : {}}
                    onSave={saveEquipo}
                    onClose={() => { setShowEqModal(false); setEditingEq(null); }}
                />
            )}

            {showApModal && (
                <AplicadorModal
                    aplicador={editingAp ? aplicadores.find(a => a.id === editingAp) : {}}
                    onSave={saveAplicador}
                    onClose={() => { setShowApModal(false); setEditingAp(null); }}
                />
            )}

            {showAsModal && (
                <AsesorModal
                    asesor={editingAs ? asesores.find(a => a.id === editingAs) : {}}
                    onSave={saveAsesor}
                    onClose={() => { setShowAsModal(false); setEditingAs(null); }}
                />
            )}

            {showQuickStart && (
                <QuickStartModal
                    onClose={() => setShowQuickStart(false)}
                    onNavigate={onNavigate}
                />
            )}
        </div>
    );
}

function ChangePwCard({ showToast }) {
    const { useState } = React;
    const [form, setForm]     = useState({ old_password:'', new_password:'', confirm:'' });
    const [error, setError]   = useState('');
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (form.new_password.length < 8) { setError('La nueva contraseña debe tener al menos 8 caracteres'); return; }
        if (form.new_password !== form.confirm) { setError('Las contraseñas no coinciden'); return; }
        setSaving(true);
        try {
            const res = await fetch('/api/auth/change-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_password: form.old_password, new_password: form.new_password }),
                credentials: 'include',
            });
            const data = await res.json();
            if (!res.ok) { setError(data.error || 'Error al cambiar contraseña'); }
            else {
                showToast('✅ Contraseña actualizada');
                setForm({ old_password:'', new_password:'', confirm:'' });
            }
        } catch { setError('Error de conexión'); }
        setSaving(false);
    };

    return (
        <div className="card card-p" style={{ marginBottom:12 }}>
            <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 14px' }}>🔑 Cambiar contraseña</h3>
            <form onSubmit={handleSubmit} style={{ display:'flex', flexDirection:'column', gap:10 }}>
                <div>
                    <label className="field-label">Contraseña actual</label>
                    <input className="input-field" type="password" placeholder="••••••••"
                        value={form.old_password} onChange={e => setForm(f => ({...f, old_password:e.target.value}))} />
                </div>
                <div>
                    <label className="field-label">Nueva contraseña</label>
                    <input className="input-field" type="password" placeholder="••••••••"
                        value={form.new_password} onChange={e => setForm(f => ({...f, new_password:e.target.value}))} />
                </div>
                <div>
                    <label className="field-label">Confirmar nueva contraseña</label>
                    <input className="input-field" type="password" placeholder="••••••••"
                        value={form.confirm} onChange={e => setForm(f => ({...f, confirm:e.target.value}))} />
                </div>
                {error && (
                    <div style={{ background:'rgba(153,63,58,0.10)', borderRadius:'var(--radius-lg)', padding:'10px 14px', fontSize:'0.82rem', color:'var(--tertiary)', fontWeight:600 }}>
                        ⚠️ {error}
                    </div>
                )}
                <button type="submit" className="btn-primary" disabled={saving}>
                    {saving ? 'Guardando…' : '✓ Cambiar contraseña'}
                </button>
            </form>
        </div>
    );
}
