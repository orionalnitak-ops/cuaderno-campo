// ── Screen: primeros datos — pantalla obligatoria para usuarios nuevos ──
// Se muestra justo después del LOPD si el titular no está rellenado.
//
// Feature 028: pedía ocho campos (NIF, CP, teléfono…) antes de dejar ver nada,
// y 3 de cada 7 personas que entraron a probar no pasaron de aquí. Ahora pide
// tres, y cada uno dice para qué sirve. El resto se rellena cuando hace falta,
// en Ajustes → Explotación.

function ScreenOnboarding({ currentUser, onComplete }) {
    const { useState } = React;
    const [form, setForm] = useState({
        titular: currentUser?.nombre || '',
        municipio: '',
        campana_activa: '2025/2026',
    });
    const [saving, setSaving] = useState(false);
    const [zoomField, setZoomField] = useState(null);

    const FIELDS = [
        ['titular',        'Tu nombre',      'text', 'Nombre y apellidos',
            'Es el nombre que sale en el cuaderno.'],
        ['municipio',      'Tu municipio',   'text', 'Valdepeñas',
            'Con él te ponemos el tiempo y los avisos de tu zona.'],
        ['campana_activa', 'Campaña',        'text', '2026/2027',
            'La campaña en la que vas a ir apuntando.'],
    ];

    const save = async () => {
        if (!form.titular.trim()) { alert('Escribe tu nombre para continuar'); return; }
        setSaving(true);
        // Se mandan SOLO estos tres campos. El backend guarda lo que recibe y deja
        // el resto como esté (blueprints/explotacion.py → actualizar_explotacion).
        const res = await fetch('/api/explotacion', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                titular: form.titular,
                municipio: form.municipio,
                campana_activa: form.campana_activa,
            }),
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
                        Empecemos
                    </h1>
                    <p style={{ color: '#6b7280', fontSize: '0.88rem', margin: '8px 0 0', lineHeight: 1.5 }}>
                        Solo tres cosas y ya puedes entrar. El NIF y los demás datos
                        se ponen luego, en Ajustes.
                    </p>
                </div>

                <div style={{ background: '#fff', borderRadius: 20, padding: 24, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
                    {FIELDS.map(([k, l, t, ph, ayuda]) => (
                        <div key={k} style={{ marginBottom: 16 }}>
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
                            <p style={{ color: '#6b7280', fontSize: '0.78rem', margin: '5px 2px 0', lineHeight: 1.4 }}>
                                {ayuda}
                            </p>
                        </div>
                    ))}
                    <button className="btn-primary" style={{ width: '100%', marginTop: 8 }} onClick={save} disabled={saving}>
                        {saving ? 'Guardando…' : 'Entrar en mi cuaderno'}
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
