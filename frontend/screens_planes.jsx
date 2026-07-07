// ── Pantalla de selección de planes / suscripción ──
function ScreenPlanes({ currentUser, showToast, onClose }) {
    const [billing, setBilling] = React.useState('yearly');
    const [loading, setLoading] = React.useState(null);
    const [isWide, setIsWide] = React.useState(() => window.innerWidth >= 700);

    React.useEffect(() => {
        const handle = () => setIsWide(window.innerWidth >= 700);
        window.addEventListener('resize', handle);
        return () => window.removeEventListener('resize', handle);
    }, []);

    const planLabel    = currentUser?.plan;
    const planActive   = currentUser?.plan_active !== false;
    const hasActiveSub = planLabel === 'basic' || planLabel === 'pro' || planLabel === 'premium';

    const checkout = async (plan, billingOverride) => {
        setLoading(plan);
        try {
            const r = await fetch('/api/stripe/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ plan, billing: billingOverride || billing }),
            });
            const d = await r.json();
            if (d.url) { window.location.href = d.url; }
            else { showToast('Error al iniciar el pago. Inténtalo de nuevo.'); setLoading(null); }
        } catch { showToast('Error de conexión. Inténtalo de nuevo.'); setLoading(null); }
    };

    const openPortal = async () => {
        setLoading('portal');
        try {
            const r = await fetch('/api/stripe/portal', { method: 'POST', credentials: 'include' });
            const d = await r.json();
            if (d.url) { window.location.href = d.url; }
            else { showToast('Error al abrir el portal.'); setLoading(null); }
        } catch { showToast('Error de conexión.'); setLoading(null); }
    };

    const PLANS = [
        {
            id: 'basic',
            name: 'Básico',
            tagline: 'Todo lo que necesitas para cumplir con la ley',
            popular: true,
            monthly: { price: '9,99', unit: '/mes', original: null },
            yearly:  { price: '100',  unit: '/año', original: '119,88 €' },
            color: '#00694c',
            gradient: 'linear-gradient(135deg, #005c42, #00694c)',
            features: [
                'Parcelas SIGPAC',
                'Tratamientos fitosanitarios',
                'Fertilización y labores',
                'Compras y ventas',
                'Exportación Excel y PDF oficial',
                'Widget meteorológico',
            ],
            missing: ['Integración SIEX (disponible en Pro)'],
        },
        {
            id: 'pro',
            name: 'Pro',
            tagline: 'Preparado para la obligatoriedad de enero 2027',
            popular: false,
            monthly: { price: '14,99', unit: '/mes', original: null },
            yearly:  { price: '150',   unit: '/año', original: '179,88 €' },
            color: '#4f46e5',
            gradient: 'linear-gradient(135deg, #3730a3, #4f46e5)',
            features: [
                'Todo lo del plan Básico incluido',
                'Integración SIEX — API FEGA, obligatoria desde 2027',
                'Panel asesor — gestiona todos tus clientes',
                'Hasta 5 explotaciones',
                'Soporte prioritario',
            ],
            missing: [],
        },
        {
            id: 'premium',
            name: 'Premium',
            tagline: 'Para asesores y grandes explotaciones',
            popular: false,
            annualOnly: true,
            // De momento 200 €/año. Ajusta el precio y crea el Price en Stripe
            // (STRIPE_PRICE_PREMIUM_YEARLY).
            monthly: { price: '200', unit: '/año', original: null },
            yearly:  { price: '200', unit: '/año', original: null },
            color: '#b45309',
            gradient: 'linear-gradient(135deg, #92400e, #b45309)',
            // TODO: detallar las ventajas exactas del plan Premium.
            features: [
                'Todo lo del plan Pro incluido',
                'Explotaciones ilimitadas',
                '(Próximamente: más ventajas Premium)',
            ],
            missing: [],
        },
    ];

    return (
        <div style={{ minHeight: '100vh', background: '#f0f2f5', display: 'flex', flexDirection: 'column' }}>

            {/* Header */}
            <div style={{
                background: 'linear-gradient(135deg, #111827, #1f2937)',
                padding: '52px 20px 28px',
                textAlign: 'center',
                position: 'relative',
            }}>
                {onClose && (
                    <button onClick={onClose} style={{
                        position: 'absolute', top: 16, left: 16,
                        background: 'rgba(255,255,255,0.10)', border: 'none', borderRadius: '50%',
                        width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
                        cursor: 'pointer', fontSize: 18, color: '#fff',
                    }}>←</button>
                )}
                <HelpButton screenId="planes" style={{ position: 'absolute', top: 16, right: 16 }} />
                <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: isWide ? '1.9rem' : '1.5rem', fontWeight: 800, color: '#fff', margin: '0 0 6px' }}>
                    Elige tu plan
                </h1>
                <p style={{ color: 'rgba(255,255,255,0.50)', fontSize: '0.83rem', margin: 0 }}>
                    Cuaderno de Campo Digital · RD 1311/2012
                </p>
            </div>

            {/* Suscripción activa */}
            {hasActiveSub && (
                <div style={{
                    background: '#f0fdf4', border: '1px solid #86efac',
                    margin: isWide ? '20px auto 0' : '16px 16px 0',
                    maxWidth: isWide ? 860 : undefined,
                    width: isWide ? 'calc(100% - 64px)' : undefined,
                    borderRadius: 10, padding: '12px 20px',
                    fontSize: '0.84rem', color: '#166534',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
                    boxSizing: 'border-box',
                }}>
                    <span>✅ Plan {planLabel === 'basic' ? 'Básico' : planLabel === 'premium' ? 'Premium' : 'Pro'} activo. Gestiona facturación y cancelación desde el portal.</span>
                    <button onClick={openPortal} disabled={!!loading} style={{
                        background: '#16a34a', color: '#fff', border: 'none', borderRadius: 8,
                        padding: '7px 14px', fontWeight: 700, fontSize: '0.78rem',
                        cursor: 'pointer', fontFamily: 'var(--font-body)', whiteSpace: 'nowrap',
                    }}>
                        {loading === 'portal' ? 'Abriendo…' : 'Gestionar →'}
                    </button>
                </div>
            )}

            {/* Trial caducado */}
            {!planActive && !hasActiveSub && (
                <div style={{
                    background: '#fef2f2', border: '1px solid #fca5a5',
                    margin: isWide ? '20px auto 0' : '16px 16px 0',
                    maxWidth: isWide ? 860 : undefined,
                    width: isWide ? 'calc(100% - 64px)' : undefined,
                    borderRadius: 10, padding: '12px 20px',
                    fontSize: '0.84rem', color: '#991b1b',
                    boxSizing: 'border-box',
                }}>
                    <strong>Tu período de prueba ha caducado.</strong> Elige un plan para seguir anotando actividades y exportando tu cuaderno.
                </div>
            )}

            {/* Toggle mensual / anual */}
            <div style={{ display: 'flex', justifyContent: 'center', padding: '24px 16px 8px' }}>
                <div style={{ background: '#e5e7eb', borderRadius: 100, padding: 4, display: 'inline-flex', gap: 2 }}>
                    {[['monthly', 'Mensual'], ['yearly', 'Anual']].map(([val, label]) => (
                        <button key={val} onClick={() => setBilling(val)} style={{
                            padding: '8px 20px', borderRadius: 100, border: 'none', cursor: 'pointer',
                            fontWeight: 700, fontSize: '0.82rem', fontFamily: 'var(--font-body)',
                            background: billing === val ? '#fff' : 'transparent',
                            color: billing === val ? '#111827' : '#6b7280',
                            boxShadow: billing === val ? '0 1px 4px rgba(0,0,0,0.12)' : 'none',
                            transition: 'all 0.15s', whiteSpace: 'nowrap',
                            display: 'flex', alignItems: 'center', gap: 6,
                        }}>
                            {label}
                            {val === 'yearly' && (
                                <span style={{
                                    background: billing === 'yearly' ? '#dcfce7' : '#f3f4f6',
                                    color: billing === 'yearly' ? '#166534' : '#9ca3af',
                                    borderRadius: 100, padding: '2px 7px',
                                    fontSize: '0.66rem', fontWeight: 800,
                                    transition: 'all 0.15s',
                                }}>−17 %</span>
                            )}
                        </button>
                    ))}
                </div>
            </div>

            {/* Tarjetas */}
            <div style={{
                display: 'flex',
                flexDirection: isWide ? 'row' : 'column',
                gap: isWide ? 20 : 16,
                padding: isWide ? '24px 32px 48px' : '16px 16px 48px',
                maxWidth: 900,
                margin: '0 auto',
                width: '100%',
                boxSizing: 'border-box',
                alignItems: isWide ? 'flex-start' : 'stretch',
            }}>
                {PLANS.map(plan => {
                    const info = plan.annualOnly ? plan.yearly : (billing === 'yearly' ? plan.yearly : plan.monthly);
                    const showDiscount = billing === 'yearly' && !plan.annualOnly;
                    const active = planLabel === plan.id;
                    const isPopular = plan.popular;

                    return (
                        <div key={plan.id} style={{
                            flex: 1,
                            background: '#fff',
                            borderRadius: 16,
                            overflow: 'hidden',
                            border: `2px solid ${active || isPopular ? plan.color : '#e5e7eb'}`,
                            boxShadow: isPopular
                                ? '0 12px 40px rgba(0,0,0,0.13)'
                                : '0 2px 8px rgba(0,0,0,0.06)',
                            transform: isWide && isPopular ? 'translateY(-10px)' : 'none',
                            transition: 'box-shadow 0.2s',
                        }}>

                            {/* Banner "MÁS POPULAR" */}
                            {isPopular ? (
                                <div style={{
                                    background: plan.gradient,
                                    color: '#fff', textAlign: 'center',
                                    padding: '9px 16px',
                                    fontSize: '0.67rem', fontWeight: 800,
                                    letterSpacing: '0.13em', textTransform: 'uppercase',
                                }}>
                                    ⭐ MÁS POPULAR
                                </div>
                            ) : (
                                <div style={{ height: 38 }} />
                            )}

                            {/* Cuerpo de la tarjeta */}
                            <div style={{ padding: '20px 24px 0' }}>

                                {/* Nombre + badge descuento */}
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                                    <div>
                                        <div style={{ fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#9ca3af', marginBottom: 4 }}>Plan</div>
                                        <div style={{ fontFamily: 'var(--font-heading)', fontSize: '1.65rem', fontWeight: 800, color: '#111827', lineHeight: 1 }}>{plan.name}</div>
                                    </div>
                                    {showDiscount && (
                                        <div style={{
                                            background: plan.id === 'basic' ? '#dcfce7' : '#ede9fe',
                                            color: plan.color,
                                            borderRadius: 100, padding: '4px 11px',
                                            fontSize: '0.72rem', fontWeight: 800,
                                        }}>−17 %</div>
                                    )}
                                    {plan.annualOnly && (
                                        <div style={{
                                            background: '#fef3c7', color: plan.color,
                                            borderRadius: 100, padding: '4px 11px',
                                            fontSize: '0.72rem', fontWeight: 800,
                                        }}>Solo anual</div>
                                    )}
                                </div>

                                <p style={{ fontSize: '0.78rem', color: '#6b7280', margin: '6px 0 16px', lineHeight: 1.5 }}>
                                    {plan.tagline}
                                </p>

                                {/* Precio */}
                                <div style={{ marginBottom: 20 }}>
                                    {info.original && (
                                        <div style={{ fontSize: '0.82rem', color: '#9ca3af', textDecoration: 'line-through', marginBottom: 2 }}>
                                            {info.original}
                                        </div>
                                    )}
                                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                                        <span style={{
                                            fontFamily: 'var(--font-heading)', fontSize: '2.5rem',
                                            fontWeight: 800, color: '#111827', lineHeight: 1, letterSpacing: '-0.03em',
                                        }}>
                                            {info.price}
                                        </span>
                                        <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#374151', marginLeft: 2 }}>€</span>
                                        <span style={{ fontSize: '0.82rem', color: '#9ca3af', marginLeft: 3 }}>{info.unit}</span>
                                    </div>
                                    <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: 4 }}>IVA incluido</div>
                                </div>

                                {/* Botón CTA */}
                                {!active ? (
                                    <button
                                        onClick={() => checkout(plan.id, plan.annualOnly ? 'yearly' : undefined)}
                                        disabled={!!loading}
                                        style={{
                                            width: '100%', minHeight: 50,
                                            background: loading === plan.id ? '#e5e7eb' : plan.gradient,
                                            color: loading === plan.id ? '#9ca3af' : '#fff',
                                            border: 'none', borderRadius: 10,
                                            padding: '13px 16px', fontWeight: 700, fontSize: '0.92rem',
                                            cursor: loading ? 'not-allowed' : 'pointer',
                                            fontFamily: 'var(--font-body)',
                                            boxShadow: loading === plan.id ? 'none' : `0 4px 16px ${plan.color}40`,
                                        }}
                                    >
                                        {loading === plan.id ? 'Redirigiendo a Stripe…' : `Contratar ${plan.name}`}
                                    </button>
                                ) : (
                                    <div style={{
                                        width: '100%', minHeight: 50,
                                        border: `2px solid ${plan.color}`, borderRadius: 10,
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        fontWeight: 700, fontSize: '0.92rem', color: plan.color,
                                        boxSizing: 'border-box',
                                    }}>
                                        ✓ Plan activo
                                    </div>
                                )}

                                <p style={{ fontSize: '0.67rem', color: '#9ca3af', margin: '8px 0 16px', textAlign: 'center', lineHeight: 1.5 }}>
                                    Pago seguro por Stripe · Cancela cuando quieras
                                </p>
                            </div>

                            {/* Separador */}
                            <div style={{ height: 1, background: '#f3f4f6', margin: '0 24px' }} />

                            {/* Lista de features */}
                            <div style={{ padding: '16px 24px 24px' }}>
                                <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
                                    {plan.features.map((f, i) => (
                                        <li key={i} style={{ display: 'flex', gap: 10, fontSize: '0.83rem', color: '#374151', lineHeight: 1.4 }}>
                                            <span style={{ color: plan.color, fontWeight: 700, flexShrink: 0 }}>✓</span>
                                            {i === 0 && plan.id === 'pro' ? <strong>{f}</strong> : f}
                                        </li>
                                    ))}
                                    {plan.missing.map((f, i) => (
                                        <li key={`m${i}`} style={{ display: 'flex', gap: 10, fontSize: '0.82rem', color: '#9ca3af', lineHeight: 1.4 }}>
                                            <span style={{ flexShrink: 0 }}>✗</span>
                                            {f}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    );
                })}
            </div>

            <p style={{ textAlign: 'center', fontSize: '0.7rem', color: '#9ca3af', padding: '0 16px 32px', lineHeight: 1.7 }}>
                Facturas automáticas por email · Soporte: soporte@cuadernocampo.es
            </p>
        </div>
    );
}
