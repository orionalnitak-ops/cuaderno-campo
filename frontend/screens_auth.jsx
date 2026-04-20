// ── Screen: Login / Autenticación ──
function ScreenLogin({ onLogin }) {
    const { useState } = React;
    const [email, setEmail]       = useState('');
    const [password, setPassword] = useState('');
    const [error, setError]       = useState('');
    const [loading, setLoading]   = useState(false);
    const [showPw, setShowPw]     = useState(false);

    const handleLogin = async (e) => {
        e.preventDefault();
        if (!email || !password) { setError('Introduce email y contraseña'); return; }
        setLoading(true);
        setError('');
        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
                credentials: 'include',
            });
            const data = await res.json();
            if (!res.ok) {
                setError(data.error || 'Credenciales incorrectas');
            } else {
                onLogin(data);
            }
        } catch {
            setError('Error de conexión. Comprueba que el servidor está activo.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            background: 'var(--surface)',
            display: 'flex',
            flexDirection: 'column',
        }}>
            {/* ── Hero header ── */}
            <div style={{
                background: 'linear-gradient(160deg, var(--secondary-fixed) 0%, #1e3a5f 100%)',
                padding: '56px 24px 40px',
                position: 'relative',
                overflow: 'hidden',
                textAlign: 'center',
            }}>
                {/* Orbs decorativos */}
                <div style={{ position:'absolute', top:-60, right:-60, width:220, height:220, borderRadius:'50%', background:'rgba(104,219,174,0.05)', pointerEvents:'none' }} />
                <div style={{ position:'absolute', bottom:-50, left:-30, width:150, height:150, borderRadius:'50%', background:'rgba(104,219,174,0.04)', pointerEvents:'none' }} />

                <div style={{ position:'relative' }}>
                    <div style={{
                        width: 72, height: 72,
                        borderRadius: 'var(--radius-xl)',
                        background: 'linear-gradient(135deg, var(--primary), var(--primary-container))',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 36, margin: '0 auto 20px',
                        boxShadow: 'var(--shadow-fab)',
                    }}>🌿</div>
                    <h1 style={{
                        fontFamily: 'var(--font-heading)',
                        fontWeight: 800, fontSize: '1.7rem',
                        color: '#fff', margin: '0 0 8px',
                        letterSpacing: '-0.02em',
                    }}>Cuaderno de Campo</h1>
                    <p style={{
                        color: 'var(--primary-fixed-dim)',
                        fontSize: '0.85rem', margin: 0,
                        fontWeight: 500,
                    }}>
                        Registro oficial de explotación agrícola · RD 1311/2012
                    </p>
                </div>
            </div>

            {/* ── Form card ── */}
            <div style={{ flex: 1, padding: '28px 20px 32px', maxWidth: 440, width: '100%', margin: '0 auto' }}>
                <h2 style={{
                    fontFamily: 'var(--font-heading)',
                    fontWeight: 800, fontSize: '1.25rem',
                    margin: '0 0 6px',
                    color: 'var(--on-background)',
                    letterSpacing: '-0.01em',
                }}>Acceder</h2>
                <p style={{ fontSize: '0.83rem', color: 'var(--on-surface-variant)', margin: '0 0 28px' }}>
                    Introduce tus credenciales para entrar al cuaderno.
                </p>

                <form onSubmit={handleLogin} style={{ display:'flex', flexDirection:'column', gap: 16 }}>
                    {/* Email */}
                    <div>
                        <label className="field-label">Email</label>
                        <input
                            className="input-field"
                            type="email"
                            placeholder="tu@email.es"
                            value={email}
                            onChange={e => { setEmail(e.target.value); setError(''); }}
                            autoComplete="email"
                            autoFocus
                            style={{ fontSize: '1rem' }}
                        />
                    </div>

                    {/* Contraseña */}
                    <div>
                        <label className="field-label">Contraseña</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                className="input-field"
                                type={showPw ? 'text' : 'password'}
                                placeholder="••••••••"
                                value={password}
                                onChange={e => { setPassword(e.target.value); setError(''); }}
                                autoComplete="current-password"
                                style={{ fontSize: '1rem', paddingRight: 48 }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPw(s => !s)}
                                style={{
                                    position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%)',
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    fontSize: 18, color: 'var(--outline)', padding: 4,
                                }}
                            >{showPw ? '🙈' : '👁'}</button>
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div style={{
                            background: 'rgba(153,63,58,0.10)',
                            border: '1px solid rgba(153,63,58,0.20)',
                            borderRadius: 'var(--radius-lg)',
                            padding: '12px 16px',
                            fontSize: '0.85rem',
                            color: 'var(--tertiary)',
                            fontWeight: 600,
                        }}>
                            ⚠️ {error}
                        </div>
                    )}

                    {/* Botón */}
                    <button
                        type="submit"
                        className="btn-primary"
                        disabled={loading}
                        style={{ width: '100%', marginTop: 4, fontSize: '1rem' }}
                    >
                        {loading ? 'Entrando…' : '🔑  Iniciar sesión'}
                    </button>
                </form>

                {/* Nota */}
                <div style={{
                    marginTop: 28,
                    padding: '14px 16px',
                    background: 'var(--surface-container-low)',
                    borderRadius: 'var(--radius-lg)',
                    fontSize: '0.78rem',
                    color: 'var(--on-surface-variant)',
                    lineHeight: 1.5,
                }}>
                    🔒 Las cuentas las crea el administrador. Si necesitas acceso, contacta con tu asesor agrícola.
                </div>

                {/* Footer legal */}
                <p style={{
                    marginTop: 24,
                    textAlign: 'center',
                    fontSize: '0.7rem',
                    color: 'var(--outline)',
                }}>
                    v2.0 · RD 1311/2012 · Cuaderno de Campo Digital
                </p>
            </div>
        </div>
    );
}
