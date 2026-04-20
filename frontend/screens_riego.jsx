const ScreenRiego = ({ user, campana, showToast, goBack }) => {
    const [riegoHistory, setRiegoHistory] = React.useState([]);
    const [parcelas, setParcelas] = React.useState([]);
    const [loading, setLoading] = React.useState(true);

    const [form, setForm] = React.useState({
        fecha: new Date().toISOString().split('T')[0],
        campana: campana,
        parcela_id: '',
        superficie_ha: '',
        sistema_riego: 'Goteo',
        horas_riego: '',
        m3_aplicados: '',
        fuente_agua: 'Pozo propio',
        caudal_lh: '',
        observaciones: ''
    });

    React.useEffect(() => {
        Promise.all([
            fetch('/api/parcelas').then(r => r.json()),
            fetch(`/api/riego?campana=${encodeURIComponent(campana)}`).then(r => r.json())
        ]).then(([pData, rData]) => {
            setParcelas(pData);
            setRiegoHistory(rData);
            setLoading(false);
        });
    }, [campana]);

    const handleSubmit = (e) => {
        e.preventDefault();
        const p = parcelas.find(x => x.id.toString() === form.parcela_id.toString());
        if (!p) {
            showToast("Selecciona una parcela válida");
            return;
        }

        const payload = {
            ...form,
            parcela_etiqueta: p.etiqueta || p.nombre,
            horas_riego: parseFloat(form.horas_riego) || 0,
            m3_aplicados: parseFloat(form.m3_aplicados) || 0,
            caudal_lh: parseFloat(form.caudal_lh) || null
        };

        fetch('/api/riego', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(res => {
            if (res.ok) {
                showToast("Anotación de riego guardada");
                goBack();
            } else {
                showToast("Error al guardar riego");
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
                        <h1 className="text-2xl font-bold">Plan de Riego</h1>
                        <p className="text-emerald-100 text-sm">Nueva anotación</p>
                    </div>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
                <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">Fecha</label>
                    <input type="date" value={form.fecha} onChange={e => setForm({...form, fecha: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" required />
                </div>
                
                <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">Parcela</label>
                    <select value={form.parcela_id} onChange={e => {
                        const p = parcelas.find(x => x.id.toString() === e.target.value);
                        setForm({...form, parcela_id: e.target.value, superficie_ha: p ? p.superficie_ha : ''});
                    }} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" required>
                        <option value="">Selecciona parcela...</option>
                        {parcelas.map(p => (
                            <option key={p.id} value={p.id}>{p.nombre} ({p.superficie_ha} ha)</option>
                        ))}
                    </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-bold text-gray-700 mb-1">Sistema Riego</label>
                        <select value={form.sistema_riego} onChange={e => setForm({...form, sistema_riego: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]">
                            <option value="Goteo">Goteo</option>
                            <option value="Aspersión">Aspersión</option>
                            <option value="Inundación">Inundación</option>
                            <option value="Pivot">Pivot</option>
                            <option value="Otro">Otro</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-gray-700 mb-1">Fuente Agua</label>
                        <select value={form.fuente_agua} onChange={e => setForm({...form, fuente_agua: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]">
                            <option value="Pozo propio">Pozo propio</option>
                            <option value="Comunidad de regantes">Comunidad regantes</option>
                            <option value="Balsa">Balsa</option>
                            <option value="Río">Río</option>
                            <option value="Otro">Otro</option>
                        </select>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-bold text-gray-700 mb-1">Horas de Riego</label>
                        <input type="number" step="0.5" value={form.horas_riego} onChange={e => setForm({...form, horas_riego: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" placeholder="Ej: 4.5" required />
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-gray-700 mb-1">Volumen (m³)</label>
                        <input type="number" step="1" value={form.m3_aplicados} onChange={e => setForm({...form, m3_aplicados: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" placeholder="Ej: 150" required />
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">Caudal (l/h) <span className="text-gray-400 font-normal">(Opcional)</span></label>
                    <input type="number" step="1" value={form.caudal_lh} onChange={e => setForm({...form, caudal_lh: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" placeholder="Ej: 2000" />
                </div>

                <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">Observaciones</label>
                    <textarea rows="2" value={form.observaciones} onChange={e => setForm({...form, observaciones: e.target.value})} className="w-full bg-gray-50 border border-gray-200 rounded-xl p-3 focus:outline-none focus:border-[#1D9E75]" placeholder="Opcional..."></textarea>
                </div>

                <button type="submit" className="w-full bg-[#1D9E75] text-white p-4 rounded-xl font-bold shadow-lg hover:shadow-xl transition flex justify-center items-center gap-2 mt-4 text-lg">
                    <i data-lucide="droplets" className="w-5 h-5"></i> Guardar Riego
                </button>
            </form>

            {riegoHistory.length > 0 && (
                <div className="px-6 mt-4 border-t border-gray-100 pt-6">
                    <h2 className="text-xl font-bold text-gray-800 mb-4">Historial de Riego ({campana})</h2>
                    <div className="space-y-4">
                        {riegoHistory.map(r => (
                            <div key={r.id} className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex items-center gap-4">
                                <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-500 flex items-center justify-center shrink-0">
                                    <i data-lucide="droplet" className="w-5 h-5"></i>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className="font-bold text-gray-900 truncate">{r.parcela_etiqueta}</h3>
                                    <p className="text-sm text-gray-500 truncate">{r.sistema_riego} • {r.fuente_agua}</p>
                                </div>
                                <div className="text-right shrink-0">
                                    <p className="text-sm font-bold text-gray-900">{r.fecha}</p>
                                    <p className="text-xs text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded-full inline-block mt-1">
                                        {r.m3_aplicados} m³
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};
