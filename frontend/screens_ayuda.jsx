// ── Sistema de ayuda: guía de inicio + ayuda contextual por pantalla ──

// ── Contenido de ayuda por pantalla ──
const HELP_SCREENS = {
    inicio: {
        title: '🏡 Pantalla de inicio',
        intro: 'Desde aquí controlas todo: el tiempo, lo que hiciste últimamente y el acceso rápido a anotar.',
        steps: [
            {
                icon: '✏️',
                title: 'Botón ✏️ — Anotar actividad',
                desc: 'El botón verde ✏️ de la barra inferior es el más importante. Púlsalo para registrar cualquier actividad: tratamientos, riego, fertilización, labores, cosecha...',
            },
            {
                icon: '🎤',
                title: 'Habla que yo escribo',
                desc: 'En la pantalla de inicio hay dos opciones: "Rellénalo tú" (formularios) y "Habla que yo escribo". Con la segunda, di en voz alta lo que hiciste — "apliqué herbicida en el olivar" — y el cuaderno lo registra solo.',
            },
            {
                icon: '🌡️',
                title: 'Previsión del tiempo',
                desc: 'Muestra la previsión de los próximos días según tu municipio. Muy útil para planificar tratamientos y riegos.',
            },
            {
                icon: '📋',
                title: 'Últimas actividades',
                desc: 'Aparecen los últimos registros para que veas de un vistazo qué has hecho recientemente. Pulsa en uno para editarlo.',
            },
        ],
    },
    parcelas: {
        title: '🗺️ Mis parcelas',
        intro: 'Aquí registras todas tus parcelas SIGPAC. Sin parcelas no puedes anotar actividades correctamente.',
        steps: [
            {
                icon: '➕',
                title: '+ Nueva parcela',
                desc: 'Pulsa el botón "+ Nueva parcela" para añadir una. Necesitas la referencia SIGPAC: provincia, municipio, polígono, parcela y recinto.',
            },
            {
                icon: '🔍',
                title: 'Buscar en SIGPAC',
                desc: 'Dentro del formulario hay un buscador que conecta con el SIGPAC oficial. Selecciona provincia, municipio, polígono y parcela de los desplegables.',
            },
            {
                icon: '🌾',
                title: 'Cultivo de campaña',
                desc: 'Asigna el cultivo actual a cada parcela. Es obligatorio para el cuaderno oficial — el PDF debe reflejar qué se cultiva en cada recinto.',
            },
            {
                icon: '🗺️',
                title: 'Vista en el mapa',
                desc: 'El mapa muestra la ubicación de cada parcela. Pulsa sobre una para ver todos sus detalles y el historial de actividades asociadas.',
            },
        ],
    },
    historial: {
        title: '📋 Historial',
        intro: 'Todos tus registros en un solo sitio: tratamientos, riegos, labores, cosechas...',
        steps: [
            {
                icon: '🔍',
                title: 'Filtrar por tipo o fecha',
                desc: 'Usa los filtros de la parte superior para buscar registros por tipo de actividad, parcela concreta o rango de fechas.',
            },
            {
                icon: '✏️',
                title: 'Editar un registro',
                desc: 'Pulsa sobre cualquier registro de la lista para abrirlo y editarlo. También puedes eliminarlo desde ahí.',
            },
            {
                icon: '📄',
                title: 'Exportar el cuaderno',
                desc: 'Para descargar el PDF oficial, ve a Ajustes → Datos y exportación. El historial es la base de ese PDF.',
            },
        ],
    },
    mas: {
        title: '⚙️ Ajustes',
        intro: 'Configura los datos de tu explotación, los equipos y descarga el cuaderno oficial.',
        steps: [
            {
                icon: '🏡',
                title: 'Datos de la explotación (obligatorio)',
                desc: 'Rellena el nombre del titular, NIF, municipio y provincia. Son datos legales obligatorios que aparecen en el PDF oficial.',
            },
            {
                icon: '📄',
                title: 'Descargar PDF oficial',
                desc: 'En la pestaña "Datos y exportación" encontrarás el botón para descargar el Cuaderno de Explotación en PDF. Es el documento válido para inspecciones.',
            },
            {
                icon: '🚜',
                title: 'Equipos de aplicación',
                desc: 'Registra tus máquinas con número de registro ROMA y fecha de la última ITEAF. Es obligatorio para los tratamientos fitosanitarios.',
            },
            {
                icon: '👤',
                title: 'Aplicadores ROPO',
                desc: 'Añade los aplicadores con su número ROPO. Cada tratamiento debe tener un aplicador registrado con carnet vigente.',
            },
        ],
    },
};

// ── Slides para la guía de inicio ──
const QUICKSTART_SLIDES = [
    {
        id: 1,
        emoji: '🌿',
        gradient: 'linear-gradient(160deg, #00694c 0%, #008560 100%)',
        title: '¡Bienvenido a tu cuaderno!',
        desc: 'Registra aquí todo lo que haces en la finca: tratamientos, riegos, abonados, cosechas... y cumple con la ley sin papeles.',
        preview: null,
        action: null,
    },
    {
        id: 2,
        emoji: '🗺️',
        gradient: 'linear-gradient(160deg, #1e3a5f 0%, #1d4ed8 100%)',
        title: '1. Primero, añade tus parcelas',
        desc: 'Sin parcelas no puedes registrar actividades. Ve a "Parcelas", pulsa "+ Nueva parcela" y busca tu referencia SIGPAC.',
        preview: 'parcelas',
        action: 'parcelas',
        actionLabel: 'Ir a Parcelas →',
    },
    {
        id: 3,
        emoji: '✏️',
        gradient: 'linear-gradient(160deg, #3730a3 0%, #4f46e5 100%)',
        title: '2. Anota cada actividad',
        desc: 'Pulsa el botón ✏️ del centro de la barra inferior. Elige el tipo de actividad y rellena el formulario.',
        preview: 'anotar',
        action: null,
    },
    {
        id: 4,
        emoji: '🎤',
        gradient: 'linear-gradient(160deg, #9f1239 0%, #db2777 100%)',
        title: '3. O simplemente habla',
        desc: '"Hoy apliqué herbicida en el olivar, 2 litros por hectárea." El cuaderno entiende lenguaje natural y lo registra solo.',
        preview: 'voz',
        action: null,
    },
    {
        id: 5,
        emoji: '📄',
        gradient: 'linear-gradient(160deg, #78350f 0%, #b45309 100%)',
        title: '4. Descarga el PDF oficial',
        desc: 'Cuando necesites el cuaderno para inspección, ve a Ajustes → Datos y exportación → Descargar PDF.',
        preview: 'pdf',
        action: 'mas',
        actionLabel: 'Ir a Ajustes →',
    },
];

// ── Mini-UI previews para los slides ──
function SlidePreview({ type }) {
    const cardStyle = {
        width: '100%',
        maxWidth: 240,
        margin: '0 auto',
        borderRadius: 14,
        overflow: 'hidden',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        background: '#f8f9fb',
    };

    if (type === 'parcelas') {
        return (
            <div style={cardStyle}>
                <div style={{ background: 'linear-gradient(135deg,#111827,#1f2937)', padding: '10px 13px' }}>
                    <div style={{ color: '#fff', fontFamily: 'Manrope', fontWeight: 800, fontSize: '0.78rem' }}>🗺️ Mis Parcelas</div>
                </div>
                <div style={{ padding: '8px 10px' }}>
                    {[
                        { label: 'Olivar norte', info: '3,2 ha · Leñosos', icon: '🌳' },
                        { label: 'Viñedo sur', info: '1,8 ha · Leñosos', icon: '🍇' },
                        { label: 'Cereal este', info: '12,4 ha · Cereales', icon: '🌾' },
                    ].map((p, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '6px 0', borderBottom: i < 2 ? '1px solid #f3f4f6' : 'none' }}>
                            <div style={{ width: 28, height: 28, background: 'linear-gradient(135deg,#00694c,#008560)', borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, flexShrink: 0 }}>{p.icon}</div>
                            <div>
                                <div style={{ fontSize: '0.66rem', color: '#111827', fontWeight: 700, lineHeight: 1.2 }}>{p.label}</div>
                                <div style={{ fontSize: '0.58rem', color: '#6b7280' }}>{p.info}</div>
                            </div>
                        </div>
                    ))}
                    <div style={{ marginTop: 8, background: 'linear-gradient(135deg,#00694c,#008560)', borderRadius: 16, padding: '6px 10px', textAlign: 'center', color: '#fff', fontSize: '0.62rem', fontWeight: 700 }}>+ Nueva parcela</div>
                </div>
            </div>
        );
    }

    if (type === 'anotar') {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, maxWidth: 200 }}>
                    {[
                        { emoji: '🌿', label: 'Fitosanitario', bg: 'linear-gradient(135deg,#00694c,#008560)' },
                        { emoji: '💧', label: 'Riego', bg: 'linear-gradient(135deg,#0369a1,#0ea5e9)' },
                        { emoji: '🌱', label: 'Fertilización', bg: 'linear-gradient(135deg,#3730a3,#4f46e5)' },
                        { emoji: '🚜', label: 'Labor agrícola', bg: 'linear-gradient(135deg,#1e3a5f,#1d4ed8)' },
                    ].map((m, i) => (
                        <div key={i} style={{ background: m.bg, borderRadius: 12, padding: '10px 8px', textAlign: 'center', boxShadow: '0 4px 12px rgba(0,0,0,0.25)' }}>
                            <div style={{ fontSize: 20 }}>{m.emoji}</div>
                            <div style={{ color: '#fff', fontSize: '0.58rem', fontWeight: 700, marginTop: 3, lineHeight: 1.2 }}>{m.label}</div>
                        </div>
                    ))}
                </div>
                <div style={{ background: 'linear-gradient(135deg,#68dbae,#86f8c9)', borderRadius: '50%', width: 48, height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, boxShadow: '0 4px 16px rgba(0,105,76,0.5)' }}>✏️</div>
            </div>
        );
    }

    if (type === 'voz') {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                <div style={{ background: 'rgba(255,255,255,0.15)', borderRadius: 14, padding: '12px 16px', maxWidth: 230, backdropFilter: 'blur(4px)' }}>
                    <div style={{ color: 'rgba(255,255,255,0.92)', fontSize: '0.75rem', fontStyle: 'italic', lineHeight: 1.55, textAlign: 'center' }}>
                        "Hoy apliqué herbicida en el olivar, 2 litros por hectárea..."
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    {[10, 18, 26, 18, 10, 22, 14].map((h, i) => (
                        <div key={i} style={{ width: 3, height: h, background: 'rgba(255,255,255,0.75)', borderRadius: 2 }} />
                    ))}
                </div>
                <div style={{ background: '#dc2626', borderRadius: '50%', width: 50, height: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, boxShadow: '0 4px 16px rgba(220,38,38,0.55)' }}>🎤</div>
            </div>
        );
    }

    if (type === 'pdf') {
        return (
            <div style={cardStyle}>
                <div style={{ background: 'linear-gradient(135deg,#111827,#1f2937)', padding: '10px 13px' }}>
                    <div style={{ color: '#fff', fontFamily: 'Manrope', fontWeight: 800, fontSize: '0.78rem' }}>⚙️ Ajustes</div>
                </div>
                <div style={{ padding: '8px 10px' }}>
                    <div style={{ background: '#f0fdf4', borderRadius: 10, padding: '9px 10px', marginBottom: 7 }}>
                        <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#166534', marginBottom: 3 }}>📄 Exportar PDF oficial</div>
                        <div style={{ fontSize: '0.58rem', color: '#6b7280', marginBottom: 7 }}>Conforme a RD 1311/2012</div>
                        <div style={{ background: 'linear-gradient(135deg,#00694c,#008560)', borderRadius: 12, padding: '5px 10px', color: '#fff', fontSize: '0.6rem', fontWeight: 700, textAlign: 'center' }}>⬇ Descargar PDF</div>
                    </div>
                    <div style={{ background: '#f0f9ff', borderRadius: 10, padding: '9px 10px' }}>
                        <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#1e3a5f', marginBottom: 7 }}>📊 Exportar Excel</div>
                        <div style={{ background: 'linear-gradient(135deg,#1e3a5f,#1d4ed8)', borderRadius: 12, padding: '5px 10px', color: '#fff', fontSize: '0.6rem', fontWeight: 700, textAlign: 'center' }}>⬇ Descargar Excel</div>
                    </div>
                </div>
            </div>
        );
    }

    return null;
}

// ── QuickStartModal — carousel de guía de inicio ──
function QuickStartModal({ onClose, onNavigate }) {
    const { useState, useRef } = React;
    const [current, setCurrent] = useState(0);
    const touchStartX = useRef(null);

    const slide = QUICKSTART_SLIDES[current];
    const isLast = current === QUICKSTART_SLIDES.length - 1;

    const next = () => { if (isLast) { onClose(); return; } setCurrent(c => c + 1); };
    const prev = () => setCurrent(c => Math.max(0, c - 1));

    const handleTouchStart = (e) => { touchStartX.current = e.touches[0].clientX; };
    const handleTouchEnd = (e) => {
        if (touchStartX.current === null) return;
        const diff = touchStartX.current - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 50) { if (diff > 0) next(); else prev(); }
        touchStartX.current = null;
    };

    const goAndClose = (screenId) => { onClose(); if (onNavigate && screenId) onNavigate(screenId); };

    return (
        <div
            style={{ position: 'fixed', inset: 0, zIndex: 300, background: slide.gradient, display: 'flex', flexDirection: 'column', animation: 'fadeIn 0.25s ease' }}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
        >
            {/* Botón saltar */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '52px 20px 0' }}>
                <button onClick={onClose} style={{
                    background: 'rgba(255,255,255,0.18)', border: 'none',
                    borderRadius: 20, padding: '6px 14px',
                    color: '#fff', fontSize: '0.8rem', fontWeight: 600,
                    cursor: 'pointer', fontFamily: 'Work Sans, sans-serif',
                }}>Saltar ✕</button>
            </div>

            {/* Contenido central */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '16px 28px', textAlign: 'center', gap: 24 }}>
                {slide.preview ? (
                    <SlidePreview type={slide.preview} />
                ) : (
                    <div style={{ fontSize: 72, filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.3))' }}>{slide.emoji}</div>
                )}
                <div>
                    <h2 style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 800, fontSize: '1.5rem', color: '#fff', margin: '0 0 10px', lineHeight: 1.2, textShadow: '0 2px 8px rgba(0,0,0,0.2)' }}>
                        {slide.title}
                    </h2>
                    <p style={{ color: 'rgba(255,255,255,0.88)', fontSize: '0.95rem', lineHeight: 1.65, margin: 0, maxWidth: 320 }}>
                        {slide.desc}
                    </p>
                </div>
                {slide.action && (
                    <button onClick={() => goAndClose(slide.action)} style={{
                        background: 'rgba(255,255,255,0.18)', border: '1.5px solid rgba(255,255,255,0.38)',
                        borderRadius: 20, padding: '10px 20px',
                        color: '#fff', fontWeight: 700, fontSize: '0.88rem',
                        cursor: 'pointer', fontFamily: 'Work Sans, sans-serif',
                    }}>{slide.actionLabel}</button>
                )}
            </div>

            {/* Dots indicadores */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: 6, paddingBottom: 12 }}>
                {QUICKSTART_SLIDES.map((_, i) => (
                    <button key={i} onClick={() => setCurrent(i)} style={{
                        width: i === current ? 20 : 6, height: 6, borderRadius: 3, border: 'none',
                        background: i === current ? '#fff' : 'rgba(255,255,255,0.32)',
                        cursor: 'pointer', padding: 0, transition: 'all 0.22s',
                    }} />
                ))}
            </div>

            {/* Botones navegación */}
            <div style={{ display: 'flex', gap: 10, padding: '0 20px 48px' }}>
                {current > 0 && (
                    <button onClick={prev} style={{
                        flex: 1, background: 'rgba(255,255,255,0.14)', border: '1.5px solid rgba(255,255,255,0.28)',
                        borderRadius: 20, padding: '14px', color: '#fff', fontWeight: 700, fontSize: '0.9rem',
                        cursor: 'pointer', fontFamily: 'Work Sans, sans-serif',
                    }}>← Anterior</button>
                )}
                <button onClick={next} style={{
                    flex: 2, background: 'rgba(255,255,255,0.95)', border: 'none',
                    borderRadius: 20, padding: '14px', color: '#111827', fontWeight: 800, fontSize: '0.95rem',
                    cursor: 'pointer', fontFamily: 'Manrope, sans-serif',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.22)',
                }}>
                    {isLast ? '¡Empezar! 🚀' : 'Siguiente →'}
                </button>
            </div>
        </div>
    );
}

// ── HelpModal — ayuda contextual por pantalla ──
function HelpModal({ screenId, onClose }) {
    const content = HELP_SCREENS[screenId];
    if (!content) return null;

    return (
        <div className="overlay" onClick={onClose}>
            <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom: 40 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                    <div style={{ flex: 1 }}>
                        <h3 style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 800, fontSize: '1.1rem', margin: 0 }}>{content.title}</h3>
                        <p style={{ fontSize: '0.82rem', color: '#6b7280', margin: '4px 0 0', lineHeight: 1.5 }}>{content.intro}</p>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280', flexShrink: 0, marginLeft: 12, padding: 0 }}>✕</button>
                </div>

                <div style={{ borderTop: '1px solid #f3f4f6', marginTop: 16, paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {content.steps.map((step, i) => (
                        <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                            <div style={{
                                width: 38, height: 38, borderRadius: '50%',
                                background: 'linear-gradient(135deg,#00694c,#008560)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: 17, flexShrink: 0,
                                boxShadow: '0 2px 8px rgba(0,105,76,0.25)',
                            }}>{step.icon}</div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 700, fontSize: '0.88rem', color: '#111827', marginBottom: 2 }}>{step.title}</div>
                                <div style={{ fontSize: '0.8rem', color: '#6b7280', lineHeight: 1.6 }}>{step.desc}</div>
                            </div>
                        </div>
                    ))}
                </div>

                <button onClick={onClose} className="btn-primary" style={{ width: '100%', marginTop: 22, minHeight: 48, fontSize: '0.95rem' }}>
                    ¡Entendido!
                </button>
            </div>
        </div>
    );
}

// ── HelpButton — botón "?" reutilizable para cabeceras ──
function HelpButton({ screenId, style }) {
    const [show, setShow] = React.useState(false);
    return (
        <>
            <button
                onClick={() => setShow(true)}
                title="Ayuda"
                style={{
                    background: 'rgba(255,255,255,0.14)', border: 'none',
                    borderRadius: '50%', width: 32, height: 32,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff', fontSize: '0.85rem', fontWeight: 800,
                    cursor: 'pointer', fontFamily: 'Manrope, sans-serif',
                    flexShrink: 0,
                    ...(style || {}),
                }}
            >?</button>
            {show && <HelpModal screenId={screenId} onClose={() => setShow(false)} />}
        </>
    );
}
