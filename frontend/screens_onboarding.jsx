// ── Screen: Datos de la Explotación — pantalla obligatoria para usuarios nuevos ──
// Se muestra justo después del LOPD si el titular no está rellenado.

function ScreenOnboarding({ currentUser, onComplete }) {
    const { useState } = React;
    const [form, setForm] = useState({
        titular: currentUser?.nombre || '',
        nif: '',
        municipio: '',
        provincia: '',
        cp: '',
        telefono: '',
        email: currentUser?.email || '',
        campana_activa: '2025/2026',
    });
    const [saving, setSaving] = useState(false);
    const [zoomField, setZoomField] = useState(null);

    const FIELDS = [
        ['titular',       'Titular',        'text',  'Nombre completo'],
        ['nif',           'NIF / CIF',       'text',  '12345678A'],
        ['municipio',     'Municipio',       'text',  'Santa Cruz de Mudela'],
        ['provincia',     'Provincia',       'text',  'Ciudad Real'],
        ['cp',            'Código postal',   'text',  '13730'],
        ['telefono',      'Teléfono',        'tel',   '600 000 000'],
        ['email',         'Email',           'email', 'titular@explotacion.es'],
        ['campana_activa','Campaña activa',  'text',  '2025/2026'],
    ];

    const save = async () => {
        if (!form.titular.trim()) { alert('El nombre del titular es obligatorio'); return; }
        setSaving(true);
        const res = await fetch('/api/explotacion', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(form),
            credentials: 'include',
        });
        setSaving(false);
        if (res.ok) onComplete(form.campana_activa);
    };

    return (
        <div style={{
            minHeight: '100vh',
            background: 'linear-gradient(160deg, #f0fdf4 0%, #ecfdf5 40%, #f0f9ff 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px 16px',
            overflowY: 'auto',
        }}>
            <div style={{ maxWidth: 480, width: '100%' }}>

                <div style={{ textAlign: 'center', marginBottom: 24 }}>
                    <div style={{ fontSize: 48, marginBottom: 8 }}>🏡</div>
                    <h1 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.4rem', color: '#111827', margin: 0 }}>
                        Datos de la Explotación
                    </h1>
                    <p style={{ color: '#6b7280', fontSize: '0.88rem', margin: '8px 0 0', lineHeight: 1.5 }}>
                        Identifícate como titular. Aparecerán en el PDF oficial del cuaderno.
                    </p>
                </div>

                <div style={{ background: '#fff', borderRadius: 20, padding: 24, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
                    {FIELDS.map(([k, l, t, ph]) => (
                        <div key={k} style={{ marginBottom: 14 }}>
                            <label className="field-label">{l}{k === 'titular' ? ' *' : ''}</label>
                            <input
                                type={t}
                                className="input-field"
                                value={form[k] || ''}
                                readOnly
                                placeholder={ph}
                                onClick={() => setZoomField({ key: k, label: l, type: t, placeholder: ph })}
                                style={{ cursor: 'pointer' }}
                            />
                        </div>
                    ))}
                    <button className="btn-primary" style={{ width: '100%', marginTop: 8 }} onClick={save} disabled={saving}>
                        {saving ? 'Guardando…' : '💾 Guardar datos'}
                    </button>
                </div>

            </div>

            {zoomField && (
                <FieldZoomOverlay
                    label={zoomField.label}
                    value={form[zoomField.key] || ''}
                    type={zoomField.type}
                    placeholder={zoomField.placeholder}
                    onConfirm={val => { setForm(f => ({ ...f, [zoomField.key]: val })); setZoomField(null); }}
                    onClose={() => setZoomField(null)}
                />
            )}
        </div>
    );
}
