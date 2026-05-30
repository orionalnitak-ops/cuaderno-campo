// ── Screen: Login / Registro ──
function ScreenLogin({ onLogin }) {
    const { useState } = React;
    const [tab, setTab]           = useState('login'); // 'login' | 'register'
    const [nombre, setNombre]     = useState('');
    const [email, setEmail]       = useState('');
    const [password, setPassword] = useState('');
    const [error, setError]       = useState('');
    const [loading, setLoading]   = useState(false);
    const [showPw, setShowPw]     = useState(false);

    const reset = (t) => { setTab(t); setError(''); setNombre(''); setEmail(''); setPassword(''); };

    const handleLogin = async (e) => {
        e.preventDefault();
        if (!email || !password) { setError('Introduce email y contraseña'); return; }
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
        } catch { setError('Error de conexión.'); }
        finally { setLoading(false); }
    };

    const handleRegister = async (e) => {
        e.preventDefault();
        if (!nombre.trim()) { setError('Introduce tu nombre'); return; }
        if (!email || !password) { setError('Introduce email y contraseña'); return; }
        if (password.length < 8) { setError('La contraseña debe tener al menos 8 caracteres'); return; }
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
                // Auto-login: /api/auth/register devuelve los datos del usuario
                const me = await fetch('/api/auth/me', { credentials: 'include' }).then(r => r.json());
                onLogin(me);
            }
        } catch { setError('Error de conexión.'); }
        finally { setLoading(false); }
    };

    return (
        <div style={{ minHeight: '100vh', background: 'var(--surface)', display: 'flex', flexDirection: 'column' }}>

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
                            {error && <div style={{ background:'rgba(153,63,58,0.10)', border:'1px solid rgba(153,63,58,0.20)', borderRadius:'var(--radius-lg)', padding:'12px 16px', fontSize:'0.85rem', color:'var(--tertiary)', fontWeight:600 }}>⚠️ {error}</div>}
                            <button type="submit" className="btn-primary" disabled={loading} style={{ width:'100%', marginTop:4, fontSize:'1rem' }}>
                                {loading ? 'Creando cuenta…' : '🌱  Empezar prueba gratuita'}
                            </button>
                            <p style={{ fontSize:'0.72rem', color:'var(--on-surface-variant)', textAlign:'center', margin:0, lineHeight:1.5 }}>
                                Al registrarte aceptas el uso de tus datos para la gestión del cuaderno de explotación conforme al RGPD.
                            </p>
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
