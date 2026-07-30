// screens_cumplimiento.jsx — "Revisión del cuaderno": semáforo de cumplimiento.
//
// Pantalla de SOLO LECTURA. No pide ni un dato nuevo: todo sale de lo que el
// agricultor ya anotó. Ver spec/features/011-revision-cuaderno/spec.md.

const CUMPL_COLORES = {
    verde:   { fg: '#00694c', bg: '#d1fae5', chip: 'chip-green' },
    naranja: { fg: '#b45309', bg: '#fef3c7', chip: 'chip-grey' },
    rojo:    { fg: 'var(--tertiary)', bg: 'var(--tertiary-fixed)', chip: 'chip-red' },
};

const CUMPL_ESTADO = {
    ok:        { chip: 'chip-green', label: 'En orden',   icon: '✅' },
    aviso:     { chip: 'chip-grey',  label: 'Revisar',    icon: '⚠️' },
    critico:   { chip: 'chip-red',   label: 'Importante', icon: '❗' },
    no_aplica: { chip: 'chip-grey',  label: 'No aplica',  icon: '➖' },
};

// Anillo de progreso. SVG inline: sin dependencias y funciona offline.
function CumplAnillo({ porcentaje, color }) {
    const R = 54, C = 2 * Math.PI * R;
    const c = CUMPL_COLORES[color] || CUMPL_COLORES.naranja;
    return (
        <svg width="140" height="140" viewBox="0 0 140 140" aria-hidden="true">
            <circle cx="70" cy="70" r={R} fill="none" stroke={c.bg} strokeWidth="12" />
            <circle
                cx="70" cy="70" r={R} fill="none" stroke={c.fg} strokeWidth="12"
                strokeLinecap="round" strokeDasharray={C}
                strokeDashoffset={C * (1 - Math.max(0, Math.min(100, porcentaje)) / 100)}
                transform="rotate(-90 70 70)"
                style={{ transition: 'stroke-dashoffset 0.6s ease' }} />
            <text x="70" y="70" textAnchor="middle" dominantBaseline="central"
                style={{
                    fontFamily: 'var(--font-heading)', fontWeight: 800,
                    fontSize: '2rem', fill: c.fg, letterSpacing: '-0.03em',
                }}>{porcentaje}%</text>
        </svg>
    );
}

function CumplBloque({ bloque, abierto, onToggle, onArreglar }) {
    const est = CUMPL_ESTADO[bloque.estado] || CUMPL_ESTADO.aviso;
    const tieneDetalle = bloque.items.length > 0;

    return (
        <div className="card" style={{ marginBottom: 10 }}>
            <div
                onClick={tieneDetalle ? onToggle : undefined}
                style={{ padding: '14px 16px', cursor: tieneDetalle ? 'pointer' : 'default' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <span style={{ fontSize: '1.05rem' }}>{est.icon}</span>
                    <span style={{
                        fontFamily: 'var(--font-heading)', fontWeight: 700,
                        fontSize: '0.95rem', flex: 1, minWidth: 0,
                    }}>{bloque.titulo}</span>
                    <span className={`chip ${est.chip}`}>{est.label}</span>
                </div>
                <div style={{
                    fontSize: '0.82rem', color: 'var(--on-surface-variant)',
                    lineHeight: 1.45, paddingLeft: 28,
                }}>
                    {bloque.mensaje}
                    {tieneDetalle && (
                        <span style={{ color: 'var(--primary)', fontWeight: 700, marginLeft: 6 }}>
                            {abierto ? 'ocultar ▲' : 'ver detalle ▼'}
                        </span>
                    )}
                </div>
            </div>

            {abierto && tieneDetalle && (
                <div style={{ borderTop: '1px solid var(--outline-variant)', padding: '12px 16px' }}>
                    {bloque.items.map(it => (
                        <div key={it.clave} style={{
                            display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 10,
                        }}>
                            <span style={{
                                width: 8, height: 8, borderRadius: '50%', marginTop: 6, flexShrink: 0,
                                background: it.severidad === 'critico'
                                    ? 'var(--tertiary)' : '#b45309',
                            }} />
                            <div style={{ minWidth: 0 }}>
                                <div style={{ fontWeight: 600, fontSize: '0.86rem' }}>{it.etiqueta}</div>
                                <div style={{
                                    fontSize: '0.78rem', color: 'var(--on-surface-variant)', lineHeight: 1.4,
                                }}>{it.detalle}</div>
                            </div>
                        </div>
                    ))}

                    {bloque.items_truncados > 0 && (
                        <div style={{
                            fontSize: '0.78rem', color: 'var(--on-surface-variant)',
                            fontStyle: 'italic', marginBottom: 10,
                        }}>y {bloque.items_truncados} más…</div>
                    )}

                    {bloque.por_que && (
                        <div style={{
                            background: 'var(--surface-container-low)', borderRadius: 'var(--radius-lg)',
                            padding: '10px 12px', fontSize: '0.78rem',
                            color: 'var(--on-surface-variant)', lineHeight: 1.5, marginBottom: 10,
                        }}>
                            <strong>Por qué importa: </strong>{bloque.por_que}
                        </div>
                    )}

                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '0.8rem', flex: 1, minWidth: 140 }}>{bloque.accion}</span>
                        {onArreglar && (
                            <button className="btn-ghost" onClick={onArreglar}
                                style={{ whiteSpace: 'nowrap' }}>Arreglar ahora →</button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

// Tarjeta de entrada a la pantalla. Vive en Ajustes. Título fijo: el veredicto
// ("Te falta bastante") queda para la pantalla de detalle, donde va acompañado
// del anillo y del descargo que lo ponen en contexto.
function CumplTarjeta({ onNavigate }) {
    const [d, setD] = React.useState(null);

    React.useEffect(() => {
        fetch('/api/cumplimiento', { credentials: 'include' })
            .then(r => r.ok ? r.json() : { ok: false })
            .then(x => { if (x.ok) setD(x.data); })
            .catch(() => {});   // si falla no se pinta nada: no puede romper Ajustes
    }, []);

    if (!d || !onNavigate) return null;
    const c = CUMPL_COLORES[d.color] || CUMPL_COLORES.naranja;

    return (
        <div
            onClick={() => onNavigate('cumplimiento')}
            style={{
                background: 'var(--surface-container-lowest)',
                borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-card)',
                borderLeft: `4px solid ${c.fg}`, padding: '14px 16px',
                display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer',
            }}>
            <div style={{
                fontFamily: 'var(--font-heading)', fontWeight: 800,
                fontSize: '1.6rem', lineHeight: 1, flexShrink: 0, color: c.fg,
            }}>{d.porcentaje}%</div>
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                    fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '0.92rem',
                }}>Revisar cuaderno</div>
                <div style={{
                    fontSize: '0.78rem', color: 'var(--on-surface-variant)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>{d.subtitulo}</div>
            </div>
            <span style={{ color: 'var(--outline)', fontSize: 20, flexShrink: 0 }}>›</span>
        </div>
    );
}

function ScreenCumplimiento({ campana, onNavigate, onOpenForm }) {
    const [data, setData] = React.useState(null);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState('');
    const [abierto, setAbierto] = React.useState(null);

    React.useEffect(() => {
        setLoading(true);
        fetch('/api/cumplimiento', { credentials: 'include' })
            .then(r => r.json())
            .then(d => {
                if (d.ok) setData(d.data);
                else setError(d.error || 'No se pudo calcular el estado del cuaderno');
                setLoading(false);
            })
            .catch(() => {
                setError('Sin conexión. Esta pantalla necesita conectarse para revisar tu cuaderno.');
                setLoading(false);
            });
    }, [campana]);

    const irA = (destino) => {
        if (!destino) return null;
        if (destino.form && onOpenForm) return () => onOpenForm(destino.form);
        if (destino.screen && onNavigate) return () => onNavigate(destino.screen, destino.section);
        return null;
    };

    if (loading) {
        return (
            <div style={{ textAlign: 'center', padding: '80px 24px', color: 'var(--outline)' }}>
                Revisando tu cuaderno…
            </div>
        );
    }

    if (error || !data) {
        return (
            <div style={{ textAlign: 'center', padding: '60px 24px', color: 'var(--outline)' }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>🚦</div>
                <p style={{
                    fontFamily: 'var(--font-heading)', fontWeight: 700,
                    color: 'var(--on-surface)', margin: '0 0 6px',
                }}>No se pudo revisar</p>
                <p style={{ fontSize: '0.85rem', margin: 0 }}>{error}</p>
            </div>
        );
    }

    const c = CUMPL_COLORES[data.color] || CUMPL_COLORES.naranja;
    const puntuables   = data.bloques.filter(b => !b.informativo);
    const informativos = data.bloques.filter(b => b.informativo && b.afectados > 0);

    return (
        <div style={{ paddingBottom: 24 }}>
            <div className="hero-header" style={{
                display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
            }}>
                <div style={{ position: 'relative', zIndex: 1 }}>
                    <h2 style={{
                        margin: 0, color: '#fff', fontSize: '1.3rem',
                        fontFamily: 'var(--font-heading)', fontWeight: 800,
                    }}>Revisión del cuaderno</h2>
                    <p style={{
                        margin: '4px 0 0', color: 'rgba(255,255,255,0.85)', fontSize: '0.82rem',
                    }}>Campaña {data.campana}</p>
                </div>
                <div style={{ position: 'relative', zIndex: 1 }}>
                    <HelpButton screenId="cumplimiento" />
                </div>
            </div>

            <div style={{ maxWidth: 600, margin: '0 auto', padding: '20px 12px 0' }}>
                {/* ══ SEMÁFORO ══ */}
                <div className="card" style={{ padding: '24px 16px', textAlign: 'center', marginBottom: 8 }}>
                    <CumplAnillo porcentaje={data.porcentaje} color={data.color} />
                    <div style={{
                        fontFamily: 'var(--font-heading)', fontWeight: 800,
                        fontSize: '1.15rem', color: c.fg, marginTop: 8,
                    }}>{data.titulo}</div>
                    <div style={{
                        fontSize: '0.85rem', color: 'var(--on-surface-variant)', marginTop: 4,
                    }}>{data.subtitulo}</div>
                </div>

                <p style={{
                    fontSize: '0.72rem', color: 'var(--outline)', textAlign: 'center',
                    lineHeight: 1.5, margin: '0 8px 20px',
                }}>{data.descargo}</p>

                {/* ══ RESUMEN ══ */}
                <div className="responsive-grid cols-4" style={{ marginBottom: 20 }}>
                    <div className="stat-card">
                        <div className="stat-label">Importantes</div>
                        <div className="stat-value" style={{
                            color: data.resumen.criticos ? 'var(--tertiary)' : 'var(--primary)',
                        }}>{data.resumen.criticos}</div>
                        <div className="stat-sub">a corregir cuanto antes</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">Avisos</div>
                        <div className="stat-value">{data.resumen.avisos}</div>
                        <div className="stat-sub">conviene repasarlos</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">Correctas</div>
                        <div className="stat-value" style={{ color: 'var(--primary)' }}>
                            {data.resumen.bloques_ok}
                        </div>
                        <div className="stat-sub">comprobaciones en orden</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-label">No aplican</div>
                        <div className="stat-value">{data.resumen.bloques_no_aplica}</div>
                        <div className="stat-sub">no cuentan en el %</div>
                    </div>
                </div>

                {/* ══ COMPROBACIONES ══ */}
                {puntuables.map(b => (
                    <CumplBloque
                        key={b.id} bloque={b} abierto={abierto === b.id}
                        onToggle={() => setAbierto(abierto === b.id ? null : b.id)}
                        onArreglar={irA(b.destino)} />
                ))}

                {/* ══ INFORMATIVOS ══ */}
                {informativos.length > 0 && (
                    <div style={{ marginTop: 24 }}>
                        <div className="date-header" style={{ padding: '8px 4px' }}>
                            AVISOS OPERATIVOS · NO CUENTAN EN EL PORCENTAJE
                        </div>
                        {informativos.map(b => (
                            <CumplBloque
                                key={b.id} bloque={b} abierto={abierto === b.id}
                                onToggle={() => setAbierto(abierto === b.id ? null : b.id)}
                                onArreglar={irA(b.destino)} />
                        ))}
                    </div>
                )}

                <p style={{
                    fontSize: '0.72rem', color: 'var(--outline)', textAlign: 'center',
                    marginTop: 20,
                }}>Recalculado ahora mismo con lo que tienes anotado.</p>
            </div>
        </div>
    );
}
