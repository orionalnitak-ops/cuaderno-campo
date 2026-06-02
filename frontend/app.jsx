// ── App Shell: Auth gate + responsive nav + routing ──
const { useState, useEffect, useCallback } = React;

const NAV_ITEMS = [
    { id: 'inicio',    icon: '🏡', label: 'Inicio' },
    { id: 'parcelas',  icon: '🗺️', label: 'Parcelas' },
    { id: '_fab',      icon: '✏️',  label: 'Anotar', fab: true },
    { id: 'historial', icon: '📋', label: 'Historial' },
    { id: 'mas',       icon: '⚙️', label: 'Ajustes' },
];

const MODULE_CARDS = [
    { id: 'tratamiento',   icon: '🌿', title: 'Tratamiento fitosanitario', desc: 'Registro de aplicaciones contra plagas y enfermedades.', bg: 'linear-gradient(135deg, #00694c, #008560)' },
    { id: 'fertilizacion', icon: '🌱', title: 'Abono', desc: 'Abonado de fondo, cobertera o fertirrigación foliar.', bg: 'linear-gradient(135deg, #3730a3, #4f46e5)' },
    { id: 'labor',         icon: '🚜', title: 'Labor agrícola', desc: 'Siembra, riego, poda, laboreo de suelos y otras tareas.', bg: 'linear-gradient(135deg, #1e3a5f, #1d4ed8)' },
    { id: 'cosecha',       icon: '📦', title: 'Cosecha', desc: 'Recolección de producto, pesaje y control de lotes.', bg: 'linear-gradient(135deg, #9f1239, #db2777)' },
    { id: 'compra',        icon: '🛒', title: 'Compras', desc: 'Registro de compras de fitosanitarios, fertilizantes y semillas.', bg: 'linear-gradient(135deg, #78350f, #b45309)' },
];

function App() {
    // ── Auth state ──
    const [authState, setAuthState]   = useState('loading'); // loading | guest | authenticated
    const [currentUser, setCurrentUser] = useState(null);     // {id, email, nombre, role, impersonating}

    // ── App state ──
    const [screen, setScreen]           = useState('inicio');
    const [homeKey, setHomeKey]         = useState(0);
    const [historialKey, setHistorialKey] = useState(0);
    const [lopdOk, setLopdOk]           = useState(false);
    const [showModules, setShowModules] = useState(false);
    const [activeForm, setActiveForm]   = useState(null);
    const [toast, setToast]             = useState({ msg: '', on: false });
    const [campana, setCampana]         = useState('2025/2026');
    const [installPrompt, setInstallPrompt] = useState(null);
    const [showInstallBanner, setShowInstallBanner] = useState(false);

    // ── Boot: check session ──
    useEffect(() => {
        const isPagoCompletado = window.location.pathname.includes('pago-completado');
        fetch('/api/auth/me', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data && data.id) {
                    setCurrentUser(data);
                    setAuthState('authenticated');
                    const key = `lopd_accepted_${data.id}`;
                    setLopdOk(!!localStorage.getItem(key));
                    if (isPagoCompletado) {
                        window.history.replaceState({}, '', '/');
                        setTimeout(() => showMsg('¡Pago completado! Tu suscripción se activará en unos momentos.'), 500);
                    }
                } else {
                    setAuthState('guest');
                }
            })
            .catch(() => setAuthState('guest'));
    }, []);

    // Load campaign on auth
    useEffect(() => {
        if (authState !== 'authenticated') return;
        fetch('/api/explotacion', { credentials: 'include' })
            .then(r => r.ok ? r.json() : {})
            .then(d => { if (d && d.campana_activa) setCampana(d.campana_activa); })
            .catch(() => {});
    }, [authState]);

    // PWA install prompt
    useEffect(() => {
        // No mostrar si ya está instalada como PWA
        if (window.matchMedia('(display-mode: standalone)').matches) return;
        // No mostrar si el usuario ya la descartó
        if (localStorage.getItem('pwa_dismissed')) return;

        const isIos = /iPhone|iPad|iPod/i.test(navigator.userAgent);
        const isMobile = window.innerWidth < 1024;

        if (isIos && isMobile) {
            // iOS no dispara beforeinstallprompt — mostramos guía manual
            setShowInstallBanner('ios');
            return;
        }

        const handler = (e) => {
            e.preventDefault();
            setInstallPrompt(e);
            if (isMobile) setShowInstallBanner('android');
        };
        window.addEventListener('beforeinstallprompt', handler);
        return () => window.removeEventListener('beforeinstallprompt', handler);
    }, []);

    const handleLogin = useCallback((userData) => {
        setCurrentUser(userData);
        setAuthState('authenticated');
        const key = `lopd_accepted_${userData.id}`;
        setLopdOk(!!localStorage.getItem(key));
    }, []);

    const handleLogout = useCallback(async () => {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
        setCurrentUser(null);
        setAuthState('guest');
        setScreen('inicio');
        setLopdOk(false);
    }, []);

    const handleSwitchBack = useCallback(async () => {
        await fetch('/api/admin/switch-back', { method: 'POST', credentials: 'include' });
        setCurrentUser(u => ({ ...u, impersonating: null }));
        setScreen('admin');
    }, []);

    const handleSwitchUser = useCallback((targetUser) => {
        setCurrentUser(u => ({ ...u, impersonating: { id: targetUser.id, email: targetUser.email, nombre: targetUser.nombre } }));
        setScreen('inicio');
    }, []);

    const showMsg = useCallback((msg) => {
        setToast({ msg, on: true });
        setTimeout(() => setToast(t => ({ ...t, on: false })), 3000);
    }, []);

    const openForm = (modulo, record = null) => {
        setActiveForm({ modulo, record });
        setShowModules(false);
    };
    const closeForm = (msg) => {
        setActiveForm(null);
        if (msg) { showMsg(msg); setHistorialKey(k => k + 1); }
    };

    const navigate = (id) => {
        if (id === '_fab') { setShowModules(s => !s); return; }
        if (id === 'inicio') setHomeKey(k => k + 1);
        setScreen(id);
        setShowModules(false);
    };

    // ── Loading ──
    if (authState === 'loading') {
        return (
            <div style={{ minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center', background:'var(--surface)' }}>
                <div style={{ textAlign:'center' }}>
                    <div style={{ fontSize:48, marginBottom:16 }}>🌿</div>
                    <p style={{ color:'var(--on-surface-variant)', fontSize:'0.9rem', fontFamily:'var(--font-body)' }}>Cargando…</p>
                </div>
            </div>
        );
    }

    // ── Login gate ──
    if (authState === 'guest') {
        return <ScreenLogin onLogin={handleLogin} />;
    }

    // ── LOPD gate (per user, after login) ──
    if (!lopdOk) {
        return (
            <ScreenLopd onAccept={() => {
                const key = `lopd_accepted_${currentUser.id}`;
                localStorage.setItem(key, '1');
                setLopdOk(true);
            }} />
        );
    }

    // ── Active form ──
    if (activeForm) {
        return (
            <div style={{ minHeight: '100vh', background: '#f8f9fb' }}>
                <ScreenForms
                    modulo={activeForm.modulo}
                    record={activeForm.record}
                    campana={campana}
                    onClose={closeForm}
                />
                <Toast toast={toast} />
            </div>
        );
    }

    const isAdmin = currentUser?.role === 'admin';
    const isImpersonating = !!currentUser?.impersonating;
    const planExpired = !isAdmin && currentUser?.plan_active === false;
    const isTrialActive = !isAdmin && currentUser?.plan_raw === 'trial' && currentUser?.plan_active === true;
    const trialDaysLeft = isTrialActive && currentUser?.trial_ends_at
        ? Math.max(0, Math.ceil((new Date(currentUser.trial_ends_at) - new Date()) / 86400000))
        : 0;

    const renderScreen = () => {
        switch (screen) {
            case 'inicio':    return <ScreenHome key={homeKey} campana={campana} onOpenForm={openForm} showToast={showMsg} onNavigate={navigate} />;
            case 'parcelas':  return <ScreenParcelas campana={campana} showToast={showMsg} />;
            case 'historial': return <ScreenHistorial key={historialKey} campana={campana} onEdit={openForm} showToast={showMsg} />;
            case 'mas':       return <ScreenSettings  campana={campana} onCampana={setCampana} showToast={showMsg} currentUser={currentUser} onLogout={handleLogout} onNavigate={navigate} />;
            case 'admin':     return isAdmin ? <ScreenAdmin currentUser={currentUser} onSwitchUser={handleSwitchUser} showToast={showMsg} /> : <ScreenHome campana={campana} onOpenForm={openForm} showToast={showMsg} />;
            case 'planes':    return <ScreenPlanes currentUser={currentUser} showToast={showMsg} onClose={() => navigate('inicio')} />;
            default:          return <ScreenHome     campana={campana} onOpenForm={openForm} showToast={showMsg} />;
        }
    };

    // Sidebar items (admin gets extra item)
    const sidebarItems = [
        { id: 'inicio',    icon: '🏡', label: 'Inicio' },
        { id: 'parcelas',  icon: '🗺️', label: 'Mis parcelas' },
        { id: 'historial', icon: '📋', label: 'Historial' },
        { id: 'mas',       icon: '⚙️', label: 'Ajustes' },
        ...(isAdmin ? [{ id: 'admin', icon: '👥', label: 'Panel Admin' }] : [{ id: 'planes', icon: '💳', label: 'Suscripción' }]),
    ];

    // Bottom nav items (admin replaces last item)
    const bottomNavItems = [
        { id: 'inicio',    icon: '🏡', label: 'Inicio' },
        { id: 'parcelas',  icon: '🗺️', label: 'Parcelas' },
        { id: '_fab',      icon: '✏️',  label: 'Anotar', fab: true },
        { id: 'historial', icon: '📋', label: 'Historial' },
        isAdmin
            ? { id: 'admin', icon: '👥', label: 'Admin' }
            : { id: 'mas',   icon: '⚙️', label: 'Ajustes' },
    ];

    return (
        <div style={{ display: 'flex', minHeight: '100vh', background: '#f8f9fb' }}>

            {/* ── Trial caducado / suscripción requerida ── */}
            {planExpired && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, zIndex: 201,
                    background: 'linear-gradient(135deg, #7f1d1d, #dc2626)',
                    color: '#fff', padding: '10px 20px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    gap: 12, fontSize: '0.82rem', fontWeight: 600,
                }}>
                    <span>⏰ Tu período de prueba ha terminado. Solo puedes consultar tus datos.</span>
                    <button onClick={() => navigate('planes')} style={{
                        background: 'rgba(255,255,255,0.20)', border: 'none',
                        borderRadius: 'var(--radius-full)', padding: '6px 14px',
                        color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: '0.78rem',
                        whiteSpace: 'nowrap',
                    }}>
                        Ver planes →
                    </button>
                </div>
            )}

            {/* ── Impersonation banner ── */}
            {isImpersonating && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, zIndex: 200,
                    background: 'linear-gradient(135deg, #78350f, #b45309)',
                    color: '#fff', padding: '10px 20px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    gap: 12, fontSize: '0.82rem', fontWeight: 600,
                }}>
                    <span>👁 Viendo datos de: <strong>{currentUser.impersonating.nombre || currentUser.impersonating.email}</strong></span>
                    <button onClick={handleSwitchBack} style={{
                        background: 'rgba(255,255,255,0.20)', border: 'none',
                        borderRadius: 'var(--radius-full)', padding: '6px 14px',
                        color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: '0.78rem',
                    }}>
                        ← Volver al panel
                    </button>
                </div>
            )}

            {/* ── Desktop Sidebar ── */}
            <nav id="sidebar" style={(isImpersonating || planExpired) ? { paddingTop: 40 } : {}}>
                <div className="sidebar-logo">
                    <div className="logo-icon">🌿</div>
                    <span className="logo-text">Cuaderno de Campo</span>
                </div>
                <div style={{ padding: '8px 0', flex: 1, overflowY: 'auto' }}>
                    <button className="sidebar-new-btn" onClick={() => setShowModules(true)}>
                        <span className="nav-icon">✏️</span>
                        <span className="nav-label">Anotar actividad</span>
                    </button>
                    {sidebarItems.map(item => (
                        <button key={item.id}
                            className={`sidebar-nav-item ${screen === item.id ? 'active' : ''}`}
                            onClick={() => navigate(item.id)}>
                            <span className="nav-icon">{item.icon}</span>
                            <span className="nav-label">{item.label}</span>
                        </button>
                    ))}
                </div>

                {/* Trial countdown notice */}
                {isTrialActive && (
                    <div style={{ padding: '0 8px 8px' }}>
                        <div style={{
                            background: 'linear-gradient(135deg, #78350f, #b45309)',
                            borderRadius: 'var(--radius-lg)',
                            padding: '10px 12px',
                            cursor: 'pointer',
                        }} onClick={() => navigate('planes')}>
                            <div style={{ fontSize: '0.65rem', color: 'rgba(255,220,100,0.9)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3 }}>
                                ⏳ Período de prueba
                            </div>
                            <div style={{ fontSize: '0.82rem', color: '#fff', fontWeight: 600, marginBottom: 8 }}>
                                {trialDaysLeft <= 1
                                    ? 'Último día de prueba'
                                    : `${trialDaysLeft} días restantes`}
                            </div>
                            <button onClick={(e) => { e.stopPropagation(); navigate('planes'); }} style={{
                                width: '100%',
                                background: '#f59e0b',
                                border: 'none',
                                borderRadius: 'var(--radius-md)',
                                padding: '7px 0',
                                color: '#fff',
                                fontWeight: 700,
                                fontSize: '0.78rem',
                                cursor: 'pointer',
                                fontFamily: 'var(--font-body)',
                            }}>
                                Suscribirse →
                            </button>
                        </div>
                    </div>
                )}

                {/* User info + logout */}
                <div style={{ padding: '12px 8px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                    <div style={{ padding: '8px 10px', marginBottom: 4 }}>
                        <div style={{ fontSize:'0.72rem', fontWeight:700, color:'var(--primary-fixed-dim)', textTransform:'uppercase', letterSpacing:'0.06em' }}>
                            {currentUser.nombre || currentUser.email}
                        </div>
                        <div style={{ fontSize:'0.65rem', color:'rgba(255,255,255,0.30)', marginTop:2 }}>
                            {isAdmin ? '👑 Administrador' : '🌾 Agricultor'}
                        </div>
                    </div>
                    <button onClick={handleLogout} style={{
                        display:'flex', alignItems:'center', gap:8,
                        width:'100%', padding:'10px 12px',
                        background:'rgba(255,255,255,0.06)', border:'none',
                        borderRadius:'var(--radius-lg)', cursor:'pointer',
                        color:'rgba(255,255,255,0.50)', fontSize:'0.82rem',
                        fontFamily:'var(--font-body)', fontWeight:500,
                        transition:'all 0.15s',
                    }}>
                        <span>🚪</span>
                        <span>Cerrar sesión</span>
                    </button>
                    <div style={{ padding: '8px 10px 0' }}>
                        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.2)' }}>
                            v2.0 · RD 1311/2012
                        </span>
                    </div>
                </div>
            </nav>

            {/* ── Right: TopBar + Screen ── */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, ...((isImpersonating || planExpired) ? { marginTop: 38 } : {}) }}>

                {/* Desktop Top Bar */}
                <header id="topbar">
                    <span className="tb-title">📋 Cuaderno de Campo</span>
                    <span className="tb-spacer" />
                    <span className="tb-campaign">Campaña {campana}</span>
                    <button className="tb-export-btn"
                        onClick={() => window.open(`/api/export/pdf?campana=${encodeURIComponent(campana)}`)}>
                        ⬇ PDF oficial
                    </button>
                    <button className="tb-export-btn"
                        onClick={() => window.open(`/api/export/excel?campana=${encodeURIComponent(campana)}`)}>
                        ⬇ Exportar Excel
                    </button>
                    {/* User badge */}
                    <div style={{
                        display:'flex', alignItems:'center', gap:8,
                        background:'var(--surface-container-low)',
                        borderRadius:'var(--radius-full)', padding:'6px 14px 6px 8px',
                        fontSize:'0.78rem', fontWeight:600, color:'var(--on-surface-variant)',
                    }}>
                        <div style={{
                            width:26, height:26, borderRadius:'var(--radius-full)',
                            background: isAdmin ? 'linear-gradient(135deg,#78350f,#b45309)' : 'linear-gradient(135deg,var(--primary),var(--primary-container))',
                            display:'flex', alignItems:'center', justifyContent:'center',
                            fontSize:13, color:'#fff',
                        }}>{isAdmin ? '👑' : '🌾'}</div>
                        {currentUser.nombre || currentUser.email}
                    </div>
                    <button onClick={handleLogout} style={{
                        background:'none', border:'1.5px solid rgba(109,122,115,0.25)',
                        borderRadius:'var(--radius-full)', padding:'6px 14px',
                        fontSize:'0.78rem', fontWeight:600, color:'var(--on-surface-variant)',
                        cursor:'pointer', fontFamily:'var(--font-body)',
                        transition:'all 0.15s',
                    }}>
                        🚪 Salir
                    </button>
                </header>

                {/* Screen content */}
                <main id="main-content" className={isTrialActive ? 'with-trial-strip' : ''}>
                    {renderScreen()}
                </main>
            </div>

            {/* ── Mobile trial strip (above bottom nav) ── */}
            {isTrialActive && (
                <div className="trial-strip-mobile" style={{
                    position: 'fixed', bottom: 'var(--nav-h)', left: 0, right: 0,
                    zIndex: 39,
                    background: 'linear-gradient(90deg, #92400e, #b45309)',
                    color: '#fff',
                    padding: '7px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 10,
                    fontSize: '0.78rem',
                    fontFamily: 'var(--font-body)',
                    boxShadow: '0 -2px 10px rgba(0,0,0,0.2)',
                }}>
                    <span style={{ fontWeight: 500 }}>
                        ⏳ {trialDaysLeft <= 1 ? 'Último día de prueba' : `${trialDaysLeft} días de prueba restantes`}
                    </span>
                    <button onClick={() => navigate('planes')} style={{
                        background: '#f59e0b',
                        border: 'none',
                        borderRadius: 'var(--radius-full)',
                        padding: '5px 13px',
                        color: '#fff',
                        fontWeight: 700,
                        cursor: 'pointer',
                        fontSize: '0.74rem',
                        fontFamily: 'var(--font-body)',
                        whiteSpace: 'nowrap',
                    }}>
                        Suscribirse
                    </button>
                </div>
            )}

            {/* ── Mobile / Tablet Bottom Nav ── */}
            <nav id="bottom-nav">
                {bottomNavItems.map(item => {
                    if (item.fab) {
                        return (
                            <button key="fab" className={`fab-center ${showModules ? 'open' : ''}`}
                                onClick={() => navigate('_fab')}
                                style={{ fontSize: 28, lineHeight: 1 }}>
                                {showModules ? '✕' : '✏️'}
                            </button>
                        );
                    }
                    return (
                        <button key={item.id}
                            className={`nav-tab ${screen === item.id ? 'active' : ''}`}
                            onClick={() => navigate(item.id)}>
                            <span className="tab-icon">{item.icon}</span>
                            <span className="tab-label">{item.label}</span>
                        </button>
                    );
                })}
            </nav>

            {/* ── Module Selector Overlay ── */}
            {showModules && (
                <div className="overlay" onClick={() => setShowModules(false)}>
                    <div className="module-sheet" style={{ paddingBottom: 0, overflow: 'hidden' }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6, padding: '4px 0 0' }}>
                            <div>
                                <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.35rem', margin: '0 0 2px', color: 'var(--on-background)', letterSpacing: '-0.02em' }}>
                                    Nuevo Registro
                                </h2>
                                <p style={{ color: 'var(--on-surface-variant)', fontSize: '0.83rem', margin: 0, lineHeight: 1.4 }}>
                                    Seleccione el tipo de actividad realizada en su explotación.
                                </p>
                            </div>
                            <button onClick={() => setShowModules(false)} style={{
                                background: 'var(--surface-container-low)', border: 'none',
                                borderRadius: 'var(--radius-full)', width: 36, height: 36,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                cursor: 'pointer', color: 'var(--on-surface-variant)', fontSize: 18, flexShrink: 0,
                            }}>✕</button>
                        </div>

                        <div className="module-grid" style={{ marginBottom: 0 }}>
                            {MODULE_CARDS.map(m => (
                                <button key={m.id} className="module-card"
                                    style={{ background: m.bg }}
                                    onClick={() => openForm(m.id)}>
                                    <span className="mc-icon">{m.icon}</span>
                                    <span className="mc-title">{m.title}</span>
                                    <span className="mc-desc">{m.desc}</span>
                                </button>
                            ))}
                        </div>

                        <div style={{
                            background: 'linear-gradient(160deg, #1a4731 0%, var(--primary) 100%)',
                            marginTop: 14, marginLeft: -16, marginRight: -16,
                            padding: '18px 20px 22px', position: 'relative', overflow: 'hidden',
                        }}>
                            <div style={{ position: 'absolute', inset: 0, background: 'repeating-linear-gradient(135deg, rgba(255,255,255,0) 0px, rgba(255,255,255,0) 15px, rgba(255,255,255,0.02) 15px, rgba(255,255,255,0.02) 16px)' }} />
                            <div style={{ position: 'relative' }}>
                                <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--primary-fixed-dim)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                                    Campaña {campana || '2025/2026'}
                                </div>
                                <p style={{ fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '0.88rem', color: 'rgba(255,255,255,0.85)', margin: 0, lineHeight: 1.5, fontStyle: 'italic' }}>
                                    "La mejor fertilización es la sombra del dueño en el campo."
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ── PWA Install Banner ── */}
            {showInstallBanner && (
                <div style={{
                    position: 'fixed', bottom: 84, left: 8, right: 8,
                    background: '#111827', borderRadius: 16,
                    padding: '14px 16px', zIndex: 250,
                    display: 'flex', alignItems: 'center', gap: 12,
                    boxShadow: '0 8px 32px rgba(0,0,0,0.35)',
                    animation: 'slideUp 0.3s ease',
                }}>
                    <span style={{ fontSize: 28, flexShrink: 0 }}>📲</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '0.88rem', color: '#fff', marginBottom: 2 }}>
                            Instala la app en tu móvil
                        </div>
                        <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.55)', lineHeight: 1.4 }}>
                            {showInstallBanner === 'ios'
                                ? 'Pulsa Compartir (□↑) → "Añadir a inicio"'
                                : 'Accede sin internet y más rápido'}
                        </div>
                    </div>
                    {showInstallBanner === 'android' && (
                        <button
                            onClick={async () => {
                                if (installPrompt) {
                                    installPrompt.prompt();
                                    const { outcome } = await installPrompt.userChoice;
                                    if (outcome === 'accepted') localStorage.setItem('pwa_dismissed', '1');
                                }
                                setShowInstallBanner(false);
                            }}
                            style={{
                                background: 'var(--primary)', color: '#fff',
                                border: 'none', borderRadius: 10,
                                padding: '9px 14px', fontWeight: 700, fontSize: '0.78rem',
                                cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
                            }}>
                            Instalar
                        </button>
                    )}
                    <button
                        onClick={() => { localStorage.setItem('pwa_dismissed', '1'); setShowInstallBanner(false); }}
                        style={{
                            background: 'rgba(255,255,255,0.10)', border: 'none',
                            borderRadius: '50%', width: 28, height: 28,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: 'rgba(255,255,255,0.60)', fontSize: 14, cursor: 'pointer',
                            flexShrink: 0,
                        }}>✕</button>
                </div>
            )}

            {/* ── Toast ── */}
            <Toast toast={toast} />
        </div>
    );
}

function Toast({ toast }) {
    return (
        <div style={{
            position: 'fixed', bottom: 88, left: '50%',
            transform: `translateX(-50%) translateY(${toast.on ? 0 : 16}px)`,
            background: '#111827', color: '#fff',
            padding: '12px 24px', borderRadius: 100,
            fontWeight: 600, fontSize: '0.88rem',
            zIndex: 300, opacity: toast.on ? 1 : 0,
            transition: 'all 0.3s', pointerEvents: 'none',
            whiteSpace: 'nowrap', boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
        }}>
            {toast.msg}
        </div>
    );
}

// Mount
const _root = document.getElementById('root');
if (_root) {
    if (ReactDOM.createRoot) {
        ReactDOM.createRoot(_root).render(<App />);
    } else {
        ReactDOM.render(<App />, _root);
    }
}
