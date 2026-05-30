// ── Pantalla de selección de planes / suscripción ──
function ScreenPlanes({ currentUser, showToast, onClose }) {
    const [billing, setBilling] = React.useState('yearly');
    const [loading, setLoading] = React.useState(null); // null | 'basic' | 'pro' | 'portal'

    const PRICES = {
        monthly: { basic: '9,99 €/mes', pro: '14,99 €/mes' },
        yearly:  { basic: '100 €/año',  pro: '150 €/año'  },
    };

    const planActive  = currentUser?.plan_active !== false;
    const planLabel   = currentUser?.plan;
    const hasActiveSub = planLabel === 'basic' || planLabel === 'pro';

    const checkout = async (plan) => {
        setLoading(plan);
        try {
            const r = await fetch('/api/stripe/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ plan, billing }),
            });
            const d = await r.json();
            if (d.url) {
                window.location.href = d.url;
            } else {
                showToast('Error al iniciar el pago. Inténtalo de nuevo.');
                setLoading(null);
            }
        } catch {
            showToast('Error de conexión. Inténtalo de nuevo.');
            setLoading(null);
        }
    };

    const openPortal = async () => {
        setLoading('portal');
        try {
            const r = await fetch('/api/stripe/portal', {
                method: 'POST', credentials: 'include',
            });
            const d = await r.json();
            if (d.url) {
                window.location.href = d.url;
            } else {
                showToast('Error al abrir el portal. Inténtalo de nuevo.');
                setLoading(null);
            }
        } catch {
            showToast('Error de conexión.');
            setLoading(null);
        }
    };

    const featureBasic = [
        'Parcelas SIGPAC',
        'Tratamientos fitosanitarios',
        'Fertilización y labores',
        'Compras y ventas',
        'Exportación Excel y PDF oficial',
        'Widget meteorológico',
    ];

    return (
        <div style={{ minHeight: '100vh', background: '#f8f9fb', display: 'flex', flexDirection: 'column' }}>

            {/* Header */}
            <div style={{
                background: 'var(--surface-container)', borderBottom: '1px solid var(--outline-variant)',
                padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 12,
            }}>
                {onClose && (
                    <button onClick={onClose} style={{
                        background: 'var(--surface-container-low)', border: 'none', borderRadius: '50%',
                        width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
                        cursor: 'pointer', fontSize: 18, color: 'var(--on-surface-variant)', flexShrink: 0,
                    }}>←</button>
                )}
                <div>
                    <h1 style={{ margin: 0, fontFamily: 'var(--font-heading)', fontSize: '1.2rem', fontWeight: 800 }}>
                        Suscripción
                    </h1>
                    <p style={{ margin: '2px 0 0', fontSize: '0.78rem', color: 'var(--on-surface-variant)' }}>
                        Cuaderno de Campo Digital · RD 1311/2012
                    </p>
                </div>
            </div>

            <div style={{ flex: 1, padding: '24px 16px 40px', maxWidth: 540, margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>

                {/* Trial caducado */}
                {!planActive && (
                    <div style={{
                        background: '#fef2f2', border: '1.5px solid #fca5a5',
                        borderRadius: 12, padding: '14px 16px', marginBottom: 20,
                        fontSize: '0.86rem', color: '#991b1b', lineHeight: 1.5,
                    }}>
                        <strong>Tu período de prueba ha caducado.</strong><br />
                        Elige un plan para seguir anotando actividades y exportando tu cuaderno.
                    </div>
                )}

                {/* Suscripción activa */}
                {hasActiveSub && (
                    <div style={{
                        background: '#f0fdf4', border: '1.5px solid #86efac',
                        borderRadius: 12, padding: '14px 16px', marginBottom: 20,
                        fontSize: '0.86rem', color: '#166534', lineHeight: 1.5,
                    }}>
                        <strong>Plan {planLabel === 'basic' ? 'Básico' : 'Pro'} activo.</strong><br />
                        Para cambiar tarjeta, cancelar o descargar facturas usa el portal de suscripción.
                        <div style={{ marginTop: 10 }}>
                            <button
                                onClick={openPortal}
                                disabled={!!loading}
                                style={{
                                    background: '#16a34a', color: '#fff', border: 'none',
                                    borderRadius: 8, padding: '8px 16px', cursor: 'pointer',
                                    fontWeight: 700, fontSize: '0.82rem', fontFamily: 'var(--font-body)',
                                }}
                            >
                                {loading === 'portal' ? 'Abriendo…' : 'Gestionar suscripción →'}
                            </button>
                        </div>
                    </div>
                )}

                {/* Billing toggle */}
                <div style={{
                    display: 'flex', background: 'var(--surface-container-low)',
                    borderRadius: 10, padding: 4, marginBottom: 24, gap: 4,
                }}>
                    {[['monthly', 'Mensual'], ['yearly', 'Anual (ahorra ~17%)']].map(([val, label]) => (
                        <button key={val} onClick={() => setBilling(val)} style={{
                            flex: 1, padding: '8px 10px',
                            background: billing === val ? 'var(--primary)' : 'transparent',
                            color: billing === val ? '#fff' : 'var(--on-surface-variant)',
                            border: 'none', borderRadius: 8, cursor: 'pointer',
                            fontWeight: 600, fontSize: '0.8rem', fontFamily: 'var(--font-body)',
                            transition: 'all 0.15s',
                        }}>{label}</button>
                    ))}
                </div>

                {/* Tarjeta Básico */}
                <div style={{
                    background: '#fff', borderRadius: 16,
                    border: planLabel === 'basic' ? '2px solid #00694c' : '2px solid var(--outline-variant)',
                    overflow: 'hidden', marginBottom: 16,
                }}>
                    <div style={{
                        background: 'linear-gradient(135deg, #00694c, #008560)',
                        padding: '20px 24px 24px', color: '#fff',
                    }}>
                        {/* Nombre del plan */}
                        <div style={{ marginBottom: 18 }}>
                            <div style={{ fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', opacity: 0.65, marginBottom: 4 }}>Plan</div>
                            <div style={{ fontFamily: 'var(--font-heading)', fontSize: '1.65rem', fontWeight: 800, lineHeight: 1 }}>Básico</div>
                        </div>
                        {/* Precio */}
                        <div style={{ borderTop: '1px solid rgba(255,255,255,0.15)', paddingTop: 18 }}>
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
                                <span style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1 }}>
                                    {PRICES[billing].basic.split('/')[0]}
                                </span>
                                <span style={{ fontSize: '0.9rem', fontWeight: 600, opacity: 0.75 }}>
                                    /{PRICES[billing].basic.split('/')[1]}
                                </span>
                            </div>
                            <div style={{ fontSize: '0.72rem', opacity: 0.6, marginTop: 6 }}>IVA incluido</div>
                        </div>
                    </div>
                    <div style={{ padding: '14px 20px 18px' }}>
                        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 7 }}>
                            {featureBasic.map(f => (
                                <li key={f} style={{ display: 'flex', gap: 10, fontSize: '0.83rem', color: 'var(--on-surface)' }}>
                                    <span style={{ color: '#00694c', fontWeight: 700, flexShrink: 0 }}>✓</span>
                                    {f}
                                </li>
                            ))}
                            <li style={{ display: 'flex', gap: 10, fontSize: '0.83rem', color: 'var(--on-surface-variant)', opacity: 0.55 }}>
                                <span style={{ flexShrink: 0 }}>✗</span>
                                Integración SIEX (se añadirá en el plan Pro)
                            </li>
                        </ul>
                        {planLabel !== 'basic' && (
                            <button
                                onClick={() => checkout('basic')}
                                disabled={!!loading}
                                style={{
                                    marginTop: 14, width: '100%', minHeight: 46,
                                    background: loading === 'basic' ? 'var(--outline-variant)' : 'linear-gradient(135deg, #00694c, #008560)',
                                    color: '#fff', border: 'none', borderRadius: 10,
                                    padding: '12px 16px', fontWeight: 700, fontSize: '0.88rem',
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    fontFamily: 'var(--font-body)',
                                }}
                            >
                                {loading === 'basic' ? 'Redirigiendo a Stripe…' : `Contratar Básico · ${PRICES[billing].basic}`}
                            </button>
                        )}
                        {planLabel === 'basic' && (
                            <div style={{ marginTop: 14, textAlign: 'center', fontSize: '0.82rem', color: '#00694c', fontWeight: 700 }}>
                                ✓ Plan activo
                            </div>
                        )}
                    </div>
                </div>

                {/* Tarjeta Pro */}
                <div style={{
                    background: '#fff', borderRadius: 16,
                    border: planLabel === 'pro' ? '2px solid #4f46e5' : '2px solid #c7d2fe',
                    overflow: 'hidden', marginBottom: 16,
                }}>
                    <div style={{
                        background: 'linear-gradient(135deg, #3730a3, #4f46e5)',
                        padding: '20px 24px 24px', color: '#fff',
                    }}>
                        {/* Badge */}
                        <div style={{ marginBottom: 16 }}>
                            <span style={{
                                background: 'rgba(255,255,255,0.18)', borderRadius: 20,
                                padding: '5px 13px', fontSize: '0.62rem', fontWeight: 700,
                                letterSpacing: '0.07em',
                            }}>LISTO PARA 2027</span>
                        </div>
                        {/* Nombre del plan */}
                        <div style={{ marginBottom: 18 }}>
                            <div style={{ fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', opacity: 0.65, marginBottom: 4 }}>Plan</div>
                            <div style={{ fontFamily: 'var(--font-heading)', fontSize: '1.65rem', fontWeight: 800, lineHeight: 1 }}>Pro</div>
                        </div>
                        {/* Precio */}
                        <div style={{ borderTop: '1px solid rgba(255,255,255,0.15)', paddingTop: 18 }}>
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
                                <span style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1 }}>
                                    {PRICES[billing].pro.split('/')[0]}
                                </span>
                                <span style={{ fontSize: '0.9rem', fontWeight: 600, opacity: 0.75 }}>
                                    /{PRICES[billing].pro.split('/')[1]}
                                </span>
                            </div>
                            <div style={{ fontSize: '0.72rem', opacity: 0.6, marginTop: 6 }}>IVA incluido</div>
                        </div>
                    </div>
                    <div style={{ padding: '14px 20px 18px' }}>
                        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 7 }}>
                            {[
                                'Todo lo del plan Básico incluido',
                                ...featureBasic,
                            ].map((f, i) => (
                                <li key={i} style={{ display: 'flex', gap: 10, fontSize: '0.83rem', color: 'var(--on-surface)', fontWeight: i === 0 ? 600 : 400 }}>
                                    <span style={{ color: '#4f46e5', fontWeight: 700, flexShrink: 0 }}>✓</span>
                                    {f}
                                </li>
                            ))}
                            <li style={{ display: 'flex', gap: 10, fontSize: '0.83rem', color: 'var(--on-surface)' }}>
                                <span style={{ color: '#4f46e5', fontWeight: 700, flexShrink: 0 }}>✓</span>
                                <span>
                                    <strong>Integración SIEX</strong>
                                    <span style={{ fontWeight: 400 }}> — API FEGA, obligatoria desde enero 2027</span>
                                </span>
                            </li>
                        </ul>
                        {planLabel !== 'pro' && (
                            <button
                                onClick={() => checkout('pro')}
                                disabled={!!loading}
                                style={{
                                    marginTop: 14, width: '100%', minHeight: 46,
                                    background: loading === 'pro' ? 'var(--outline-variant)' : 'linear-gradient(135deg, #3730a3, #4f46e5)',
                                    color: '#fff', border: 'none', borderRadius: 10,
                                    padding: '12px 16px', fontWeight: 700, fontSize: '0.88rem',
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    fontFamily: 'var(--font-body)',
                                }}
                            >
                                {loading === 'pro' ? 'Redirigiendo a Stripe…' : `Contratar Pro · ${PRICES[billing].pro}`}
                            </button>
                        )}
                        {planLabel === 'pro' && (
                            <div style={{ marginTop: 14, textAlign: 'center', fontSize: '0.82rem', color: '#4f46e5', fontWeight: 700 }}>
                                ✓ Plan activo
                            </div>
                        )}
                    </div>
                </div>

                <p style={{
                    textAlign: 'center', fontSize: '0.72rem', color: 'var(--on-surface-variant)',
                    marginTop: 8, lineHeight: 1.6,
                }}>
                    Pago seguro gestionado por Stripe · Cancela en cualquier momento<br />
                    Precios con IVA incluido · Facturas automáticas por email
                </p>
            </div>
        </div>
    );
}
