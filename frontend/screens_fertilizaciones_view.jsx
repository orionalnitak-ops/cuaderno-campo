const ScreenFertilizacionView = ({ campana, onShowUpgrade, user }) => {
    const [registros, setRegistros] = React.useState([]);
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        if (user.plan !== 'pro') {
            setLoading(false);
            return;
        }
        fetch(`/api/fertilizacion?campana=${encodeURIComponent(campana)}`)
            .then(res => res.json())
            .then(data => {
                setRegistros(Array.isArray(data) ? data : []);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [user.plan, campana]);

    if (user.plan !== 'pro') {
        return (
            <div className="pb-32 px-4 pt-6 h-full flex flex-col justify-center items-center text-center">
                <div className="text-6xl mb-4">🔒</div>
                <h2 className="text-xl font-bold text-gray-800 mb-2">Módulo PRO</h2>
                <p className="text-gray-500 mb-6 px-4">El registro de fertilización es obligatorio para mantener el cuaderno actualizado, pero requiere una suscripción PRO.</p>
                <button onClick={onShowUpgrade} className="bg-[#1D9E75] text-white font-bold px-6 py-3 rounded-xl shadow-lg">
                    Desbloquear ahora
                </button>
            </div>
        );
    }

    if (loading) {
        return <div className="p-8 text-center text-4xl animate-spin">⏳</div>;
    }

    return (
        <div className="pb-32 px-4 pt-6">
            <h1 className="text-2xl font-bold text-gray-800 mb-6">Fertilizaciones</h1>
            
            <div className="grid gap-4">
                {registros.map(r => (
                    <div key={r.id} className="bg-white rounded-2xl shadow-sm border border-emerald-100 p-4">
                        <div className="flex justify-between items-start mb-2">
                            <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">{r.fecha}</span>
                            <span className="text-[10px] bg-gray-100 text-gray-600 px-2 py-1 rounded-full font-bold">{r.tipo_fertilizante}</span>
                        </div>
                        <h3 className="font-bold text-gray-800 text-lg mb-1">{r.nombre_producto}</h3>
                        <p className="text-sm text-gray-500 mb-3">{r.parcela_etiqueta}</p>
                        
                        <div className="bg-gray-50 rounded-xl p-3 flex justify-between">
                            <div className="text-center w-1/3 border-r border-gray-200">
                                <span className="block text-xs text-gray-400">N-P-K</span>
                                <span className="font-bold text-gray-700">{r.n_pct || 0}-{r.p2o5_pct || 0}-{r.k2o_pct || 0}</span>
                            </div>
                            <div className="text-center w-1/3 border-r border-gray-200">
                                <span className="block text-xs text-gray-400">Dosis</span>
                                <span className="font-bold text-gray-700">{r.dosis_kg_m3_ha}</span>
                            </div>
                            <div className="text-center w-1/3">
                                <span className="block text-xs text-gray-400">Sis.</span>
                                <span className="font-bold text-gray-700">{r.forma_aplicacion}</span>
                            </div>
                        </div>
                    </div>
                ))}
                
                {registros.length === 0 && (
                    <div className="text-center py-12 text-gray-400 bg-white rounded-lg border border-dashed border-gray-200 mt-4 mx-2">
                        <div className="text-4xl mb-3 opacity-50">🌱</div>
                        <p>No hay abonados en esta campaña.</p>
                    </div>
                )}
            </div>
        </div>
    );
};
