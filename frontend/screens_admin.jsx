// ── Screen: Panel de Administración ──
function ScreenAdmin({ currentUser, onSwitchUser, showToast }) {
    const { useState, useEffect } = React;
    const [users, setUsers]       = useState([]);
    const [loading, setLoading]   = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm]         = useState({ email:'', nombre:'', password:'', role:'agricultor' });
    const [saving, setSaving]     = useState(false);
    const [formError, setFormError] = useState('');
    const [confirmDel, setConfirmDel] = useState(null); // user id a desactivar
    const [confirmReset, setConfirmReset] = useState(null); // user id a resetear cuaderno
    const [confirmPurge, setConfirmPurge] = useState(null); // user id a borrar permanentemente
    const [pdfCampana, setPdfCampana] = useState('2025/2026');

    const CAMPANAS = ['2023/2024', '2024/2025', '2025/2026', '2026/2027'];

    const handleExportPdf = (uid, nombre) => {
        const url = `/api/admin/users/${uid}/export/pdf?campana=${encodeURIComponent(pdfCampana)}`;
        const a = document.createElement('a');
        a.href = url;
        a.download = `cuaderno_${(nombre || 'agricultor').replace(/\s+/g,'_')}_${pdfCampana.replace('/','_')}.pdf`;
        a.click();
        showToast(`📄 Exportando PDF de ${nombre || 'agricultor'}…`);
    };

    const loadUsers = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/admin/users', { credentials:'include' });
            const data = await res.json();
            setUsers(Array.isArray(data) ? data : []);
        } catch { setUsers([]); }
        setLoading(false);
    };

    useEffect(() => { loadUsers(); }, []);

    const handleCreate = async (e) => {
        e.preventDefault();
        setFormError('');
        if (!form.email || !form.password) { setFormError('Email y contraseña son obligatorios'); return; }
        if (form.password.length < 6) { setFormError('La contraseña debe tener al menos 6 caracteres'); return; }
        setSaving(true);
        try {
            const res = await fetch('/api/admin/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(form),
                credentials: 'include',
            });
            const data = await res.json();
            if (!res.ok) { setFormError(data.error || 'Error al crear usuario'); }
            else {
                showToast('✅ Usuario creado correctamente');
                setShowForm(false);
                setForm({ email:'', nombre:'', password:'', role:'agricultor' });
                loadUsers();
            }
        } catch { setFormError('Error de conexión'); }
        setSaving(false);
    };

    const handleDeactivate = async (uid) => {
        try {
            await fetch(`/api/admin/users/${uid}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active: false }),
                credentials: 'include',
            });
            showToast('Usuario desactivado');
            setConfirmDel(null);
            loadUsers();
        } catch { showToast('Error al desactivar usuario'); }
    };

    const handleReactivate = async (uid) => {
        await fetch(`/api/admin/users/${uid}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ active: true }),
            credentials: 'include',
        });
        showToast('Usuario reactivado');
        loadUsers();
    };

    const handleToggleUnlimited = async (uid, nuevoValor) => {
        try {
            await fetch(`/api/admin/users/${uid}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ unlimited_explotaciones: nuevoValor }),
                credentials: 'include',
            });
            showToast(nuevoValor ? '⭐ Súper usuario: explotaciones ilimitadas' : 'Explotaciones limitadas al plan');
            loadUsers();
        } catch { showToast('Error al cambiar el permiso'); }
    };

    const handleChangePlan = async (uid, nuevoPlan) => {
        try {
            await fetch(`/api/admin/users/${uid}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plan: nuevoPlan }),
                credentials: 'include',
            });
            showToast(`Plan cambiado a ${nuevoPlan}`);
            loadUsers();
        } catch { showToast('Error al cambiar el plan'); }
    };

    const handlePurgeUser = async (uid, nombre) => {
        try {
            const res = await fetch(`/api/admin/users/${uid}/delete-permanent`, {
                method: 'DELETE', credentials: 'include',
            });
            const d = await res.json();
            if (d.ok) showToast(`🗑 Cuenta de ${nombre} eliminada`);
            else showToast('Error al eliminar la cuenta');
        } catch { showToast('Error de conexión'); }
        setConfirmPurge(null);
        loadUsers();
    };

    const handleResetCuaderno = async (uid, nombre) => {
        try {
            const res = await fetch(`/api/admin/users/${uid}/reset-cuaderno`, {
                method: 'POST', credentials: 'include',
            });
            const d = await res.json();
            if (d.ok) showToast(`✅ Cuaderno de ${nombre} borrado`);
            else showToast('Error al borrar el cuaderno');
        } catch { showToast('Error de conexión'); }
        setConfirmReset(null);
        loadUsers();
    };

    const handleSwitchUser = async (user) => {
        await fetch(`/api/admin/switch-user/${user.id}`, {
            method: 'POST', credentials: 'include',
        });
        onSwitchUser(user);
    };

    const ROLE_LABEL = { admin: '👑 Admin', agricultor: '🌾 Agricultor' };
    const ROLE_COLOR = { admin: '#78350f', agricultor: '#065f46' };
    const ROLE_BG    = { admin: 'rgba(120,53,15,0.10)', agricultor: 'rgba(6,95,70,0.10)' };

    const PLAN_CHIP = {
        premium: { bg:'#fef3c7', color:'#92400e', label:'🟠 PREMIUM' },
        pro:     { bg:'#ede9fe', color:'#5b21b6', label:'🟣 PRO' },
        basic:   { bg:'#dcfce7', color:'#065f46', label:'🟢 BÁSICO' },
        trial:   { bg:'#fef3c7', color:'#78350f', label:'🟡 PRUEBA' },
        expired: { bg:'var(--tertiary-fixed)', color:'var(--tertiary)', label:'🔴 CADUCADO' },
    };

    const formatFecha = (iso) => {
        if (!iso) return '';
        const d = new Date(iso.replace(' ', 'T'));
        if (isNaN(d.getTime())) return '';
        return d.toLocaleDateString('es-ES');
    };

    const renderPlanChip = (u) => {
        if (u.role === 'admin') return null;
        const style = PLAN_CHIP[u.plan_label] || PLAN_CHIP.expired;
        let suffix = '';
        if (u.plan_label === 'trial') {
            const f = formatFecha(u.trial_ends_at);
            if (f) suffix = ` · vence ${f}`;
        } else if (u.plan_label === 'expired') {
            const f = formatFecha(u.trial_ends_at);
            if (f) suffix = ` · caducó ${f}`;
        } else if (u.plan_label === 'basic' || u.plan_label === 'pro') {
            const f = formatFecha(u.subscription_ends_at);
            if (f) suffix = ` · renueva ${f}`;
        }
        return (
            <span style={{
                display:'inline-flex', alignItems:'center', gap:3,
                background: style.bg, color: style.color,
                borderRadius:'var(--radius-full)', padding:'2px 8px',
                fontSize:'0.65rem', fontWeight:700, letterSpacing:'0.04em',
            }}>
                {style.label}{suffix}
            </span>
        );
    };

    return (
        <div style={{ paddingBottom: 32 }}>
            {/* ── Header ── */}
            <div className="screen-header">
                <div style={{ display:'flex', alignItems:'center', gap: 12 }}>
                    <div style={{
                        width: 48, height: 48, borderRadius:'var(--radius-xl)',
                        background:'linear-gradient(135deg,#78350f,#b45309)',
                        display:'flex', alignItems:'center', justifyContent:'center',
                        fontSize: 24, flexShrink: 0,
                    }}>👥</div>
                    <div>
                        <h1 style={{ fontFamily:'var(--font-heading)', fontWeight:800, fontSize:'1.4rem', color:'#fff', margin:0, letterSpacing:'-0.02em' }}>
                            Panel de Admin
                        </h1>
                        <p style={{ color:'rgba(255,255,255,0.55)', fontSize:'0.8rem', margin:0 }}>
                            Gestión de usuarios y explotaciones
                        </p>
                    </div>
                </div>
            </div>

            <div style={{ padding: '20px 16px 0' }}>
                {/* ── Botón nuevo usuario ── */}
                <button
                    className="btn-primary"
                    style={{ width:'100%', marginBottom: 20, background:'linear-gradient(135deg,#78350f,#b45309)' }}
                    onClick={() => { setShowForm(true); setFormError(''); }}
                >
                    ➕  Crear nuevo usuario
                </button>

                {/* ── Formulario nuevo usuario ── */}
                {showForm && (
                    <div style={{
                        background:'var(--surface-container-lowest)',
                        borderRadius:'var(--radius-xl)',
                        padding: 20,
                        marginBottom: 20,
                        boxShadow:'var(--shadow-card)',
                    }}>
                        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: 16 }}>
                            <h3 style={{ fontFamily:'var(--font-heading)', fontWeight:700, fontSize:'1rem', margin:0 }}>
                                Nuevo usuario
                            </h3>
                            <button onClick={() => setShowForm(false)} style={{
                                background:'var(--surface-container-low)', border:'none',
                                borderRadius:'var(--radius-full)', width:32, height:32,
                                cursor:'pointer', color:'var(--on-surface-variant)', fontSize:16,
                                display:'flex', alignItems:'center', justifyContent:'center',
                            }}>✕</button>
                        </div>
                        <form onSubmit={handleCreate} style={{ display:'flex', flexDirection:'column', gap:12 }}>
                            <div>
                                <label className="field-label">Nombre</label>
                                <input className="input-field" type="text" placeholder="Juan García"
                                    value={form.nombre} onChange={e => setForm(f => ({...f, nombre: e.target.value}))} />
                            </div>
                            <div>
                                <label className="field-label">Email *</label>
                                <input className="input-field" type="email" placeholder="agricultor@email.es"
                                    value={form.email} onChange={e => setForm(f => ({...f, email: e.target.value}))} />
                            </div>
                            <div>
                                <label className="field-label">Contraseña * (mín. 6 caracteres)</label>
                                <input className="input-field" type="password" placeholder="••••••••"
                                    value={form.password} onChange={e => setForm(f => ({...f, password: e.target.value}))} />
                            </div>
                            <div>
                                <label className="field-label">Rol</label>
                                <select className="input-field" value={form.role}
                                    onChange={e => setForm(f => ({...f, role: e.target.value}))}>
                                    <option value="agricultor">🌾 Agricultor</option>
                                    <option value="admin">👑 Administrador</option>
                                </select>
                            </div>
                            {formError && (
                                <div style={{ background:'rgba(153,63,58,0.10)', border:'1px solid rgba(153,63,58,0.20)', borderRadius:'var(--radius-lg)', padding:'10px 14px', fontSize:'0.82rem', color:'var(--tertiary)', fontWeight:600 }}>
                                    ⚠️ {formError}
                                </div>
                            )}
                            <div style={{ display:'flex', gap:10, marginTop:4 }}>
                                <button type="submit" className="btn-primary" disabled={saving} style={{ flex:1 }}>
                                    {saving ? 'Guardando…' : '✓ Crear usuario'}
                                </button>
                                <button type="button" className="btn-ghost" onClick={() => setShowForm(false)} style={{ flex:1 }}>
                                    Cancelar
                                </button>
                            </div>
                        </form>
                    </div>
                )}

                {/* ── Selector campaña para exportaciones ── */}
                <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16, background:'var(--surface-container-lowest)', borderRadius:'var(--radius-lg)', padding:'10px 14px', boxShadow:'var(--shadow-card)' }}>
                    <span style={{ fontSize:'0.82rem', color:'var(--on-surface-variant)', fontWeight:600, whiteSpace:'nowrap' }}>📄 Campaña PDF:</span>
                    <select className="input-field" value={pdfCampana} onChange={e => setPdfCampana(e.target.value)} style={{ flex:1, margin:0 }}>
                        {CAMPANAS.map(c => <option key={c}>{c}</option>)}
                    </select>
                </div>

                {/* ── Lista usuarios ── */}
                <h2 className="section-title" style={{ marginBottom: 12 }}>
                    Usuarios ({users.length})
                </h2>

                {loading && (
                    <div style={{ textAlign:'center', padding:32, color:'var(--on-surface-variant)', fontSize:'0.9rem' }}>
                        Cargando…
                    </div>
                )}

                {!loading && users.map(u => (
                    <div key={u.id} style={{
                        background: u.active ? 'var(--surface-container-lowest)' : 'var(--surface-container-low)',
                        borderRadius:'var(--radius-xl)',
                        padding: '16px',
                        marginBottom: 10,
                        boxShadow:'var(--shadow-card)',
                        opacity: u.active ? 1 : 0.6,
                    }}>
                        {/* Fila superior */}
                        <div style={{ display:'flex', alignItems:'flex-start', gap:12, marginBottom:10 }}>
                            <div style={{
                                width:44, height:44, borderRadius:'var(--radius-lg)', flexShrink:0,
                                background: u.role === 'admin'
                                    ? 'linear-gradient(135deg,#78350f,#b45309)'
                                    : 'linear-gradient(135deg,var(--primary),var(--primary-container))',
                                display:'flex', alignItems:'center', justifyContent:'center',
                                fontSize:20, color:'#fff',
                            }}>
                                {u.role === 'admin' ? '👑' : '🌾'}
                            </div>
                            <div style={{ flex:1, minWidth:0 }}>
                                <div style={{ fontFamily:'var(--font-heading)', fontWeight:700, fontSize:'0.95rem', color:'var(--on-background)' }}>
                                    {u.nombre || '(sin nombre)'}
                                </div>
                                <div style={{ fontSize:'0.78rem', color:'var(--on-surface-variant)', marginTop:2, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                                    {u.email}
                                </div>
                                <div style={{ display:'flex', gap:6, marginTop:6, flexWrap:'wrap' }}>
                                    <span style={{
                                        display:'inline-flex', alignItems:'center', gap:3,
                                        background: ROLE_BG[u.role], color: ROLE_COLOR[u.role],
                                        borderRadius:'var(--radius-full)', padding:'2px 8px',
                                        fontSize:'0.65rem', fontWeight:700, letterSpacing:'0.04em',
                                    }}>
                                        {ROLE_LABEL[u.role] || u.role}
                                    </span>
                                    {renderPlanChip(u)}
                                    {!u.active && (
                                        <span className="chip chip-grey">INACTIVO</span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Stats */}
                        {u.active && u.stats && (
                            <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:8, marginBottom:12 }}>
                                {[
                                    { label:'Parcelas',   value: u.stats.parcelas, icon:'🗺️' },
                                    { label:'Tratamientos', value: u.stats.tratamientos, icon:'🌿' },
                                    { label:'Labores',    value: u.stats.labores, icon:'🚜' },
                                ].map(s => (
                                    <div key={s.label} style={{
                                        background:'var(--surface-container-low)',
                                        borderRadius:'var(--radius-lg)',
                                        padding:'8px 10px',
                                        textAlign:'center',
                                    }}>
                                        <div style={{ fontSize:14 }}>{s.icon}</div>
                                        <div style={{ fontFamily:'var(--font-heading)', fontWeight:800, fontSize:'1.1rem', color:'var(--on-background)', lineHeight:1 }}>
                                            {s.value}
                                        </div>
                                        <div style={{ fontSize:'0.6rem', color:'var(--on-surface-variant)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em', marginTop:2 }}>
                                            {s.label}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Acciones */}
                        {u.id !== currentUser.id && (
                            <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
                                {u.active && u.role !== 'admin' && (
                                    <button
                                        className="btn-primary"
                                        style={{ flex:1, minWidth:120, fontSize:'0.82rem', minHeight:40, padding:'10px 14px' }}
                                        onClick={() => handleSwitchUser(u)}
                                    >
                                        👁 Ver cuaderno
                                    </button>
                                )}
                                {u.active && u.role !== 'admin' && (
                                    <button
                                        className="btn-ghost"
                                        style={{ fontSize:'0.82rem', minHeight:40, padding:'10px 14px' }}
                                        onClick={() => handleExportPdf(u.id, u.nombre)}
                                    >
                                        📄 PDF
                                    </button>
                                )}
                                {u.active && u.role !== 'admin' && (
                                    <select
                                        value={u.plan || 'trial'}
                                        onChange={e => handleChangePlan(u.id, e.target.value)}
                                        title="Cambiar plan del usuario"
                                        style={{ fontSize:'0.82rem', minHeight:40, padding:'8px 12px',
                                            borderRadius:'var(--radius-lg)', border:'1px solid var(--outline-variant)',
                                            background:'var(--surface-container-lowest)', color:'var(--on-background)',
                                            fontFamily:'var(--font-body)', cursor:'pointer' }}
                                    >
                                        <option value="trial">🟡 Prueba</option>
                                        <option value="basic">🟢 Básico</option>
                                        <option value="pro">🟣 Pro</option>
                                        <option value="premium">🟠 Premium</option>
                                    </select>
                                )}
                                {u.active && u.role !== 'admin' && (
                                    <button
                                        className="btn-ghost"
                                        style={{ fontSize:'0.82rem', minHeight:40, padding:'10px 14px',
                                            color: u.unlimited_explotaciones ? '#b45309' : 'var(--on-surface-variant)',
                                            borderColor: u.unlimited_explotaciones ? 'rgba(180,83,9,0.4)' : undefined,
                                            fontWeight: u.unlimited_explotaciones ? 700 : 500 }}
                                        onClick={() => handleToggleUnlimited(u.id, u.unlimited_explotaciones ? 0 : 1)}
                                        title="Súper usuario: explotaciones ilimitadas (exento del tope del plan)"
                                    >
                                        {u.unlimited_explotaciones ? '⭐ Ilimitado' : '☆ Limitar expl.'}
                                    </button>
                                )}
                                {u.active && u.role !== 'admin' && (
                                    confirmReset === u.id ? (
                                        <>
                                            <button className="btn-ghost" style={{ flex:1, minWidth:100, fontSize:'0.82rem', minHeight:40, padding:'10px 14px', color:'#b45309', borderColor:'rgba(180,83,9,0.4)', fontWeight:700 }}
                                                onClick={() => handleResetCuaderno(u.id, u.nombre)}>
                                                ⚠️ Sí, borrar todo
                                            </button>
                                            <button className="btn-ghost" style={{ fontSize:'0.82rem', minHeight:40, padding:'10px 14px' }}
                                                onClick={() => setConfirmReset(null)}>
                                                Cancelar
                                            </button>
                                        </>
                                    ) : (
                                        <button className="btn-ghost" style={{ fontSize:'0.82rem', minHeight:40, padding:'10px 14px', color:'#b45309', borderColor:'rgba(180,83,9,0.3)' }}
                                            onClick={() => setConfirmReset(u.id)}>
                                            🗑 Vaciar cuaderno
                                        </button>
                                    )
                                )}
                                {u.active ? (
                                    confirmDel === u.id ? (
                                        <>
                                            <button className="btn-ghost" style={{ flex:1, minWidth:100, fontSize:'0.82rem', minHeight:40, padding:'10px 14px', color:'var(--tertiary)', borderColor:'rgba(153,63,58,0.3)' }}
                                                onClick={() => handleDeactivate(u.id)}>
                                                ✓ Confirmar
                                            </button>
                                            <button className="btn-ghost" style={{ fontSize:'0.82rem', minHeight:40, padding:'10px 14px' }}
                                                onClick={() => setConfirmDel(null)}>
                                                Cancelar
                                            </button>
                                        </>
                                    ) : (
                                        <button className="btn-ghost" style={{ fontSize:'0.82rem', minHeight:40, padding:'10px 14px', color:'var(--tertiary)', borderColor:'rgba(153,63,58,0.3)' }}
                                            onClick={() => setConfirmDel(u.id)}>
                                            🚫 Desactivar
                                        </button>
                                    )
                                ) : (
                                    <button className="btn-ghost" style={{ fontSize:'0.82rem', minHeight:40, padding:'10px 14px' }}
                                        onClick={() => handleReactivate(u.id)}>
                                        ✓ Reactivar
                                    </button>
                                )}
                                {u.role !== 'admin' && (
                                    confirmPurge === u.id ? (
                                        <>
                                            <button className="btn-ghost" style={{ flex:1, minWidth:120, fontSize:'0.82rem', minHeight:40, padding:'10px 14px', color:'#dc2626', borderColor:'rgba(220,38,38,0.4)', fontWeight:700 }}
                                                onClick={() => handlePurgeUser(u.id, u.nombre)}>
                                                ☠️ Eliminar cuenta
                                            </button>
                                            <button className="btn-ghost" style={{ fontSize:'0.82rem', minHeight:40, padding:'10px 14px' }}
                                                onClick={() => setConfirmPurge(null)}>
                                                Cancelar
                                            </button>
                                        </>
                                    ) : (
                                        <button className="btn-ghost" style={{ fontSize:'0.82rem', minHeight:40, padding:'10px 14px', color:'#dc2626', borderColor:'rgba(220,38,38,0.25)' }}
                                            onClick={() => setConfirmPurge(u.id)}>
                                            ☠️ Borrar cuenta
                                        </button>
                                    )
                                )}
                            </div>
                        )}
                        {u.id === currentUser.id && (
                            <div style={{ fontSize:'0.75rem', color:'var(--on-surface-variant)', fontStyle:'italic' }}>
                                Tu cuenta actual
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
