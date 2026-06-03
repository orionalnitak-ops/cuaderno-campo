// ── Screen: Historial — Stitch "Editorial Agronomy" design ──
// Visual ref: Stitch screen b4975ca3981a4d139d7e5884011216fd
function ScreenHistorial({ campana, onEdit, showToast }) {
    const { useState, useEffect, useCallback } = React;

    const [records, setRecords] = useState([]);
    const [loading, setLoading] = useState(true);
    const [parcelas, setParcelas] = useState([]);
    const [showFilters, setShowFilters] = useState(false);

    const [fParcela,  setFParcela]  = useState('');
    const [fModulo,   setFModulo]   = useState('todos');
    const [fDesde,    setFDesde]    = useState('');
    const [fHasta,    setFHasta]    = useState('');
    const [fCampana,  setFCampana]  = useState(campana);

    const activeFilters = [fParcela, fModulo !== 'todos' ? fModulo : '', fDesde, fHasta].filter(Boolean).length;

    // Module metadata
    const MODULE_META = {
        tratamientos:  { icon: '🌿', label: 'Fitosanitario', chipClass: 'chip-tratamiento', accentColor: 'var(--primary)' },
        fertilizacion: { icon: '🌱', label: 'Fertilización',  chipClass: 'chip-fertilizacion', accentColor: '#4f46e5' },
        labores:       { icon: '🚜', label: 'Labor',          chipClass: 'chip-labor',         accentColor: '#1e4ed8' },
        cosecha:       { icon: '📦', label: 'Cosecha',        chipClass: 'chip-cosecha',        accentColor: '#be185d' },
        compras:       { icon: '🛒', label: 'Compras',        chipClass: 'chip-compra',         accentColor: '#b45309' },
        riego:         { icon: '💧', label: 'Riego',          chipClass: 'chip-riego',           accentColor: '#0369a1' },
        abonado:       { icon: '📋', label: 'Plan abonado',  chipClass: 'chip-abonado',        accentColor: '#0f766e' },
    };

    const MODULE_PILLS = [
        ['todos',         'Todos'],
        ['tratamientos',  '🌿 Fitosanitarios'],
        ['fertilizacion', '🌱 Fertilización'],
        ['labores',       '🚜 Labores'],
        ['cosecha',       '📦 Cosecha'],
        ['compras',       '🛒 Compras'],
        ['riego',         '💧 Riego'],
        ['abonado',       '📋 Plan abono'],
    ];

    const fetchRecords = useCallback(() => {
        setLoading(true);
        const params = new URLSearchParams();
        if (fParcela)             params.set('parcela_id', fParcela);
        if (fModulo !== 'todos')  params.set('modulo', fModulo);
        if (fDesde)               params.set('fecha_desde', fDesde);
        if (fHasta)               params.set('fecha_hasta', fHasta);
        if (fCampana)             params.set('campana', fCampana);

        fetch(`/api/historial?${params}`)
            .then(r => r.json())
            .then(data => { setRecords(Array.isArray(data) ? data : []); setLoading(false); })
            .catch(() => setLoading(false));
    }, [fParcela, fModulo, fDesde, fHasta, fCampana]);

    useEffect(() => { fetchRecords(); }, [fetchRecords]);
    useEffect(() => {
        fetch('/api/parcelas').then(r => r.json()).then(d => setParcelas(Array.isArray(d) ? d : []));
    }, []);

    const clearFilters = () => {
        setFParcela(''); setFModulo('todos'); setFDesde(''); setFHasta(''); setFCampana(campana);
    };

    const handleDelete = async (record) => {
        if (!confirm('¿Eliminar este registro?')) return;
        const endpoint = { tratamientos: 'tratamientos', fertilizacion: 'fertilizacion', labores: 'labores', cosecha: 'cosecha', compras: 'compras' }[record._modulo];
        if (!endpoint) return;
        await fetch(`/api/${endpoint}/${record.id}`, { method: 'DELETE' });
        showToast('Registro eliminado');
        fetchRecords();
    };

    const exportExcel = () => window.open(`/api/export/excel?campana=${encodeURIComponent(fCampana || campana)}`);

    const fmtDate = (d) => {
        if (!d) return '';
        try { return new Date(d + 'T00:00:00').toLocaleDateString('es-ES', { day: 'numeric', month: 'short' }); }
        catch { return d; }
    };

    return (
        <div style={{ paddingBottom: 32 }}>
            {/* ── Dark header (Stitch: "Historial de Actividad") ── */}
            <div style={{
                background: 'var(--secondary-fixed)',
                padding: '52px 20px 0',
                position: 'sticky', top: 0, zIndex: 20,
            }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                    <div>
                        <h1 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.55rem', color: '#fff', margin: '0 0 2px', letterSpacing: '-0.02em' }}>
                            Historial de Actividad
                        </h1>
                        <p style={{ color: 'rgba(255,255,255,0.50)', fontSize: '0.78rem', margin: 0 }}>
                            {loading ? '…' : `${records.length} registros`}
                        </p>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button className="btn-ghost" onClick={exportExcel}
                            style={{ color: '#fff', borderColor: 'rgba(255,255,255,0.20)', padding: '9px 14px', fontSize: '0.8rem', minHeight: 40, background: 'rgba(104,219,174,0.12)' }}>
                            📊 Exportar Excel
                        </button>
                        <button className="btn-ghost" onClick={() => setShowFilters(true)}
                            style={{ color: '#fff', borderColor: 'rgba(255,255,255,0.20)', padding: '9px 14px', fontSize: '0.8rem', minHeight: 40, position: 'relative' }}>
                            🔍 Filtrar
                            {activeFilters > 0 && (
                                <span style={{ position: 'absolute', top: -4, right: -4, background: 'var(--tertiary)', color: '#fff', borderRadius: '50%', width: 16, height: 16, fontSize: '0.6rem', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>
                                    {activeFilters}
                                </span>
                            )}
                        </button>
                    </div>
                </div>

                {/* ── Parcela selector (Stitch: "Todas las parcelas" dropdown) ── */}
                <div style={{ padding: '0 0 12px' }}>
                    <select className="input-field" value={fParcela} onChange={e => setFParcela(e.target.value)}
                        style={{ background: 'rgba(255,255,255,0.08)', borderColor: 'rgba(255,255,255,0.12)', color: '#fff', borderRadius: 'var(--radius-full)', fontSize: '0.85rem', padding: '10px 36px 10px 14px' }}>
                        <option value="" style={{ background: 'var(--secondary-fixed)' }}>Todas las parcelas</option>
                        {parcelas.map(p => <option key={p.id} value={p.id} style={{ background: 'var(--secondary-fixed)' }}>
                            {p.nombre_finca} (Pol {p.poligono}/Par {p.parcela_num})
                        </option>)}
                    </select>
                </div>

                {/* ── Module pills ── */}
                <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 14, scrollbarWidth: 'none' }}>
                    {MODULE_PILLS.map(([id, label]) => (
                        <button key={id} onClick={() => setFModulo(id)} style={{
                            background: fModulo === id ? 'var(--primary-fixed-dim)' : 'rgba(255,255,255,0.08)',
                            color: fModulo === id ? 'var(--secondary-fixed)' : 'rgba(255,255,255,0.65)',
                            border: 'none',
                            borderRadius: 'var(--radius-full)',
                            padding: '7px 14px',
                            fontSize: '0.78rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            whiteSpace: 'nowrap',
                            transition: 'all 0.15s',
                        }}>
                            {label}
                        </button>
                    ))}
                </div>
            </div>

            {/* ── Active filter chips ── */}
            {activeFilters > 0 && (
                <div style={{ padding: '10px 16px', display: 'flex', gap: 6, flexWrap: 'wrap', background: 'var(--surface-container-lowest)' }}>
                    {fDesde && <span className="chip chip-primary">Desde: {fDesde} <button onClick={() => setFDesde('')} style={{ background: 'none', border: 'none', cursor: 'pointer', marginLeft: 2, color: 'inherit' }}>×</button></span>}
                    {fHasta && <span className="chip chip-primary">Hasta: {fHasta} <button onClick={() => setFHasta('')} style={{ background: 'none', border: 'none', cursor: 'pointer', marginLeft: 2, color: 'inherit' }}>×</button></span>}
                    <button onClick={clearFilters} style={{ background: 'none', border: 'none', color: 'var(--tertiary)', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer' }}>Limpiar todo</button>
                </div>
            )}

            {/* ── Records (Stitch: grouped timeline cards) ── */}
            <div style={{ paddingTop: 8 }}>
                {loading ? (
                    <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--outline)' }}>Cargando historial…</div>
                ) : records.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '60px 24px', color: 'var(--outline)' }}>
                        <div style={{ fontSize: 48, marginBottom: 12 }}>📋</div>
                        <p style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, color: 'var(--on-surface)', margin: '0 0 6px' }}>Sin registros</p>
                        <p style={{ fontSize: '0.85rem', margin: 0 }}>
                            {activeFilters > 0 ? 'Prueba a cambiar los filtros' : 'Añade tu primer registro usando el botón +'}
                        </p>
                    </div>
                ) : records.map((r, i) => {
                    const meta = MODULE_META[r._modulo] || { icon: '📝', label: 'Registro', chipClass: 'chip-grey', accentColor: 'var(--outline)' };
                    return (
                        <div key={`${r._modulo}-${r.id}-${i}`} className="record-card" style={{ margin: '0 12px 8px' }}>
                            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                                {/* Left accent + icon */}
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                                    <div style={{ width: 40, height: 40, borderRadius: 'var(--radius-lg)', background: `${meta.accentColor}14`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0, border: `1.5px solid ${meta.accentColor}22` }}>
                                        {meta.icon}
                                    </div>
                                </div>
                                {/* Content */}
                                <div style={{ flex: 1, minWidth: 0 }}
                                    onClick={() => onEdit && onEdit(r._modulo?.replace(/s$/, '').replace('labore', 'labor'), r)}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                                        <span className={`chip ${meta.chipClass}`} style={{ fontSize: '0.6rem' }}>{meta.label.toUpperCase()}</span>
                                        <span style={{ fontSize: '0.72rem', color: 'var(--outline)', marginLeft: 'auto', flexShrink: 0 }}>
                                            {fmtDate((r._fecha || '').slice(0, 10))}
                                        </span>
                                    </div>
                                    <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '0.95rem', color: 'var(--on-surface)', marginBottom: 3 }}>
                                        {r._resumen?.split('·')[0]?.trim() || r.parcela_etiqueta || 'Registro'}
                                    </div>
                                    <div style={{ fontSize: '0.78rem', color: 'var(--on-surface-variant)', marginBottom: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        📍 {r.parcela_etiqueta}
                                    </div>
                                    {/* Stitch detail pills */}
                                    {r._resumen && (
                                        <div style={{ fontSize: '0.74rem', color: 'var(--on-surface-variant)', lineHeight: 1.5 }}>
                                            {r._resumen}
                                        </div>
                                    )}
                                </div>
                                {/* Delete */}
                                <button onClick={() => handleDelete(r)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--surface-dim)', fontSize: 16, padding: '2px 6px', flexShrink: 0, borderRadius: 'var(--radius-md)', transition: 'all 0.15s' }}
                                    onMouseEnter={e => { e.currentTarget.style.color = 'var(--tertiary)'; e.currentTarget.style.background = 'rgba(153,63,58,0.08)'; }}
                                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--surface-dim)'; e.currentTarget.style.background = 'none'; }}>
                                    🗑
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* ── Filter bottom sheet ── */}
            {showFilters && (
                <div className="overlay" onClick={() => setShowFilters(false)}>
                    <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom: 40 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                            <h3 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.1rem', margin: 0 }}>🔍 Filtrar registros</h3>
                            <button onClick={() => setShowFilters(false)} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--on-surface-variant)', padding: 4 }}>✕</button>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                            <div>
                                <label className="field-label">Fecha desde</label>
                                <input type="date" className="input-field" value={fDesde} onChange={e => setFDesde(e.target.value)} />
                            </div>
                            <div>
                                <label className="field-label">Fecha hasta</label>
                                <input type="date" className="input-field" value={fHasta} onChange={e => setFHasta(e.target.value)} />
                            </div>
                            <div>
                                <label className="field-label">Campaña</label>
                                <input className="input-field" value={fCampana} onChange={e => setFCampana(e.target.value)} placeholder="2025/2026" />
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                            {activeFilters > 0 && <button className="btn-ghost" onClick={clearFilters} style={{ flex: 1 }}>Limpiar</button>}
                            <button className="btn-primary" style={{ flex: 2 }} onClick={() => { fetchRecords(); setShowFilters(false); }}>
                                Aplicar filtros
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
