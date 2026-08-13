// ── Screen: Login / Registro ──
function ScreenLogin({ onLogin }) {
    const { useState } = React;
    const [tab, setTab]           = useState('login'); // 'login' | 'register'
    const [nombre, setNombre]     = useState('');
    const [email, setEmail]       = useState('');
    const [password, setPassword] = useState('');
    const [error, setError]       = useState('');
    const [loading, setLoading]   = useState(false);
    const [showPw, setShowPw]           = useState(false);
    const [privacidad, setPrivacidad]   = useState(false);

    const reset = (t) => { setTab(t); setError(''); setNombre(''); setEmail(''); setPassword(''); setPrivacidad(false); };

    const handleLogin = async (e) => {
        e.preventDefault();
        if (!email || !password) { setError('Introduce email y contraseña'); return; }
        if (!navigator.onLine) {
            setError('Sin conexión. Inicia sesión al menos una vez con red para poder acceder sin cobertura después.');
            return;
        }
        setLoading(true); setError('');
        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
                credentials: 'include',
            });
            const data = await res.json();
            if (!res.ok) { setError(data.error || 'Credenciales incorrectas'); }
            else { onLogin(data); }
        } catch { setError('Sin conexión. Inicia sesión cuando tengas red.'); }
        finally { setLoading(false); }
    };

    const handleRegister = async (e) => {
        e.preventDefault();
        if (!nombre.trim()) { setError('Introduce tu nombre'); return; }
        if (!email || !password) { setError('Introduce email y contraseña'); return; }
        if (password.length < 8) { setError('La contraseña debe tener al menos 8 caracteres'); return; }
        if (!privacidad) { setError('Debes aceptar la Política de Privacidad para continuar'); return; }
        setLoading(true); setError('');
        try {
            const res = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nombre: nombre.trim(), email: email.trim().toLowerCase(), password }),
                credentials: 'include',
            });
            const data = await res.json();
            if (!res.ok) { setError(data.error || 'No se pudo crear la cuenta'); }
            else {
                onLogin(data);
            }
        } catch { setError('Error de conexión.'); }
        finally { setLoading(false); }
    };

    return (
        <div style={{ minHeight: '100vh', background: 'var(--surface)', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>

            {/* ── Hero header ── */}
            <div style={{
                background: 'linear-gradient(160deg, var(--secondary-fixed) 0%, #1e3a5f 100%)',
                padding: '56px 24px 40px',
                position: 'relative', overflow: 'hidden', textAlign: 'center',
            }}>
                <div style={{ position:'absolute', top:-60, right:-60, width:220, height:220, borderRadius:'50%', background:'rgba(104,219,174,0.05)', pointerEvents:'none' }} />
                <div style={{ position:'absolute', bottom:-50, left:-30, width:150, height:150, borderRadius:'50%', background:'rgba(104,219,174,0.04)', pointerEvents:'none' }} />
                <div style={{ position:'relative' }}>
                    <div style={{
                        width: 72, height: 72, borderRadius: 'var(--radius-xl)',
                        background: 'linear-gradient(135deg, var(--primary), var(--primary-container))',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 36, margin: '0 auto 20px', boxShadow: 'var(--shadow-fab)',
                    }}>🌿</div>
                    <h1 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.7rem', color: '#fff', margin: '0 0 8px', letterSpacing: '-0.02em' }}>
                        Cuaderno de Campo
                    </h1>
                    <p style={{ color: 'var(--primary-fixed-dim)', fontSize: '0.85rem', margin: 0, fontWeight: 500 }}>
                        Registro oficial de explotación agrícola · RD 1311/2012
                    </p>
                </div>
            </div>

            {/* ── Form card ── */}
            <div style={{ flex: 1, padding: '28px 20px 32px', maxWidth: 440, width: '100%', margin: '0 auto' }}>

                {/* Tabs */}
                <div style={{ display: 'flex', background: 'var(--surface-container-low)', borderRadius: 10, padding: 4, marginBottom: 28, gap: 4 }}>
                    {[['login', 'Acceder'], ['register', 'Crear cuenta']].map(([t, label]) => (
                        <button key={t} onClick={() => reset(t)} style={{
                            flex: 1, padding: '9px 12px',
                            background: tab === t ? 'var(--primary)' : 'transparent',
                            color: tab === t ? '#fff' : 'var(--on-surface-variant)',
                            border: 'none', borderRadius: 8, cursor: 'pointer',
                            fontWeight: 700, fontSize: '0.88rem', fontFamily: 'var(--font-body)',
                            transition: 'all 0.15s',
                        }}>{label}</button>
                    ))}
                </div>

                {tab === 'login' ? (
                    <>
                        <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.25rem', margin: '0 0 6px', color: 'var(--on-background)', letterSpacing: '-0.01em' }}>
                            Acceder
                        </h2>
                        <p style={{ fontSize: '0.83rem', color: 'var(--on-surface-variant)', margin: '0 0 24px' }}>
                            Introduce tus credenciales para entrar al cuaderno.
                        </p>
                        <form onSubmit={handleLogin} style={{ display:'flex', flexDirection:'column', gap: 16 }}>
                            <div>
                                <label className="field-label">Email</label>
                                <input className="input-field" type="email" placeholder="tu@email.es"
                                    value={email} onChange={e => { setEmail(e.target.value); setError(''); }}
                                    autoComplete="email" autoFocus style={{ fontSize: '1rem' }} />
                            </div>
                            <div>
                                <label className="field-label">Contraseña</label>
                                <div style={{ position: 'relative' }}>
                                    <input className="input-field" type={showPw ? 'text' : 'password'}
                                        placeholder="••••••••" value={password}
                                        onChange={e => { setPassword(e.target.value); setError(''); }}
                                        autoComplete="current-password" style={{ fontSize: '1rem', paddingRight: 48 }} />
                                    <button type="button" onClick={() => setShowPw(s => !s)} style={{
                                        position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%)',
                                        background: 'none', border: 'none', cursor: 'pointer',
                                        fontSize: 18, color: 'var(--outline)', padding: 4,
                                    }}>{showPw ? '🙈' : '👁'}</button>
                                </div>
                            </div>
                            {error && <div style={{ background:'rgba(153,63,58,0.10)', border:'1px solid rgba(153,63,58,0.20)', borderRadius:'var(--radius-lg)', padding:'12px 16px', fontSize:'0.85rem', color:'var(--tertiary)', fontWeight:600 }}>⚠️ {error}</div>}
                            <button type="submit" className="btn-primary" disabled={loading} style={{ width:'100%', marginTop:4, fontSize:'1rem' }}>
                                {loading ? 'Entrando…' : '🔑  Iniciar sesión'}
                            </button>
                        </form>
                        <p style={{ textAlign:'center', marginTop:16 }}>
                            <button type="button" onClick={() => { window.location.href = '/recuperar'; }}
                                style={{ background:'none', border:'none', color:'var(--primary)',
                                         fontWeight:600, fontSize:'0.83rem', cursor:'pointer' }}>
                                ¿Olvidaste tu contraseña?
                            </button>
                        </p>
                    </>
                ) : (
                    <>
                        <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.25rem', margin: '0 0 6px', color: 'var(--on-background)', letterSpacing: '-0.01em' }}>
                            Crear cuenta
                        </h2>
                        <p style={{ fontSize: '0.83rem', color: 'var(--on-surface-variant)', margin: '0 0 24px' }}>
                            7 días de prueba gratuita · Sin tarjeta · Cancela cuando quieras.
                        </p>
                        <form onSubmit={handleRegister} style={{ display:'flex', flexDirection:'column', gap: 16 }}>
                            <div>
                                <label className="field-label">Tu nombre</label>
                                <input className="input-field" type="text" placeholder="Juan García"
                                    value={nombre} onChange={e => { setNombre(e.target.value); setError(''); }}
                                    autoComplete="name" autoFocus style={{ fontSize: '1rem' }} />
                            </div>
                            <div>
                                <label className="field-label">Email</label>
                                <input className="input-field" type="email" placeholder="tu@email.es"
                                    value={email} onChange={e => { setEmail(e.target.value); setError(''); }}
                                    autoComplete="email" style={{ fontSize: '1rem' }} />
                            </div>
                            <div>
                                <label className="field-label">Contraseña <span style={{ fontWeight:400, fontSize:'0.75rem' }}>(mín. 8 caracteres)</span></label>
                                <div style={{ position: 'relative' }}>
                                    <input className="input-field" type={showPw ? 'text' : 'password'}
                                        placeholder="••••••••" value={password}
                                        onChange={e => { setPassword(e.target.value); setError(''); }}
                                        autoComplete="new-password" style={{ fontSize: '1rem', paddingRight: 48 }} />
                                    <button type="button" onClick={() => setShowPw(s => !s)} style={{
                                        position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%)',
                                        background: 'none', border: 'none', cursor: 'pointer',
                                        fontSize: 18, color: 'var(--outline)', padding: 4,
                                    }}>{showPw ? '🙈' : '👁'}</button>
                                </div>
                            </div>
                            <label style={{ display:'flex', alignItems:'flex-start', gap:10, cursor:'pointer', userSelect:'none' }}>
                                <input
                                    type="checkbox"
                                    checked={privacidad}
                                    onChange={e => { setPrivacidad(e.target.checked); setError(''); }}
                                    style={{ marginTop:2, width:18, height:18, accentColor:'var(--primary)', flexShrink:0, cursor:'pointer' }}
                                />
                                <span style={{ fontSize:'0.78rem', color:'var(--on-surface-variant)', lineHeight:1.5 }}>
                                    He leído y acepto la{' '}
                                    <a href="/privacidad" target="_blank" rel="noopener noreferrer"
                                       style={{ color:'var(--primary)', fontWeight:600 }}>
                                        Política de Privacidad
                                    </a>
                                    {' '}y el tratamiento de mis datos para la gestión del cuaderno de explotación.
                                </span>
                            </label>
                            {error && <div style={{ background:'rgba(153,63,58,0.10)', border:'1px solid rgba(153,63,58,0.20)', borderRadius:'var(--radius-lg)', padding:'12px 16px', fontSize:'0.85rem', color:'var(--tertiary)', fontWeight:600 }}>⚠️ {error}</div>}
                            <button type="submit" className="btn-primary" disabled={loading || !privacidad} style={{ width:'100%', marginTop:4, fontSize:'1rem', opacity: privacidad ? 1 : 0.5 }}>
                                {loading ? 'Creando cuenta…' : '🌱  Empezar prueba gratuita'}
                            </button>
                        </form>
                    </>
                )}

                {/* Footer legal */}
                <p style={{ marginTop: 28, textAlign: 'center', fontSize: '0.7rem', color: 'var(--outline)' }}>
                    v2.0 · RD 1311/2012 · Cuaderno de Campo Digital
                </p>
            </div>
        </div>
    );
}


// ── Shell común para las pantallas públicas de correo (recuperar / reset / verificar) ──
function ScreenAuthPublic({ titulo, children }) {
    return (
        <div style={{ minHeight: '100vh', background: 'var(--surface)', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
            <div style={{
                background: 'linear-gradient(160deg, var(--secondary-fixed) 0%, #1e3a5f 100%)',
                padding: '48px 24px 32px', textAlign: 'center',
            }}>
                <div style={{
                    width: 64, height: 64, borderRadius: 'var(--radius-xl)',
                    background: 'linear-gradient(135deg, var(--primary), var(--primary-container))',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 32, margin: '0 auto 16px', boxShadow: 'var(--shadow-fab)',
                }}>🌿</div>
                <h1 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.4rem', color: '#fff', margin: 0, letterSpacing: '-0.02em' }}>
                    {titulo}
                </h1>
            </div>
            <div style={{ flex: 1, padding: '28px 20px 32px', maxWidth: 440, width: '100%', margin: '0 auto' }}>
                {children}
                <p style={{ marginTop: 28, textAlign: 'center' }}>
                    <a href="/" style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '0.85rem', textDecoration: 'none' }}>
                        ← Volver al inicio
                    </a>
                </p>
            </div>
        </div>
    );
}


// ── Screen: Recuperar contraseña (pedir email) ──
function ScreenRecuperar() {
    const { useState } = React;
    const [email, setEmail]     = useState('');
    const [enviado, setEnviado] = useState(false);
    const [loading, setLoading] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        if (!email.trim()) return;
        setLoading(true);
        try {
            await fetch('/api/auth/forgot-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email.trim().toLowerCase() }),
                credentials: 'include',
            });
        } catch { /* respuesta idéntica pase lo que pase: no se filtra nada */ }
        setEnviado(true);
        setLoading(false);
    };

    return (
        <ScreenAuthPublic titulo="Recuperar contraseña">
            {enviado ? (
                <div style={{ background:'rgba(0,105,76,0.08)', border:'1px solid rgba(0,105,76,0.20)', borderRadius:'var(--radius-lg)', padding:'18px 20px', fontSize:'0.9rem', color:'var(--on-background)', lineHeight:1.6 }}>
                    ✅ Si ese correo está registrado, te hemos enviado un enlace para cambiar la contraseña. Revisa tu bandeja de entrada (y el spam, por si acaso).
                </div>
            ) : (
                <>
                    <p style={{ fontSize: '0.88rem', color: 'var(--on-surface-variant)', margin: '0 0 22px', lineHeight:1.6 }}>
                        Escribe tu email y te enviamos un enlace para poner una contraseña nueva.
                    </p>
                    <form onSubmit={submit} style={{ display:'flex', flexDirection:'column', gap: 16 }}>
                        <div>
                            <label className="field-label">Email</label>
                            <input className="input-field" type="email" placeholder="tu@email.es"
                                value={email} onChange={e => setEmail(e.target.value)}
                                autoComplete="email" autoFocus style={{ fontSize: '1rem' }} />
                        </div>
                        <button type="submit" className="btn-primary" disabled={loading} style={{ width:'100%', fontSize:'1rem' }}>
                            {loading ? 'Enviando…' : '📩  Enviarme el enlace'}
                        </button>
                    </form>
                </>
            )}
        </ScreenAuthPublic>
    );
}


// ── Screen: Nueva contraseña (desde el enlace del correo) ──
function ScreenNuevaContrasena() {
    const { useState } = React;
    const token = new URLSearchParams(window.location.search).get('token') || '';
    const [password, setPassword] = useState('');
    const [showPw, setShowPw]     = useState(false);
    const [error, setError]       = useState('');
    const [hecho, setHecho]       = useState(false);
    const [loading, setLoading]   = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        if (password.length < 8) { setError('La contraseña debe tener al menos 8 caracteres'); return; }
        setLoading(true); setError('');
        try {
            const res = await fetch('/api/auth/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, password }),
                credentials: 'include',
            });
            const data = await res.json();
            if (!res.ok) { setError(data.error || 'No se pudo cambiar la contraseña'); }
            else { setHecho(true); }
        } catch { setError('Error de conexión.'); }
        finally { setLoading(false); }
    };

    return (
        <ScreenAuthPublic titulo="Nueva contraseña">
            {hecho ? (
                <div style={{ background:'rgba(0,105,76,0.08)', border:'1px solid rgba(0,105,76,0.20)', borderRadius:'var(--radius-lg)', padding:'18px 20px', fontSize:'0.9rem', color:'var(--on-background)', lineHeight:1.6 }}>
                    ✅ Contraseña cambiada. Ya puedes <a href="/" style={{ color:'var(--primary)', fontWeight:700 }}>iniciar sesión</a> con la nueva.
                </div>
            ) : !token ? (
                <div style={{ background:'rgba(153,63,58,0.10)', border:'1px solid rgba(153,63,58,0.20)', borderRadius:'var(--radius-lg)', padding:'14px 18px', fontSize:'0.88rem', color:'var(--tertiary)', fontWeight:600 }}>
                    ⚠️ Enlace incompleto. Vuelve a pedir el correo de recuperación.
                </div>
            ) : (
                <>
                    <p style={{ fontSize: '0.88rem', color: 'var(--on-surface-variant)', margin: '0 0 22px', lineHeight:1.6 }}>
                        Escribe tu contraseña nueva (mínimo 8 caracteres).
                    </p>
                    <form onSubmit={submit} style={{ display:'flex', flexDirection:'column', gap: 16 }}>
                        <div>
                            <label className="field-label">Nueva contraseña</label>
                            <div style={{ position: 'relative' }}>
                                <input className="input-field" type={showPw ? 'text' : 'password'}
                                    placeholder="••••••••" value={password}
                                    onChange={e => { setPassword(e.target.value); setError(''); }}
                                    autoComplete="new-password" autoFocus style={{ fontSize: '1rem', paddingRight: 48 }} />
                                <button type="button" onClick={() => setShowPw(s => !s)} style={{
                                    position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%)',
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    fontSize: 18, color: 'var(--outline)', padding: 4,
                                }}>{showPw ? '🙈' : '👁'}</button>
                            </div>
                        </div>
                        {error && <div style={{ background:'rgba(153,63,58,0.10)', border:'1px solid rgba(153,63,58,0.20)', borderRadius:'var(--radius-lg)', padding:'12px 16px', fontSize:'0.85rem', color:'var(--tertiary)', fontWeight:600 }}>⚠️ {error}</div>}
                        <button type="submit" className="btn-primary" disabled={loading} style={{ width:'100%', fontSize:'1rem' }}>
                            {loading ? 'Guardando…' : '🔒  Guardar contraseña'}
                        </button>
                    </form>
                </>
            )}
        </ScreenAuthPublic>
    );
}


// ── Screen: Verificación de correo (consume el token al abrir el enlace) ──
function ScreenVerificar() {
    const { useState, useEffect } = React;
    const [estado, setEstado] = useState('verificando'); // verificando | ok | error

    useEffect(() => {
        const token = new URLSearchParams(window.location.search).get('token') || '';
        if (!token) { setEstado('error'); return; }
        fetch('/api/auth/verify-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token }),
            credentials: 'include',
        })
            .then(r => setEstado(r.ok ? 'ok' : 'error'))
            .catch(() => setEstado('error'));
    }, []);

    return (
        <ScreenAuthPublic titulo="Verificar correo">
            {estado === 'verificando' && (
                <p style={{ textAlign:'center', color:'var(--on-surface-variant)', fontSize:'0.9rem' }}>Verificando…</p>
            )}
            {estado === 'ok' && (
                <div style={{ background:'rgba(0,105,76,0.08)', border:'1px solid rgba(0,105,76,0.20)', borderRadius:'var(--radius-lg)', padding:'18px 20px', fontSize:'0.9rem', color:'var(--on-background)', lineHeight:1.6 }}>
                    ✅ Correo verificado. Gracias. Ya puedes <a href="/" style={{ color:'var(--primary)', fontWeight:700 }}>entrar al cuaderno</a>.
                </div>
            )}
            {estado === 'error' && (
                <div style={{ background:'rgba(153,63,58,0.10)', border:'1px solid rgba(153,63,58,0.20)', borderRadius:'var(--radius-lg)', padding:'14px 18px', fontSize:'0.88rem', color:'var(--tertiary)', fontWeight:600 }}>
                    ⚠️ El enlace no es válido o ya ha caducado. No pasa nada: puedes seguir usando la app igualmente.
                </div>
            )}
        </ScreenAuthPublic>
    );
}
