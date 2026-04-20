const ScreenAbonado = ({ user, campana, showToast, goBack }) => {
    const [abonadoHistory, setAbonadoHistory] = React.useState([]);
    const [parcelas, setParcelas] = React.useState([]);
    const [loading, setLoading] = React.useState(true);

    const [form, setForm] = React.useState({
        campana: campana,
        parcela_id: '',
        cultivo: '',
        superficie_ha: '',
        rendimiento_esperado_kg_ha: '',
        abono_recomendado: '',
        dosis_recomendada_kg_ha: '',
        observaciones: ''
    });

    const [totals, setTotals] = React.useState(null);

    React.useEffect(() => {
        Promise.all([
            fetch('/api/parcelas').then(r => r.json()),
            fetch(`/api/abonado?campana=${encodeURIComponent(campana)}`).then(r => r.json())
        ]).then(([pData, aData]) => {
            setParcelas(pData);
            setAbonadoHistory(aData);
            setLoading(false);
        });
    }, [campana]);

    const calculateNPK = () => {
        const p = parcelas.find(x => x.id.toString() === form.parcela_id.toString());
        if (!p) return;

        let reqN=0, reqP=0, reqK=0;
        const c = form.cultivo.toUpperCase();
        if (c.includes('TRIGO')) { reqN=120; reqP=60; reqK=60; }
        else if (c.includes('CEBADA')) { reqN=100; reqP=50; reqK=50; }
        else if (c.includes('YEROS') || c.includes('LEGUMINOSA')) { reqN=20; reqP=40; reqK=40; }
        else if (c.includes('OLIVAR')) { reqN=80; reqP=30; reqK=100; }
        else if (c.includes('FRUTALES')) { reqN=100; reqP=50; reqK=150; }
        else if (c.includes('GIRASOL')) { reqN=80; reqP=60; reqK=60; }
        else if (c.includes('BARBECHO')) { reqN=0; reqP=0; reqK=0; }
        else { reqN=60; reqP=40; reqK=40; } // Default generic

        const sup = parseFloat(form.superficie_ha) || 0;
        
        // Very basic Yield factor could be applied here if needed, but not specified in prompt 
        // strictly beyond "Enter expected yield (kg/ha)". The reference NPK is by Crop.

        let recomendacion = "Se recomienda NPK genérico";
        if (c.includes('TRIGO') || c.includes('CEBADA') || c.includes('CEREAL')) recomendacion = "Se recomienda urea + MAP";
        if (c.includes('YEROS') || c.includes('LEGUMINOSA') || c.includes('GUISANTE')) recomendacion = "No requiere nitrógeno sintético";
        if (c.includes('OLIVAR')) recomendacion = "Se recomienda abono 15-15-15 o similar";

        const N = reqN * sup;
        const P = reqP * sup;
        const K = reqK * sup;

        setTotals({ reqN, reqP, reqK, N, P, K, msg: recomendacion });
        return { reqN, reqP, reqK, N, P, K, msg: recomendacion };
    };

    const handleCalculateClick = (e) => {
        e.preventDefault();
        calculateNPK();
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        const p = parcelas.find(x => x.id.toString() === form.parcela_id.toString());
        if (!p) {
            showToast("Selecciona una parcela válida");
            return;
        }

        const t = totals || calculateNPK();
        if (!t) return;

        const payload = {
            ...form,
            parcela_etiqueta: p.etiqueta || p.nombre,
            rendimiento_esperado_kg_ha: parseFloat(form.rendimiento_esperado_kg_ha) || 0,
            n_necesario_kg_ha: t.reqN,
            p_necesario_kg_ha: t.reqP,
            k_necesario_kg_ha: t.reqK,
            n_total_kg: t.N,
            p_total_kg: t.P,
            k_total_kg: t.K,
            dosis_recomendada_kg_ha: parseFloat(form.dosis_recomendada_kg_ha) || 0
        };

        fetch('/api/abonado', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(res => {
            if (res.ok) {
                showToast("Plan de abonado guardado");
                goBack();
            } else {
                showToast("Error al guardar plan");
            }
        });
    };

    if (loading) return <div className="p-8 text-center animate-spin">⏳</div>;

    return (
        <div className="pb-32 bg-white min-h-screen">
            <div className="bg-[#1D9E75] text-white p-6 pt-12 shadow-sm rounded-b-3xl">
                <div className="flex items-center gap-4">
                    <button onClick={goBack} className="w-10 h-10 bg-white/20 rounded-full flex justify-center items-center backdrop-blur-sm">
                        <i data-lucide="arrow-left" className="w-5 h-5 text-white"></i>
                    </button>
                    <div>
                        <h1 className="text-2xl font-bold">Plan de Abonado</h1>
                        <p className="text-emerald-100 text-sm">Cálculo de necesidades (NPK)</p>
                    </div>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
                <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">Parcela</label>
                    <select value={form.parcela_id} onChange={e => {
                        const p = parcelas.find(x => x.id.toString() === e.target.value);
                        setForm({
                            ...form, 
                            parcela_id: e.target.value, 
                            superficie_ha: p ? p.superficie_ha : '',
                            cultivo: p ? (p.cultivo_actual || '') : ''
                        });
                        setTotals(null);
                    }} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" required>
                        <option value="">Selecciona parcela...</option>
                        {parcelas.map(p => (
                            <option key={p.id} value={p.id}>{p.nombre} ({p.superficie_ha} ha)</option>
                        ))}
                    </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-bold text-gray-700 mb-1">Cultivo</label>
                        <input type="text" value={form.cultivo} onChange={e => setForm({...form, cultivo: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" required />
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-gray-700 mb-1">Superficie (ha)</label>
                        <input type="number" step="0.01" value={form.superficie_ha} readOnly className="w-full bg-gray-100 border border-gray-200 rounded-xl p-3 text-gray-500" />
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">Rendimiento Esperado (kg/ha) <span className="text-xs text-gray-400 font-normal">(Opcional)</span></label>
                    <input type="number" value={form.rendimiento_esperado_kg_ha} onChange={e => setForm({...form, rendimiento_esperado_kg_ha: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" placeholder="Ej: 3500" />
                </div>

                <button type="button" onClick={handleCalculateClick} className="w-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-bold p-3 rounded-xl hover:bg-indigo-100 transition">
                    Calcular Necesidades NPK
                </button>

                {totals && (
                    <div className="bg-gray-50 rounded-2xl p-4 border border-gray-200 animate-fade-in space-y-3 mt-4">
                        <h3 className="font-bold text-gray-800 text-sm border-b border-gray-200 pb-2">Resultados del Cálculo:</h3>
                        <div className="grid grid-cols-3 gap-2 text-center">
                            <div className="bg-blue-50 border border-blue-100 rounded-xl p-2 shadow-sm">
                                <div className="text-xs text-blue-600 font-bold">Nitrógeno (N)</div>
                                <div className="text-lg font-black text-blue-900">{totals.N.toFixed(1)} <span className="text-[10px] font-normal">kg</span></div>
                            </div>
                            <div className="bg-orange-50 border border-orange-100 rounded-xl p-2 shadow-sm">
                                <div className="text-xs text-orange-600 font-bold">Fósforo (P)</div>
                                <div className="text-lg font-black text-orange-900">{totals.P.toFixed(1)} <span className="text-[10px] font-normal">kg</span></div>
                            </div>
                            <div className="bg-green-50 border border-green-100 rounded-xl p-2 shadow-sm">
                                <div className="text-xs text-green-600 font-bold">Potasio (K)</div>
                                <div className="text-lg font-black text-green-900">{totals.K.toFixed(1)} <span className="text-[10px] font-normal">kg</span></div>
                            </div>
                        </div>
                        <div className="bg-white p-3 rounded-xl border-l-4 border-[#1D9E75] text-sm text-gray-700 font-medium mt-2">
                            💡 {totals.msg}
                        </div>
                    </div>
                )}

                <div className="pt-4 border-t border-gray-100 mt-4 space-y-4">
                    <div>
                        <label className="block text-sm font-bold text-gray-700 mb-1">Abono Recomendado (Producto)</label>
                        <input type="text" value={form.abono_recomendado} onChange={e => setForm({...form, abono_recomendado: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" placeholder="Ej: Urea 46%, NPK 8-15-15..." required />
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-gray-700 mb-1">Dosis (kg/ha)</label>
                        <input type="number" step="0.1" value={form.dosis_recomendada_kg_ha} onChange={e => setForm({...form, dosis_recomendada_kg_ha: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" placeholder="Ej: 250" required />
                    </div>
                </div>

                <div className="mt-4">
                    <label className="block text-sm font-bold text-gray-700 mb-1">Observaciones</label>
                    <textarea rows="2" value={form.observaciones} onChange={e => setForm({...form, observaciones: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" placeholder="Opcional..."></textarea>
                </div>

                <button type="submit" className="w-full bg-[#1D9E75] text-white p-4 rounded-xl font-bold shadow-lg hover:shadow-xl transition flex justify-center items-center gap-2 mt-6 text-lg">
                    <i data-lucide="save" className="w-5 h-5"></i> Guardar Plan
                </button>
            </form>

            {abonadoHistory.length > 0 && (
                <div className="px-6 mt-4 border-t border-gray-100 pt-6">
                    <h2 className="text-xl font-bold text-gray-800 mb-4">Planes guardados</h2>
                    <div className="space-y-4">
                        {abonadoHistory.map(a => (
                            <div key={a.id} className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex items-center gap-4">
                                <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-500 flex items-center justify-center shrink-0">
                                    <i data-lucide="file-spreadsheet" className="w-5 h-5"></i>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className="font-bold text-gray-900 truncate">{a.parcela_etiqueta}</h3>
                                    <p className="text-sm text-gray-500 truncate">{a.cultivo} • {a.abono_recomendado}</p>
                                </div>
                                <div className="text-right shrink-0 flex flex-col items-end gap-1">
                                    <p className="text-sm font-bold text-gray-900">{a.dosis_recomendada_kg_ha} kg/ha</p>
                                    <button onClick={() => window.open(`/api/export/pdf?campana=${encodeURIComponent(campana)}`, '_blank')} className="text-[10px] bg-gray-100 hover:bg-gray-200 text-gray-700 px-2 py-1 rounded font-bold border border-gray-300">
                                        🖨️ Imprimir
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};
