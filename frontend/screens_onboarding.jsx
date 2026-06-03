// ── Screen: Onboarding wizard para nuevos usuarios ──
// Aparece cuando el usuario no tiene parcelas ni datos de explotación configurados.

function ScreenOnboarding({ currentUser, onComplete }) {
    const { useState } = React;
    const [step, setStep] = useState(1); // 1 = explotación, 2 = primera parcela, 3 = listo
    const [saving, setSaving] = useState(false);

    // Paso 1: datos de la explotación
    const [expl, setExpl] = useState({
        titular: currentUser?.nombre || '',
        nif: '',
        municipio: '',
        provincia: '',
        cp: '',
    });

    // Paso 2: primera parcela (simplificado)
    const [parc, setParc] = useState({
        nombre_finca: '',
        superficie_ha: '',
        municipio_nombre: '',
        sistema_explotacion: 'Secano',
    });

    const setE = (k, v) => setExpl(x => ({ ...x, [k]: v }));
    const setP = (k, v) => setParc(x => ({ ...x, [k]: v }));

    const saveExpl = async () => {
        if (!expl.titular.trim()) { alert('Introduce el nombre del titular'); return; }
        setSaving(true);
        await fetch('/api/explotacion', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(expl),
            credentials: 'include',
        });
        setSaving(false);
        setStep(2);
    };

    const saveParc = async () => {
        if (!parc.nombre_finca.trim()) { alert('Introduce un nombre para la parcela'); return; }
        if (!parc.superficie_ha || isNaN(parseFloat(parc.superficie_ha))) { alert('Introduce la superficie en hectáreas'); return; }
        setSaving(true);
        const res = await fetch('/api/parcelas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...parc,
                superficie_ha: parseFloat(String(parc.superficie_ha).replace(',', '.')),
                comunidad: 'Castilla-La Mancha',
            }),
            credentials: 'include',
        });
        setSaving(false);
        if (!res.ok) { const d = await res.json().catch(() => ({})); alert(d.error || 'Error al guardar la parcela'); return; }
        setStep(3);
    };

    const STEP_LABELS = ['Explotación', 'Parcela', 'Listo'];

    return (
        <div style={{
            minHeight: '100vh',
            background: 'linear-gradient(160deg, #f0fdf4 0%, #ecfdf5 40%, #f0f9ff 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px 16px',
        }}>
            <div style={{ maxWidth: 440, width: '100%' }}>
                {/* Logo / título */}
                <div style={{ textAlign: 'center', marginBottom: 28 }}>
                    <div style={{ fontSize: 52, marginBottom: 8 }}>🌿</div>
                    <h1 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.5rem', color: '#111827', margin: 0 }}>
                        ¡Bienvenido al Cuaderno!
                    </h1>
                    <p style={{ color: '#6b7280', fontSize: '0.88rem', margin: '8px 0 0' }}>
                        Vamos a configurar tu explotación en 2 pasos.
                    </p>
                </div>

                {/* Barra de progreso */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 28 }}>
                    {STEP_LABELS.map((label, i) => {
                        const num = i + 1;
                        const done = step > num;
                        const active = step === num;
                        return (
                            <React.Fragment key={num}>
                                <div style={{ flex: 1, textAlign: 'center' }}>
                                    <div style={{
                                        width: 32, height: 32, borderRadius: '50%', margin: '0 auto 4px',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        background: done ? '#10b981' : active ? 'var(--primary)' : '#e5e7eb',
                                        color: (done || active) ? '#fff' : '#9ca3af',
                                        fontSize: done ? 16 : '0.85rem',
                                        fontWeight: 700,
                                        transition: 'all 0.3s',
                                    }}>
                                        {done ? '✓' : num}
                                    </div>
                                    <div style={{ fontSize: '0.68rem', color: active ? 'var(--primary)' : '#9ca3af', fontWeight: active ? 700 : 400 }}>
                                        {label}
                                    </div>
                                </div>
                                {i < STEP_LABELS.length - 1 && (
                                    <div style={{ flex: 2, height: 2, background: step > i + 1 ? '#10b981' : '#e5e7eb', transition: 'background 0.3s', marginBottom: 20 }} />
                                )}
                            </React.Fragment>
                        );
                    })}
                </div>

                {/* ── Paso 1: Explotación ── */}
                {step === 1 && (
                    <div style={{ background: '#fff', borderRadius: 20, padding: 24, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
                        <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '1.1rem', color: '#111827', margin: '0 0 6px' }}>
                            Datos de la explotación
                        </h2>
                        <p style={{ color: '#6b7280', fontSize: '0.82rem', margin: '0 0 20px' }}>
                            Aparecerán en el PDF oficial del cuaderno.
                        </p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                            <div>
                                <label className="field-label">Titular *</label>
                                <input className="input-field" type="text" placeholder="Juan García Pérez"
                                    value={expl.titular} onChange={e => setE('titular', e.target.value)} />
                            </div>
                            <div>
                                <label className="field-label">NIF / CIF</label>
                                <input className="input-field" type="text" placeholder="12345678A"
                                    value={expl.nif} onChange={e => setE('nif', e.target.value)} />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                                <div>
                                    <label className="field-label">Municipio</label>
                                    <input className="input-field" type="text" placeholder="Santa Cruz de Mudela"
                                        value={expl.municipio} onChange={e => setE('municipio', e.target.value)} />
                                </div>
                                <div>
                                    <label className="field-label">Provincia</label>
                                    <input className="input-field" type="text" placeholder="Ciudad Real"
                                        value={expl.provincia} onChange={e => setE('provincia', e.target.value)} />
                                </div>
                            </div>
                            <button className="btn-primary" onClick={saveExpl} disabled={saving} style={{ marginTop: 4 }}>
                                {saving ? 'Guardando…' : 'Siguiente →'}
                            </button>
                        </div>
                    </div>
                )}

                {/* ── Paso 2: Primera parcela ── */}
                {step === 2 && (
                    <div style={{ background: '#fff', borderRadius: 20, padding: 24, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
                        <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '1.1rem', color: '#111827', margin: '0 0 6px' }}>
                            Añade tu primera parcela
                        </h2>
                        <p style={{ color: '#6b7280', fontSize: '0.82rem', margin: '0 0 20px' }}>
                            Puedes añadir más parcelas y los datos SIGPAC después.
                        </p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                            <div>
                                <label className="field-label">Nombre de la finca *</label>
                                <input className="input-field" type="text" placeholder="La Retama, Parcela Norte…"
                                    value={parc.nombre_finca} onChange={e => setP('nombre_finca', e.target.value)} />
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                                <div>
                                    <label className="field-label">Superficie (ha) *</label>
                                    <input className="input-field" type="text" inputMode="decimal" placeholder="4.5"
                                        value={parc.superficie_ha} onChange={e => setP('superficie_ha', e.target.value)} />
                                </div>
                                <div>
                                    <label className="field-label">Municipio</label>
                                    <input className="input-field" type="text" placeholder={expl.municipio || 'Tu municipio'}
                                        value={parc.municipio_nombre} onChange={e => setP('municipio_nombre', e.target.value)} />
                                </div>
                            </div>
                            <div>
                                <label className="field-label">Sistema de cultivo</label>
                                <select className="input-field" value={parc.sistema_explotacion} onChange={e => setP('sistema_explotacion', e.target.value)}>
                                    {['Secano', 'Regadío', 'Mixto'].map(s => <option key={s}>{s}</option>)}
                                </select>
                            </div>
                            <div style={{ display: 'flex', gap: 10 }}>
                                <button className="btn-ghost" onClick={() => setStep(3)} style={{ flex: 1, fontSize: '0.85rem' }}>
                                    Añadir después
                                </button>
                                <button className="btn-primary" onClick={saveParc} disabled={saving} style={{ flex: 2 }}>
                                    {saving ? 'Guardando…' : 'Guardar parcela →'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* ── Paso 3: Listo ── */}
                {step === 3 && (
                    <div style={{ background: '#fff', borderRadius: 20, padding: 28, boxShadow: '0 4px 24px rgba(0,0,0,0.08)', textAlign: 'center' }}>
                        <div style={{ fontSize: 56, marginBottom: 12 }}>🎉</div>
                        <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.2rem', color: '#111827', margin: '0 0 8px' }}>
                            ¡Tu cuaderno está listo!
                        </h2>
                        <p style={{ color: '#6b7280', fontSize: '0.88rem', margin: '0 0 24px', lineHeight: 1.6 }}>
                            Ya puedes registrar tratamientos, fertilización, labores y más. Cuando necesites el PDF oficial, lo tienes en la pantalla de inicio.
                        </p>
                        <button className="btn-primary" onClick={onComplete} style={{ width: '100%' }}>
                            Ir al cuaderno →
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
