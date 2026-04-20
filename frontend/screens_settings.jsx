// ── Screen: Ajustes / Más ──
function ScreenSettings({ campana, onCampana, showToast, currentUser, onLogout }) {
    const { useState, useEffect } = React;
    const [section, setSection] = useState('explotacion');
    const [explot, setExplot]   = useState({});
    const [equipos, setEquipos] = useState([]);
    const [aplicadores, setAplicadores] = useState([]);
    const [saving, setSaving]   = useState(false);

    // Equipo / Aplicador form visibility
    const [showEqForm, setShowEqForm]   = useState(false);
    const [showApForm, setShowApForm]   = useState(false);
    const [eqForm, setEqForm]   = useState({});
    const [apForm, setApForm]   = useState({});
    const [editingEq, setEditingEq] = useState(null);
    const [editingAp, setEditingAp] = useState(null);

    useEffect(() => {
        fetch('/api/explotacion').then(r => r.json()).then(d => setExplot(d || {}));
        fetch('/api/equipos').then(r => r.json()).then(d => setEquipos(Array.isArray(d) ? d : []));
        fetch('/api/aplicadores').then(r => r.json()).then(d => setAplicadores(Array.isArray(d) ? d : []));
    }, []);

    const saveExplot = async () => {
        setSaving(true);
        await fetch('/api/explotacion', { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(explot) });
        if (explot.campana_activa) onCampana(explot.campana_activa);
        showToast('Datos guardados correctamente');
        setSaving(false);
    };

    const saveEquipo = async () => {
        const method = editingEq ? 'PUT' : 'POST';
        const url = editingEq ? `/api/equipos/${editingEq}` : '/api/equipos';
        await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(eqForm) });
        showToast(editingEq ? 'Equipo actualizado' : 'Equipo añadido');
        fetch('/api/equipos').then(r => r.json()).then(d => setEquipos(Array.isArray(d) ? d : []));
        setShowEqForm(false); setEqForm({}); setEditingEq(null);
    };

    const deleteEquipo = async (id) => {
        if (!confirm('¿Eliminar este equipo?')) return;
        await fetch(`/api/equipos/${id}`, { method:'DELETE' });
        showToast('Equipo eliminado');
        setEquipos(e => e.filter(x => x.id !== id));
    };

    const saveAplicador = async () => {
        const method = editingAp ? 'PUT' : 'POST';
        const url = editingAp ? `/api/aplicadores/${editingAp}` : '/api/aplicadores';
        await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(apForm) });
        showToast(editingAp ? 'Aplicador actualizado' : 'Aplicador añadido');
        fetch('/api/aplicadores').then(r => r.json()).then(d => setAplicadores(Array.isArray(d) ? d : []));
        setShowApForm(false); setApForm({}); setEditingAp(null);
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

    const FieldRow = ({ label, children }) => (
        <div style={{ marginBottom: 16 }}>
            <label className="field-label">{label}</label>
            {children}
        </div>
    );

    const renderSection = () => {
        switch(section) {
            case 'explotacion': return (
                <div>
                    <h2 className="section-title" style={{ marginBottom: 20 }}>Datos de la Explotación</h2>
                    <div className="responsive-grid cols-2">
                        <FieldRow label="Titular">
                            <input className="input-field" value={explot.titular||''} onChange={e => setExplot(x => ({...x, titular:e.target.value}))} placeholder="Nombre completo" />
                        </FieldRow>
                        <FieldRow label="NIF / CIF">
                            <input className="input-field" value={explot.nif||''} onChange={e => setExplot(x => ({...x, nif:e.target.value}))} placeholder="12345678A" />
                        </FieldRow>
                        <FieldRow label="Municipio">
                            <input className="input-field" value={explot.municipio||''} onChange={e => setExplot(x => ({...x, municipio:e.target.value}))} placeholder="Santa Cruz de Mudela" />
                        </FieldRow>
                        <FieldRow label="Provincia">
                            <input className="input-field" value={explot.provincia||''} onChange={e => setExplot(x => ({...x, provincia:e.target.value}))} placeholder="Ciudad Real" />
                        </FieldRow>
                        <FieldRow label="Código postal">
                            <input className="input-field" value={explot.cp||''} onChange={e => setExplot(x => ({...x, cp:e.target.value}))} placeholder="13730" />
                        </FieldRow>
                        <FieldRow label="Teléfono">
                            <input className="input-field" type="tel" value={explot.telefono||''} onChange={e => setExplot(x => ({...x, telefono:e.target.value}))} placeholder="600 000 000" />
                        </FieldRow>
                        <FieldRow label="Email">
                            <input className="input-field" type="email" value={explot.email||''} onChange={e => setExplot(x => ({...x, email:e.target.value}))} placeholder="titular@explotacion.es" />
                        </FieldRow>
                        <FieldRow label="Campaña activa">
                            <input className="input-field" value={explot.campana_activa||''} onChange={e => setExplot(x => ({...x, campana_activa:e.target.value}))} placeholder="2025/2026" />
                        </FieldRow>
                    </div>
                    <button className="btn-primary" onClick={saveExplot} disabled={saving} style={{ marginTop: 8 }}>
                        {saving ? 'Guardando…' : '💾 Guardar datos'}
                    </button>
                </div>
            );

            case 'equipos': return (
                <div>
                    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                        <h2 className="section-title" style={{ margin:0 }}>Equipos de Aplicación</h2>
                        <button className="btn-primary" style={{ padding:'10px 16px', fontSize:'0.85rem' }}
                            onClick={() => { setEqForm({}); setEditingEq(null); setShowEqForm(true); }}>
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
                            <button onClick={() => { setEqForm({...eq}); setEditingEq(eq.id); setShowEqForm(true); }}
                                style={{ background:'none', border:'none', cursor:'pointer', color:'#6b7280', fontSize:18 }}>✏️</button>
                            <button onClick={() => deleteEquipo(eq.id)}
                                style={{ background:'none', border:'none', cursor:'pointer', color:'#d1d5db', fontSize:18 }}
                                onMouseEnter={e=>e.currentTarget.style.color='#ef4444'}
                                onMouseLeave={e=>e.currentTarget.style.color='#d1d5db'}>🗑</button>
                        </div>
                    ))}
                </div>
            );

            case 'aplicadores': return (
                <div>
                    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                        <h2 className="section-title" style={{ margin:0 }}>Aplicadores ROPO</h2>
                        <button className="btn-primary" style={{ padding:'10px 16px', fontSize:'0.85rem' }}
                            onClick={() => { setApForm({}); setEditingAp(null); setShowApForm(true); }}>
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
                            <button onClick={() => { setApForm({...ap}); setEditingAp(ap.id); setShowApForm(true); }}
                                style={{ background:'none', border:'none', cursor:'pointer', color:'#6b7280', fontSize:18 }}>✏️</button>
                            <button onClick={() => deleteAplicador(ap.id)}
                                style={{ background:'none', border:'none', cursor:'pointer', color:'#d1d5db', fontSize:18 }}
                                onMouseEnter={e=>e.currentTarget.style.color='#ef4444'}
                                onMouseLeave={e=>e.currentTarget.style.color='#d1d5db'}>🗑</button>
                        </div>
                    ))}
                </div>
            );

            case 'datos': return (
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
            );

            case 'cuenta': return (
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
            );

            case 'legal': return (
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
            );
            default: return null;
        }
    };

    return (
        <div style={{ paddingBottom: 32 }}>
            <div style={{ background:'linear-gradient(135deg,#111827,#1f2937)', padding:'52px 20px 20px' }}>
                <h1 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.4rem', color:'#fff', margin:0 }}>
                    ⚙️ Ajustes
                </h1>
            </div>

            {/* Section tabs */}
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
                {renderSection()}
            </div>

            {/* Equipo form modal */}
            {showEqForm && (
                <div className="overlay" onClick={() => setShowEqForm(false)}>
                    <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom:40 }}>
                        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                            <h3 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', margin:0 }}>
                                🚜 {editingEq ? 'Editar equipo' : 'Nuevo equipo'}
                            </h3>
                            <button onClick={() => setShowEqForm(false)} style={{ background:'none', border:'none', fontSize:22, cursor:'pointer', color:'#6b7280' }}>✕</button>
                        </div>
                        {[['descripcion','Descripción / nombre','text'],['tipo','Tipo','text'],['marca','Marca','text'],['modelo','Modelo','text'],['num_registro_roma','Nº Registro ROMA','text'],['fecha_iteaf','Fecha ITEAF','date']].map(([k,l,t]) => (
                            <div key={k} style={{ marginBottom:14 }}>
                                <label className="field-label">{l}</label>
                                <input type={t} className="input-field" value={eqForm[k]||''} onChange={e => setEqForm(f => ({...f,[k]:e.target.value}))} />
                            </div>
                        ))}
                        <button className="btn-primary" style={{ width:'100%', marginTop:8 }} onClick={saveEquipo}>
                            {editingEq ? 'Actualizar equipo' : 'Añadir equipo'}
                        </button>
                    </div>
                </div>
            )}

            {/* Aplicador form modal */}
            {showApForm && (
                <div className="overlay" onClick={() => setShowApForm(false)}>
                    <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom:40 }}>
                        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
                            <h3 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', margin:0 }}>
                                👤 {editingAp ? 'Editar aplicador' : 'Nuevo aplicador'}
                            </h3>
                            <button onClick={() => setShowApForm(false)} style={{ background:'none', border:'none', fontSize:22, cursor:'pointer', color:'#6b7280' }}>✕</button>
                        </div>
                        {[['nombre','Nombre completo'],['nif','NIF'],['num_ropo','Nº ROPO']].map(([k,l]) => (
                            <div key={k} style={{ marginBottom:14 }}>
                                <label className="field-label">{l}</label>
                                <input className="input-field" value={apForm[k]||''} onChange={e => setApForm(f => ({...f,[k]:e.target.value}))} />
                            </div>
                        ))}
                        <button className="btn-primary" style={{ width:'100%', marginTop:8 }} onClick={saveAplicador}>
                            {editingAp ? 'Actualizar aplicador' : 'Añadir aplicador'}
                        </button>
                    </div>
                </div>
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
