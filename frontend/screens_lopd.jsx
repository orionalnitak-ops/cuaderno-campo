// ── Screen: LOPD / Bienvenida — Stitch "Editorial Agronomy" design ──
// Visual reference: Stitch project 2531086873277236561, screen 5b61a1b2936f4e0292fb2a0933effbc4
function ScreenLopd({ onAccept }) {
    const [showModal, setShowModal] = React.useState(false);

    return (
        <div style={{
            minHeight: '100vh',
            background: 'var(--surface)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px 20px',
            overflowY: 'auto',
        }}>
            <div style={{
                background: 'var(--surface-container-lowest)',
                borderRadius: 'var(--radius-xl)',
                width: '100%',
                maxWidth: 440,
                overflow: 'hidden',
                boxShadow: 'var(--shadow-ambient)',
            }}>
                {/* Top card content */}
                <div style={{ padding: '32px 24px 24px', textAlign: 'center' }}>
                    {/* Logo: circular tractor icon — exact Stitch style */}
                    <div className="lopd-logo" style={{ animation: 'pulse 2.5s ease-in-out infinite' }}>
                        🚜
                    </div>

                    <h1 style={{
                        fontFamily: 'var(--font-heading)',
                        fontWeight: 800,
                        fontSize: '1.75rem',
                        color: 'var(--on-background)',
                        margin: '0 0 4px',
                        letterSpacing: '-0.02em',
                    }}>
                        Cuaderno de Campo
                    </h1>
                    <p style={{
                        color: 'var(--on-surface-variant)',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        margin: '0 0 20px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                    }}>
                        Gestión Agrícola Inteligente
                    </p>

                    {/* Hero image — exact Stitch: campo rectangular con overlay */}
                    <div style={{
                        width: '100%',
                        aspectRatio: '16/9',
                        background: 'linear-gradient(160deg, #1a4731 0%, #2d7a53 50%, #4caf7a 100%)',
                        borderRadius: 'var(--radius-xl)',
                        marginBottom: 20,
                        position: 'relative',
                        overflow: 'hidden',
                        display: 'flex',
                        alignItems: 'flex-end',
                    }}>
                        {/* Field texture */}
                        <div style={{
                            position: 'absolute', inset: 0,
                            background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0) 0px, rgba(0,0,0,0) 18px, rgba(0,0,0,0.04) 18px, rgba(0,0,0,0.04) 19px)',
                        }} />
                        {/* Overlay badge */}
                        <div style={{
                            padding: '10px 14px',
                            background: 'linear-gradient(to top, rgba(0,0,0,0.65), transparent)',
                            width: '100%',
                        }}>
                            <span style={{
                                background: 'rgba(104,219,174,0.25)',
                                color: 'var(--primary-fixed)',
                                fontSize: '0.72rem',
                                fontWeight: 700,
                                letterSpacing: '0.06em',
                                padding: '3px 10px',
                                borderRadius: 'var(--radius-full)',
                            }}>
                                Versión 2025/2026
                            </span>
                        </div>
                    </div>

                    {/* Privacy row — icon + text (Stitch style) */}
                    <div className="lopd-privacy-row" style={{ borderBottom: 'none', paddingBottom: 0 }}>
                        <div className="lopd-privacy-icon">🔒</div>
                        <div style={{ flex: 1, textAlign: 'left' }}>
                            <p style={{ fontSize: '0.84rem', color: 'var(--on-surface)', lineHeight: 1.65, margin: 0 }}>
                                Cumplimos con la <strong>LOPD</strong> y <strong>RGPD</strong>. Tus datos de explotación y parcelas
                                están almacenados únicamente en este dispositivo. Solo tú tienes acceso a ellos.
                            </p>
                        </div>
                    </div>
                </div>

                {/* CTA section */}
                <div style={{ padding: '0 24px 28px' }}>
                    <button className="btn-primary" style={{ width: '100%', marginBottom: 14 }} onClick={onAccept}>
                        Acepto y continuar →
                    </button>
                    <button onClick={() => setShowModal(true)} style={{
                        background: 'none', border: 'none',
                        color: 'var(--primary)',
                        fontSize: '0.84rem', fontWeight: 600,
                        cursor: 'pointer', width: '100%',
                        textAlign: 'center', padding: '4px',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                    }}>
                        Más información ↗
                    </button>
                    <p style={{
                        textAlign: 'center',
                        fontSize: '0.65rem',
                        color: 'var(--outline)',
                        marginTop: 18, marginBottom: 0,
                        letterSpacing: '0.05em',
                        textTransform: 'uppercase',
                    }}>
                        Editorial Agronomy Systems · 2025
                    </p>
                </div>
            </div>

            {showModal && <PrivacyModal onClose={() => setShowModal(false)} />}
        </div>
    );
}

function PrivacyModal({ onClose }) {
    return (
        <div className="overlay" style={{ alignItems: 'center', justifyContent: 'center' }} onClick={onClose}>
            <div style={{
                background: 'var(--surface-container-lowest)',
                borderRadius: 'var(--radius-xl)',
                padding: '28px 24px',
                maxWidth: 540,
                width: 'calc(100% - 32px)',
                maxHeight: '88vh',
                overflowY: 'auto',
                animation: 'scaleIn 0.2s ease',
                boxShadow: 'var(--shadow-ambient)',
            }} onClick={e => e.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                    <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.1rem', margin: 0 }}>
                        🔒 Política de Privacidad
                    </h2>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--on-surface-variant)', padding: 4 }}>✕</button>
                </div>

                {[
                    ['1. Responsable del tratamiento', 'El titular de la explotación agrícola registrado en esta aplicación es el responsable del tratamiento de sus propios datos personales y de los de su explotación.'],
                    ['2. Finalidad del tratamiento', 'Los datos se tratan exclusivamente para el cumplimiento de la obligación legal de llevar un cuaderno de explotación agrícola conforme al Real Decreto 1311/2012 y normativa aplicable de la PAC.'],
                    ['3. Derechos ARCO', 'Tiene derecho a acceder, rectificar, suprimir, limitar, oponerse al tratamiento y a la portabilidad de sus datos. Puede ejercerlos en Más → Ajustes o eliminando la base de datos.'],
                    ['4. Período de conservación', 'Los datos se conservan mientras mantenga la aplicación. El cuaderno debe conservarse un mínimo de 3 años tras la campaña según normativa PAC.'],
                    ['5. Transferencias internacionales', 'No se realizan transferencias. Toda la información se almacena localmente en este dispositivo o servidor.'],
                    ['6. Base legal', 'La base legal es el cumplimiento de una obligación legal (art. 6.1.c RGPD) derivada del RD 1311/2012 sobre uso sostenible de productos fitosanitarios.'],
                ].map(([title, text]) => (
                    <div key={title} className="lopd-privacy-row">
                        <div className="lopd-privacy-icon">📋</div>
                        <div>
                            <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '0.85rem', color: 'var(--on-background)', marginBottom: 4 }}>{title}</div>
                            <p style={{ fontSize: '0.82rem', lineHeight: 1.7, color: 'var(--on-surface-variant)', margin: 0 }}>{text}</p>
                        </div>
                    </div>
                ))}

                <button className="btn-primary" style={{ width: '100%', marginTop: 20 }} onClick={onClose}>
                    Cerrar
                </button>
            </div>
        </div>
    );
}
