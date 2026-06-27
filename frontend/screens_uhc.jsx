// screens_uhc.jsx — Gestión de Unidades Homogéneas de Cultivo

function ScreenUHC({ campana, showToast, parcelas }) {
    const [grupos, setGrupos] = React.useState([]);
    const [loading, setLoading] = React.useState(true);
    const [editando, setEditando] = React.useState(null); // null | objeto grupo en edición
    const [parcelasGrupo, setParcelasGrupo] = React.useState([]);

    const reload = () => {
        setLoading(true);
        fetch(`/api/uhc?campana=${encodeURIComponent(campana)}`, { credentials: 'include' })
            .then(r => r.json())
            .then(d => { setGrupos(Array.isArray(d) ? d : []); setLoading(false); })
            .catch(() => setLoading(false));
    };

    React.useEffect(() => { reload(); }, [campana]);

    const abrirNuevo = () => {
        setParcelasGrupo([]);
        setEditando({ nombre: '', cultivo: '', notas: '', parcela_ids: [] });
    };

    const abrirEditar = async (g) => {
        const res = await fetch(`/api/uhc/${g.id}`, { credentials: 'include' });
        const d = await res.json();
        const ids = (d.parcelas || []).map(p => p.id);
        setParcelasGrupo(d.parcelas || []);
        setEditando({ ...d.uhc, parcela_ids: ids });
    };

    const eliminar = async (g) => {
        if (!confirm(`¿Eliminar el grupo "${g.nombre}"? Los tratamientos ya guardados no se borran.`)) return;
        await fetch(`/api/uhc/${g.id}`, { method: 'DELETE', credentials: 'include' });
        showToast('Grupo eliminado');
        reload();
    };

    const guardar = async () => {
        if (!(editando.nombre || '').trim()) { alert('El nombre del grupo es obligatorio'); return; }
        const esNuevo = !editando.id;
        const method = esNuevo ? 'POST' : 'PUT';
        const url = esNuevo ? '/api/uhc' : `/api/uhc/${editando.id}`;
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ ...editando, campana }),
        });
        if (!res.ok) {
            const d = await res.json().catch(() => ({}));
            alert(d.error || 'Error al guardar');
            return;
        }
        showToast(esNuevo ? '✅ Grupo creado' : '✅ Grupo actualizado');
        setEditando(null);
        reload();
    };

    const toggleParcela = (pid) => {
        setEditando(prev => {
            const ids = prev.parcela_ids || [];
            return {
                ...prev,
                parcela_ids: ids.includes(pid) ? ids.filter(x => x !== pid) : [...ids, pid],
            };
        });
    };

    if (editando !== null) {
        const parcelasActivas = (parcelas || []).filter(p => p.activa !== 0);
        return (
            <div style={{ maxWidth: 600, margin: '0 auto', padding: '16px 12px' }}>
                <button onClick={() => setEditando(null)} style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--primary)', fontWeight: 600, fontSize: '0.9rem', marginBottom: 16,
                }}>← Volver</button>

                <h2 style={{ margin: '0 0 20px', fontSize: '1.1rem' }}>
                    {editando.id ? 'Editar grupo' : 'Nuevo grupo UHC'}
                </h2>

                <div style={{ marginBottom: 14 }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: '0.85rem' }}>
                        Nombre del grupo *
                    </label>
                    <input className="input-field" placeholder="Ej: Trigo secano norte"
                        value={editando.nombre}
                        onChange={e => setEditando(p => ({ ...p, nombre: e.target.value }))} />
                </div>

                <div style={{ marginBottom: 14 }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: '0.85rem' }}>
                        Cultivo principal
                    </label>
                    <input className="input-field" placeholder="Ej: TRIGO, CEBADA, GIRASOL…"
                        value={editando.cultivo || ''}
                        onChange={e => setEditando(p => ({ ...p, cultivo: e.target.value }))} />
                </div>

                <div style={{ marginBottom: 20 }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 4, fontSize: '0.85rem' }}>
                        Notas
                    </label>
                    <textarea className="input-field" rows={2} placeholder="Opcional"
                        value={editando.notas || ''}
                        onChange={e => setEditando(p => ({ ...p, notas: e.target.value }))}
                        style={{ resize: 'vertical' }} />
                </div>

                <div style={{ marginBottom: 20 }}>
                    <label style={{ display: 'block', fontWeight: 600, marginBottom: 8, fontSize: '0.85rem' }}>
                        Parcelas del grupo ({(editando.parcela_ids || []).length} seleccionadas)
                    </label>
                    {parcelasActivas.length === 0 ? (
                        <p style={{ color: 'var(--on-surface-variant)', fontSize: '0.85rem' }}>
                            No tienes parcelas registradas todavía.
                        </p>
                    ) : (
                        <div style={{ border: '1px solid var(--outline-variant)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                            {parcelasActivas.map((p, i) => {
                                const sel = (editando.parcela_ids || []).includes(p.id);
                                return (
                                    <label key={p.id} style={{
                                        display: 'flex', alignItems: 'center', gap: 12,
                                        padding: '10px 14px',
                                        background: sel ? 'var(--primary-container)' : (i % 2 === 0 ? '#fff' : 'var(--surface-variant)'),
                                        cursor: 'pointer',
                                        borderBottom: i < parcelasActivas.length - 1 ? '1px solid var(--outline-variant)' : 'none',
                                    }}>
                                        <input type="checkbox" checked={sel} onChange={() => toggleParcela(p.id)}
                                            style={{ accentColor: 'var(--primary)', width: 18, height: 18 }} />
                                        <span style={{ flex: 1, fontSize: '0.88rem', fontWeight: sel ? 600 : 400 }}>
                                            {p.nombre_finca}
                                        </span>
                                        <span style={{ fontSize: '0.78rem', color: 'var(--on-surface-variant)' }}>
                                            {p.superficie_ha ? `${Number(p.superficie_ha).toFixed(2)} ha` : ''}
                                        </span>
                                    </label>
                                );
                            })}
                        </div>
                    )}
                </div>

                <button onClick={guardar} style={{
                    width: '100%', padding: '14px', background: 'var(--primary)',
                    color: '#fff', border: 'none', borderRadius: 'var(--radius-full)',
                    fontWeight: 700, fontSize: '1rem', cursor: 'pointer',
                    fontFamily: 'var(--font-body)',
                }}>
                    {editando.id ? '💾 Actualizar grupo' : '✓ Crear grupo'}
                </button>
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 600, margin: '0 auto', padding: '16px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <h2 style={{ margin: 0, fontSize: '1.1rem' }}>🌱 Grupos UHC</h2>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <HelpButton screenId="uhc" style={{ background: 'var(--surface-container-low)', color: 'var(--primary)' }} />
                <button onClick={abrirNuevo} style={{
                    background: 'var(--primary)', color: '#fff', border: 'none',
                    borderRadius: 'var(--radius-full)', padding: '8px 18px',
                    fontWeight: 700, fontSize: '0.88rem', cursor: 'pointer',
                    fontFamily: 'var(--font-body)',
                }}>+ Nuevo grupo</button>
                </div>
            </div>

            <p style={{ fontSize: '0.82rem', color: 'var(--on-surface-variant)', marginTop: 0, marginBottom: 20 }}>
                Un grupo UHC permite registrar un tratamiento fitosanitario una sola vez para todas las parcelas del grupo.
            </p>

            {loading ? (
                <p style={{ textAlign: 'center', color: 'var(--on-surface-variant)' }}>Cargando…</p>
            ) : grupos.length === 0 ? (
                <div style={{
                    textAlign: 'center', padding: '40px 20px',
                    background: 'var(--surface-container-low)', borderRadius: 'var(--radius-lg)',
                }}>
                    <div style={{ fontSize: '2.5rem', marginBottom: 12 }}>🌾</div>
                    <p style={{ fontWeight: 600, margin: '0 0 8px' }}>Sin grupos todavía</p>
                    <p style={{ fontSize: '0.82rem', color: 'var(--on-surface-variant)', margin: 0 }}>
                        Crea un grupo para agrupar parcelas del mismo cultivo.
                    </p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {grupos.map(g => (
                        <div key={g.id} style={{
                            background: '#fff', borderRadius: 'var(--radius-lg)',
                            border: '1px solid var(--outline-variant)', padding: '14px 16px',
                            display: 'flex', alignItems: 'center', gap: 12,
                        }}>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: 2 }}>{g.nombre}</div>
                                <div style={{ fontSize: '0.78rem', color: 'var(--on-surface-variant)' }}>
                                    {g.cultivo ? `${g.cultivo} · ` : ''}{g.num_parcelas} parcela{g.num_parcelas !== 1 ? 's' : ''}
                                </div>
                            </div>
                            <button onClick={() => abrirEditar(g)} style={{
                                background: 'var(--surface-container-low)', border: 'none',
                                borderRadius: 'var(--radius-md)', padding: '6px 12px',
                                cursor: 'pointer', fontSize: '0.82rem', fontWeight: 600,
                                color: 'var(--on-surface-variant)',
                            }}>✏️ Editar</button>
                            <button onClick={() => eliminar(g)} style={{
                                background: 'none', border: 'none',
                                cursor: 'pointer', color: '#dc2626', fontSize: '1.1rem',
                                padding: '4px 8px',
                            }}>🗑</button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
