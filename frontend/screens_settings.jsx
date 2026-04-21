// ── Explotación modal (position:fixed → teclado Android funciona) ──
function ExplotacionModal({ data, onSave, onClose }) {
    const { useState } = React;
    const [form, setForm] = useState(data || {});
    const [saving, setSaving] = useState(false);
    const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

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

    return (
        <div className="overlay" onClick={onClose}>
            <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom: 40 }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                    <h3 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', margin:0 }}>🏡 Datos de la Explotación</h3>
                    <button onClick={onClose} style={{ background:'none', border:'none', fontSize:22, cursor:'pointer', color:'#6b7280' }}>✕</button>
                </div>
                {[
                    ['titular','Titular','text','Nombre completo'],
                    ['nif','NIF / CIF','text','12345678A'],
                    ['municipio','Municipio','text','Santa Cruz de Mudela'],
                    ['provincia','Provincia','text','Ciudad Real'],
                    ['cp','Código postal','text','13730'],
                    ['telefono','Teléfono','tel','600 000 000'],
                    ['email','Email','email','titular@explotacion.es'],
                    ['campana_activa','Campaña activa','text','2025/2026'],
                ].map(([k,l,t,ph]) => (
                    <div key={k} style={{ marginBottom:14 }}>
                        <label className="field-label">{l}</label>
                        <input type={t} className="input-field" value={form[k]||''} onChange={set(k)} placeholder={ph} />
                    </div>
                ))}
                <button className="btn-primary" style={{ width:'100%', marginTop:8 }} onClick={save} disabled={saving}>
                    {saving ? 'Guardando…' : '💾 Guardar datos'}
                </button>
            </div>
        </div>
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
    const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));
    return (
        <div className="overlay" onClick={onClose}>
            <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom: 40 }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                    <h3 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', margin:0 }}>
                        🚜 {equipo && equipo.id ? 'Editar equipo' : 'Nuevo equipo'}
                    </h3>
                    <button onClick={onClose} style={{ background:'none', border:'none', fontSize:22, cursor:'pointer', color:'#6b7280' }}>✕</button>
                </div>
                {[['descripcion','Descripción / nombre','text'],['tipo','Tipo','text'],['marca','Marca','text'],['modelo','Modelo','text'],['num_registro_roma','Nº Registro ROMA','text'],['fecha_iteaf','Fecha ITEAF','date']].map(([k,l,t]) => (
                    <div key={k} style={{ marginBottom:14 }}>
                        <label className="field-label">{l}</label>
                        <input type={t} className="input-field" value={form[k]||''} onChange={set(k)} />
                    </div>
                ))}
                <button className="btn-primary" style={{ width:'100%', marginTop:8 }} onClick={() => onSave(form)}>
                    {equipo && equipo.id ? 'Actualizar equipo' : 'Añadir equipo'}
                </button>
            </div>
        </div>
    );
}

// ── Aplicador form modal ──
function AplicadorModal({ aplicador, onSave, onClose }) {
    const { useState } = React;
    const [form, setForm] = useState(aplicador || {});
    const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));
    return (
        <div className="overlay" onClick={onClose}>
            <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom: 40 }}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                    <h3 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', margin:0 }}>
                        👤 {aplicador && aplicador.id ? 'Editar aplicador' : 'Nuevo aplicador'}
                    </h3>
                    <button onClick={onClose} style={{ background:'none', border:'none', fontSize:22, cursor:'pointer', color:'#6b7280' }}>✕</button>
                </div>
                {[['nombre','Nombre completo'],['nif','NIF'],['num_ropo','Nº ROPO']].map(([k,l]) => (
                    <div key={k} style={{ marginBottom:14 }}>
                        <label className="field-label">{l}</label>
                        <input className="input-field" value={form[k]||''} onChange={set(k)} />
                    </div>
                ))}
                <button className="btn-primary" style={{ width:'100%', marginTop:8 }} onClick={() => onSave(form)}>
                    {aplicador && aplicador.id ? 'Actualizar aplicador' : 'Añadir aplicador'}
                </button>
            </div>
        </div>
    );
}

// ── Screen: Ajustes / Más ──
function ScreenSettings({ campana, onCampana, showToast, currentUser, onLogout }) {
    const { useState, useEffect } = React;
    const [section, setSection] = useState('explotacion');
    const [equipos, setEquipos] = useState([]);
    const [aplicadores, setAplicadores] = useState([]);

    const [showEqModal, setShowEqModal]   = useState(false);
    const [showApModal, setShowApModal]   = useState(false);
    const [editingEq, setEditingEq] = useState(null);
    const [editingAp, setEditingAp] = useState(null);

    useEffect(() => {
        fetch('/api/equipos').then(r => r.json()).then(d => setEquipos(Array.isArray(d) ? d : []));
        fetch('/api/aplicadores').then(r => r.json()).then(d => setAplicadores(Array.isArray(d) ? d : []));
    }, []);

    const saveEquipo = async (form) => {
        const method = editingEq ? 'PUT' : 'POST';
        const url = editingEq ? `/api/equipos/${editingEq}` : '/api/equipos';
        await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(form) });
        showToast(editingEq ? 'Equipo actualizado' : 'Equipo añadido');
        fetch('/api/equipos').then(r => r.json()).then(d => setEquipos(Array.isArray(d) ? d : []));
        setShowEqModal(false); setEditingEq(null);
    };

    const deleteEquipo = async (id) => {
        if (!confirm('¿Eliminar este equipo?')) return;
        await fetch(`/api/equipos/${id}`, { method:'DELETE' });
        showToast('Equipo eliminado');
        setEquipos(e => e.filter(x => x.id !== id));
    };

    const saveAplicador = async (form) => {
        const method = editingAp ? 'PUT' : 'POST';
        const url = editingAp ? `/api/aplicadores/${editingAp}` : '/api/aplicadores';
        await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(form) });
        showToast(editingAp ? 'Aplicador actualizado' : 'Aplicador añadido');
        fetch('/api/aplicadores').then(r => r.json()).then(d => setAplicadores(Array.isArray(d) ? d : []));
        setShowApModal(false); setEditingAp(null);
    };

    const deleteAplicador = async (id) => {
        if (!confirm('¿Eliminar este aplicador?')) return;
        await fetch(`/api/aplicadores/${id}`, { method:'DELETE' });
        showToast('Aplicador eliminado');
        setAplicadores(a => a.filter(x => x.id !== id));
    };

    const SECTIONS = [
        { id: 'explotacion', icon: '🏡', label: 'Explotación' },
        { id: 'equipos',     icon: '🚜', label: 'Equipos' },
        { id: 'aplicadores', icon: '👤', label: 'Aplicadores' },
        { id: 'datos',       icon: '💾', label: 'Datos y exportación' },
        { id: 'cuenta',      icon: '🔑', label: 'Mi cuenta' },
        { id: 'legal',       icon: '📄', label: 'Legal y privacidad' },
    ];

    return (
        <div style={{ paddingBottom: 32 }}>
            <div style={{ background:'linear-gradient(135deg,#111827,#1f2937)', padding:'52px 20px 20px' }}>
                <h1 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.4rem', color:'#fff', margin:0 }}>
                    ⚙️ Ajustes
                </h1>
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
                        <div className="card card-p" style={{ marginBottom:12 }}>
                            <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 8px' }}>💾 Copia de seguridad</h3>
                            <p style={{ fontSize:'0.82rem', color:'#6b7280', margin:'0 0 14px' }}>
                                Descarga la base de datos completa (.db) para hacer una copia de seguridad.
                            </p>
                            <button className="btn-ghost" onClick={() => window.open('/api/backup/export')}>
                                ⬇ Descargar base de datos
                            </button>
                        </div>
                        <div className="card card-p">
                            <h3 style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.95rem', margin:'0 0 8px' }}>📥 Restaurar copia de seguridad</h3>
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
        if (form.new_password.length < 6) { setError('La nueva contraseña debe tener al menos 6 caracteres'); return; }
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
