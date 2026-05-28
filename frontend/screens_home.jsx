function _wxDiaLabel(fechaStr) {
    const d = new Date(fechaStr + 'T12:00:00');
    const hoy = new Date(); hoy.setHours(12,0,0,0);
    const man = new Date(hoy); man.setDate(man.getDate()+1);
    if (d.toDateString() === hoy.toDateString()) return 'Hoy';
    if (d.toDateString() === man.toDateString()) return 'Mañana';
    return d.toLocaleDateString('es-ES', { weekday:'short', day:'numeric', month:'short' });
}

function ScreenHome({ campana, onOpenForm, showToast, onNavigate }) {
    const { useState, useEffect, useCallback } = React;

    // ── Estado principal ──
    const [explot, setExplot]           = useState(null);
    const [weather, setWeather]         = useState(null);
    const [wxState, setWxState]         = useState('idle');   // idle|loading|ok|error
    const [wxView, setWxView]           = useState('dias');   // 'dias' | 'horas'
    const [modalOpcion, setModalOpcion] = useState(null);  // null | 'tu' | 'yo'
    const [tuSubView, setTuSubView]     = useState(null);  // null | 'desde_cero'

    // ── Estado NLP ──
    const [nlpTexto, setNlpTexto]               = useState('');
    const [nlpProcesando, setNlpProcesando]     = useState(false);
    const [nlpResultado, setNlpResultado]       = useState(null);
    const [nlpGuardando, setNlpGuardando]       = useState(false);
    const [nlpParcelaNombre, setNlpParcelaNombre] = useState('');
    const [micActivo, setMicActivo]             = useState(false);
    const recognitionRef = React.useRef(null);
    const [importando, setImportando]           = useState(false);
    const [importResult, setImportResult]       = useState(null);
    const [gsheetUrl, setGsheetUrl]             = useState('');
    const [gsheetActivo, setGsheetActivo]       = useState(false);
    const fileRef = React.useRef(null);

    const useDragScroll = () => {
        const ref = React.useRef(null);
        const dragging = React.useRef(false);
        const startX = React.useRef(0);
        const scrollLeft = React.useRef(0);
        const onMouseDown = e => { dragging.current = true; startX.current = e.pageX - ref.current.offsetLeft; scrollLeft.current = ref.current.scrollLeft; ref.current.style.cursor = 'grabbing'; };
        const onMouseUp   = () => { dragging.current = false; if (ref.current) ref.current.style.cursor = 'grab'; };
        const onMouseMove = e => { if (!dragging.current) return; e.preventDefault(); const x = e.pageX - ref.current.offsetLeft; ref.current.scrollLeft = scrollLeft.current - (x - startX.current); };
        return { ref, onMouseDown, onMouseUp, onMouseLeave: onMouseUp, onMouseMove };
    };
    const dragDias  = useDragScroll();
    const dragHoras = useDragScroll();

    // ── Cargar explotación ──
    useEffect(() => {
        fetch('/api/explotacion', { credentials: 'include' })
            .then(r => r.ok ? r.json() : {})
            .then(d => setExplot(d || {}))
            .catch(() => setExplot({}));
    }, []);

    // ── Meteorología (Open-Meteo) ──
    const loadWeather = useCallback(async (municipio) => {
        const mun = (municipio || '').trim();
        if (!mun) { setWxState('error'); return; }
        try {
            setWxState('loading');
            const gRes  = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(mun)}&country=ES&language=es&count=1`);
            const gJson = await gRes.json();
            const hit   = gJson?.results?.[0];
            if (!hit) { setWxState('error'); return; }
            const params = [
                `latitude=${hit.latitude}`, `longitude=${hit.longitude}`,
                `current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code`,
                `daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max`,
                `hourly=temperature_2m,precipitation,precipitation_probability,weather_code,wind_speed_10m`,
                `wind_speed_unit=kmh`, `timezone=Europe%2FMadrid`, `forecast_days=7`,
            ].join('&');
            const wRes  = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
            const w = await wRes.json();
            const c = w?.current;
            if (!c) { setWxState('error'); return; }

            // Procesar pronóstico diario
            const daily = (w.daily?.time || []).map((t, i) => ({
                fecha: t, code: w.daily.weather_code[i],
                tmax: Math.round(w.daily.temperature_2m_max[i]),
                tmin: Math.round(w.daily.temperature_2m_min[i]),
                lluvia_mm: +(w.daily.precipitation_sum[i] ?? 0).toFixed(1),
                prob_lluvia: w.daily.precipitation_probability_max[i] ?? 0,
                viento: Math.round(w.daily.wind_speed_10m_max[i] ?? 0),
                rachas: Math.round(w.daily.wind_gusts_10m_max[i] ?? 0),
            }));

            // Procesar pronóstico horario — próximas 24h
            const now = new Date();
            const hourly = (w.hourly?.time || []).map((t, i) => ({
                hora: t, code: w.hourly.weather_code[i],
                temp: Math.round(w.hourly.temperature_2m[i]),
                lluvia_mm: +(w.hourly.precipitation[i] ?? 0).toFixed(1),
                prob_lluvia: w.hourly.precipitation_probability[i] ?? 0,
                viento: Math.round(w.hourly.wind_speed_10m[i] ?? 0),
            })).filter(h => {
                const d = new Date(h.hora);
                return d >= now && d <= new Date(now.getTime() + 24 * 3600000);
            });

            // Generar alertas a partir de umbrales AEMET
            const alertas = [];
            daily.forEach(d => {
                const lbl = _wxDiaLabel(d.fecha);
                // Tormentas (códigos WMO 95-99)
                if (d.code === 99) alertas.push({ nivel: 'rojo',    icon: '🔴', texto: `⚡ Tormenta con granizo fuerte — ${lbl}` });
                else if (d.code === 96) alertas.push({ nivel: 'naranja', icon: '🟠', texto: `⚡ Tormenta con granizo — ${lbl}` });
                else if ([95, 80, 81, 82].includes(d.code) && d.prob_lluvia >= 70)
                    alertas.push({ nivel: 'amarillo', icon: '🟡', texto: `⚡ Tormentas/chubascos probables (${d.prob_lluvia}%) — ${lbl}` });
                else if (d.code === 95) alertas.push({ nivel: 'amarillo', icon: '🟡', texto: `⚡ Tormenta eléctrica — ${lbl}` });
                // Lluvia — umbrales AEMET CLM (acumulado diario)
                if (d.lluvia_mm >= 60) alertas.push({ nivel: 'rojo',    icon: '🔴', texto: `Lluvia muy intensa (${d.lluvia_mm}mm) — ${lbl}` });
                else if (d.lluvia_mm >= 30) alertas.push({ nivel: 'naranja', icon: '🟠', texto: `Lluvia intensa (${d.lluvia_mm}mm) — ${lbl}` });
                else if (d.lluvia_mm >= 15) alertas.push({ nivel: 'amarillo', icon: '🟡', texto: `Lluvia fuerte (${d.lluvia_mm}mm) — ${lbl}` });
                // Viento — AEMET usa rachas, no velocidad sostenida
                const g = d.rachas;
                if (g >= 90)      alertas.push({ nivel: 'rojo',    icon: '🔴', texto: `Rachas muy fuertes (${g}km/h) — ${lbl}` });
                else if (g >= 70) alertas.push({ nivel: 'naranja', icon: '🟠', texto: `Rachas fuertes (${g}km/h) — ${lbl}` });
                else if (g >= 55) alertas.push({ nivel: 'amarillo', icon: '🟡', texto: `Rachas moderadas (${g}km/h) — ${lbl}` });
                // Calor — umbrales AEMET CLM
                if (d.tmax >= 42)      alertas.push({ nivel: 'rojo',    icon: '🔴', texto: `Calor extremo (${d.tmax}°C) — ${lbl}` });
                else if (d.tmax >= 40) alertas.push({ nivel: 'naranja', icon: '🟠', texto: `Calor intenso (${d.tmax}°C) — ${lbl}` });
                else if (d.tmax >= 38) alertas.push({ nivel: 'amarillo', icon: '🟡', texto: `Calor (${d.tmax}°C) — ${lbl}` });
                // Heladas
                if (d.tmin <= -8)      alertas.push({ nivel: 'naranja', icon: '🟠', texto: `Helada fuerte (${d.tmin}°C) — ${lbl}` });
                else if (d.tmin <= -4) alertas.push({ nivel: 'amarillo', icon: '🟡', texto: `Helada (${d.tmin}°C) — ${lbl}` });
            });

            // Avisos agrícolas — umbrales más bajos, prácticos para trabajo en campo
            const avisos = [];
            daily.slice(0, 5).forEach(d => {
                const lbl = _wxDiaLabel(d.fecha);
                const yaAlertaViento  = alertas.some(a => a.texto.includes(lbl) && a.texto.includes('km/h'));
                const yaAlertaLluvia  = alertas.some(a => a.texto.includes(lbl) && (a.texto.includes('mm') || a.texto.includes('Tormenta') || a.texto.includes('chubascos')));
                const yaAlertaCalor   = alertas.some(a => a.texto.includes(lbl) && a.texto.includes('°C') && a.texto.includes('Calor'));
                const yaAlertaHelada  = alertas.some(a => a.texto.includes(lbl) && a.texto.includes('°C') && a.texto.includes('elada'));
                // Viento: ≥40km/h rachas o ≥25km/h sostenido — impide tratamientos fitosanitarios
                if (!yaAlertaViento && d.rachas >= 40)
                    avisos.push({ nivel: 'aviso', icon: '💨', texto: `Viento fuerte (rachas ${d.rachas}km/h) — no tratar — ${lbl}` });
                else if (!yaAlertaViento && d.viento >= 25)
                    avisos.push({ nivel: 'aviso', icon: '💨', texto: `Viento moderado (${d.viento}km/h) — precaución al tratar — ${lbl}` });
                // Lluvia leve: ≥5mm o probabilidad ≥50%
                if (!yaAlertaLluvia && (d.lluvia_mm >= 5 || d.prob_lluvia >= 50))
                    avisos.push({ nivel: 'aviso', icon: '🌧️', texto: `Lluvia prevista (${d.lluvia_mm}mm, ${d.prob_lluvia}%) — ${lbl}` });
                // Calor agrícola: 35-37°C — riesgo para trabajadores y aplicación de fitosanitarios
                if (!yaAlertaCalor && d.tmax >= 35 && d.tmax < 38)
                    avisos.push({ nivel: 'aviso', icon: '☀️', texto: `Calor (${d.tmax}°C) — evitar horas centrales — ${lbl}` });
                // Helada suave: 0-3°C — riesgo para viña, almendro y frutales en flor
                if (!yaAlertaHelada && d.tmin <= 3 && d.tmin > -4)
                    avisos.push({ nivel: 'aviso', icon: '❄️', texto: `Riesgo de helada (${d.tmin}°C mín) — ${lbl}` });
            });

            // Alertas oficiales AEMET (si hay API key configurada)
            let aemetAlertas = [];
            try {
                const provincia = hit.admin2 || hit.admin1 || '';
                if (provincia) {
                    const aRes  = await fetch(`/api/aemet/alertas?provincia=${encodeURIComponent(provincia)}`);
                    const aJson = await aRes.json();
                    if (aJson.ok) aemetAlertas = aJson.alertas || [];
                }
            } catch {}

            setWeather({
                temp: Math.round(c.temperature_2m), hum: Math.round(c.relative_humidity_2m),
                wind: Math.round(c.wind_speed_10m), precip: c.precipitation ?? 0,
                code: c.weather_code, municipio: hit.name,
                daily, hourly,
                alertas: [...aemetAlertas, ...alertas],
                avisos,
            });
            setWxState('ok');
        } catch { setWxState('error'); }
    }, []);

    useEffect(() => {
        if (explot === null) return;           // aún cargando
        if (!explot?.municipio?.trim()) { setWxState('error'); return; }
        loadWeather(explot.municipio);
        const id = setInterval(() => loadWeather(explot.municipio), 30 * 60 * 1000);
        return () => clearInterval(id);
    }, [explot, loadWeather]);

    // ── Helpers meteorología ──
    const wxIcon = (code) => {
        const map = { 0: '☀️ Despejado', 1: '🌤️ P. nublado', 2: '⛅ Nublado', 3: '☁️ Cubierto', 45: '🌫️ Niebla', 51: '🌦️ Llovizna', 53: '🌦️ Llovizna', 61: '🌧️ Lluvia', 63: '🌧️ Lluvia', 65: '🌧️ Lluvia fuerte', 71: '🌨️ Nieve', 80: '🌧️ Chubascos', 82: '⛈️ Chubascos', 85: '🌨️ Nevadas', 95: '⛈️ Tormenta', 96: '⛈️ Tormenta granizo', 99: '⛈️ Tormenta granizo' };
        for (const key of Object.keys(map).sort((a,b)=>+b-+a)) { if (code >= +key) return map[key].split(' '); }
        return ['🌡️', ''];
    };
    // ── Reconocimiento de voz ──
    const toggleMic = () => {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) { showToast('Tu navegador no soporta reconocimiento de voz'); return; }
        if (micActivo) {
            recognitionRef.current?.stop();
            setMicActivo(false);
            return;
        }
        const rec = new SR();
        rec.lang = 'es-ES';
        rec.continuous = true;
        rec.interimResults = false;
        recognitionRef.current = rec;
        const baseText = nlpTexto.trim();
        let acumulado = baseText;
        rec.onstart = () => setMicActivo(true);
        rec.onend   = () => setMicActivo(false);
        rec.onerror = (ev) => {
            setMicActivo(false);
            if (ev.error !== 'no-speech') showToast('Error de micrófono — comprueba los permisos');
        };
        rec.onresult = (e) => {
            for (let i = e.resultIndex; i < e.results.length; i++) {
                if (e.results[i].isFinal) {
                    const t = e.results[i][0].transcript.trim();
                    acumulado = acumulado ? acumulado + ' ' + t : t;
                }
            }
            setNlpTexto(acumulado);
        };
        rec.start();
    };

    const resetNlp = () => {
        recognitionRef.current?.stop();
        setMicActivo(false);
        setNlpTexto(''); setNlpResultado(null); setNlpGuardando(false);
    };
    const volverHome = () => { setModalOpcion(null); setTuSubView(null); resetNlp(); };

    const headerLine = [explot?.titular, explot?.municipio, campana ? `Campaña ${campana}` : null]
        .filter(Boolean).join(' · ') || 'Explotación sin configurar';
    const wx = weather ? wxIcon(weather.code) : ['🌡️', ''];

    // ── NLP: Procesar texto ──
    const procesarTexto = async () => {
        if (!nlpTexto.trim()) { showToast('Por favor, escribe algo'); return; }
        setNlpProcesando(true);
        try {
            const res = await fetch('/api/parse', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ texto: nlpTexto }),
                credentials: 'include',
            });
            if (!res.ok) throw new Error('Error del servidor');
            setNlpResultado(await res.json());
        } catch (e) { showToast('❌ ' + e.message); }
        finally { setNlpProcesando(false); }
    };

    // ── NLP: Guardar registro ──
    const guardarRegistro = async () => {
        const p = nlpResultado?.parseo;
        const parcelaNombreEfectivo = p?.parcela?.nombre_candidato || nlpParcelaNombre.trim();
        if (!p?.parcela?.id && !parcelaNombreEfectivo) {
            showToast('Escribe el nombre de la parcela para continuar.');
            return;
        }
        setNlpGuardando(true);
        try {
            const res = await fetch('/api/parse/guardar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    accion:          p?.accion?.tipo,
                    palabra_clave:   p?.accion?.palabra_clave || null,
                    parcela_id:      p?.parcela?.id || null,
                    parcela_nombre:  parcelaNombreEfectivo || null,
                    producto:        p?.producto?.nombre || '',
                    fecha:           p?.fecha,
                    texto_original:  nlpResultado.texto_original,
                    campana,
                }),
                credentials: 'include',
            });
            const json = await res.json();
            if (!res.ok) throw new Error(json.error || 'Error al guardar');
            const esNuevaCreada = !p?.parcela?.id && parcelaNombreEfectivo;
            showToast(esNuevaCreada
                ? `✅ Guardado. Parcela "${json.parcela_nombre}" añadida a Mis Parcelas`
                : `✅ Guardado en ${json.parcela_nombre || 'parcela'}`);
            setNlpParcelaNombre('');
            volverHome();
        } catch (e) { showToast('❌ ' + e.message); }
        finally { setNlpGuardando(false); }
    };

    // ════════════════════════════════════════════
    // PANTALLA: NLP — Confirmar resultado
    // ════════════════════════════════════════════
    if (modalOpcion === 'yo' && nlpResultado) {
        const p = nlpResultado.parseo;
        const parcelaNombre = p?.parcela?.nombre || p?.parcela?.nombre_candidato;
        const esNueva = p?.parcela?.es_nueva;
        const faltaParcela = !parcelaNombre;

        return (
            <div style={{ padding: '16px 16px 32px' }}>
                <button onClick={resetNlp} style={S.backBtn}>← Volver</button>
                <h2 style={{ fontSize: '1.3rem', fontWeight: 800, margin: '0 0 4px' }}>Confirma los datos</h2>
                <p style={{ fontSize: '0.82rem', color: 'var(--on-surface-variant)', margin: '0 0 20px' }}>
                    "{nlpResultado.texto_original}"
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
                    {/* Parcela */}
                    {faltaParcela ? (
                        <div style={{ background: 'var(--surface-container-low)', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
                            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--on-surface-variant)', marginBottom: 6 }}>
                                📍 Parcela — no detectada
                            </div>
                            <input
                                autoFocus
                                placeholder="Escribe el nombre de la parcela…"
                                value={nlpParcelaNombre}
                                onChange={e => setNlpParcelaNombre(e.target.value)}
                                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '2px solid var(--primary)', fontSize: '0.95rem', boxSizing: 'border-box' }}
                            />
                            <div style={{ fontSize: '0.72rem', color: 'var(--on-surface-variant)', marginTop: 4 }}>
                                Se añadirá automáticamente a Mis Parcelas
                            </div>
                        </div>
                    ) : (
                        <NlpFila
                            icono="📍"
                            label="Parcela"
                            valor={parcelaNombre}
                            badge={esNueva ? '🆕 se añadirá a Mis Parcelas' : null}
                        />
                    )}
                    {/* Acción */}
                    <NlpFila icono="⚡" label="Acción"
                        valor={p?.accion?.tipo === 'labor' && p?.accion?.palabra_clave
                            ? p.accion.palabra_clave
                            : p?.accion?.tipo}
                    />
                    {/* Producto */}
                    <NlpFila icono="🧴" label="Producto" valor={p?.producto?.nombre} />
                    {/* Fecha */}
                    <NlpFila icono="📅" label="Fecha" valor={p?.fecha} />
                </div>

                    <button onClick={guardarRegistro} disabled={nlpGuardando || (faltaParcela && !nlpParcelaNombre.trim())}
                        style={{ ...S.btn, background: (nlpGuardando || (faltaParcela && !nlpParcelaNombre.trim())) ? 'var(--surface-variant)' : 'var(--primary)', color: (nlpGuardando || (faltaParcela && !nlpParcelaNombre.trim())) ? 'var(--on-surface-variant)' : '#fff', width: '100%' }}>
                        {nlpGuardando ? '⏳ Guardando...' : '✅ Guardar registro'}
                    </button>
            </div>
        );
    }

    // ════════════════════════════════════════════
    // PANTALLA: NLP — Entrada de texto
    // ════════════════════════════════════════════
    if (modalOpcion === 'yo') {
        return (
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
                <button onClick={volverHome} style={S.backBtn}>← Volver</button>
                <h2 style={{ fontWeight: 800, fontSize: '1.5rem', margin: '0 0 6px' }}>Habla que yo escribo</h2>
                <p style={{ fontSize: '0.88rem', color: 'var(--on-surface-variant)', margin: '0 0 24px', lineHeight: 1.5 }}>
                    Escribe lo que has hecho hoy, como si se lo dijeras a alguien:
                </p>

                <div style={{ background: 'var(--surface-container-low)', borderRadius: 'var(--radius-lg)', padding: '14px', marginBottom: 16, fontSize: '0.8rem', color: 'var(--on-surface-variant)', lineHeight: 1.8 }}>
                    <div style={{ fontWeight: 700, marginBottom: 4 }}>Ejemplos:</div>
                    <div>• "He tratado El Molino con cobre"</div>
                    <div>• "Abonado La Vega con urea, 50 kg"</div>
                    <div>• "Regé El Cerro esta mañana"</div>
                </div>

                {/* Área de texto + botón micrófono */}
                <div style={{ position: 'relative', marginBottom: 14 }}>
                    <textarea
                        value={nlpTexto}
                        onChange={e => setNlpTexto(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter' && e.ctrlKey) procesarTexto(); }}
                        placeholder={micActivo ? '🎤 Escuchando… habla ahora' : 'Escribe aquí o usa el micrófono…'}
                        style={{ fontFamily: 'var(--font-body)', fontSize: '1rem', padding: '14px', paddingBottom: 70, borderRadius: 'var(--radius-lg)', border: `2px solid ${micActivo ? '#dc2626' : 'var(--outline-variant)'}`, minHeight: 110, resize: 'vertical', width: '100%', boxSizing: 'border-box', transition: 'border-color 0.2s' }}
                    />
                    <button onClick={toggleMic} title={micActivo ? 'Parar grabación' : 'Grabar voz'} style={{
                        position: 'absolute', right: 10, bottom: 10,
                        width: 'auto', height: 52, borderRadius: 100, border: 'none', cursor: 'pointer',
                        background: micActivo ? '#dc2626' : 'var(--primary)',
                        color: '#fff', fontSize: 22, display: 'flex', alignItems: 'center', justifyContent: 'center',
                        gap: 8, padding: '0 18px',
                        boxShadow: micActivo ? '0 0 0 5px rgba(220,38,38,0.25)' : '0 2px 8px rgba(0,0,0,0.18)',
                        animation: micActivo ? 'pulse-mic 1.2s infinite' : 'none',
                        fontFamily: 'var(--font-body)', fontWeight: 700, fontSize: '0.95rem',
                    }}>
                        <span style={{ fontSize: 22 }}>{micActivo ? '⏹' : '🎤'}</span>
                        <span>{micActivo ? 'Parar' : 'Hablar'}</span>
                    </button>
                </div>

                <button onClick={procesarTexto} disabled={nlpProcesando || !nlpTexto.trim()}
                    style={{ ...S.btn, background: nlpProcesando || !nlpTexto.trim() ? 'var(--surface-variant)' : 'var(--primary)', color: nlpProcesando || !nlpTexto.trim() ? 'var(--on-surface-variant)' : '#fff' }}>
                    {nlpProcesando ? '⏳ Analizando...' : '✓ Procesar'}
                </button>
            </div>
        );
    }

    // ════════════════════════════════════════════
    // ════════════════════════════════════════════
    // PANTALLA: "Rellénalo tú" → módulos + Parcelas
    // ════════════════════════════════════════════
    if (modalOpcion === 'tu' && !tuSubView) {
        const MODULOS = [
            { icon: '🗺️', label: 'Parcelas',                  m: 'parcelas' },
            { icon: '🚜', label: 'Labor agrícola',             m: 'labor' },
            { icon: '🌿', label: 'Tratamiento fitosanitario',  m: 'tratamiento' },
            { icon: '🌱', label: 'Abono / Fertilización',      m: 'fertilizacion' },
            { icon: '📦', label: 'Cosecha',                    m: 'cosecha' },
            { icon: '🛒', label: 'Compras',                    m: 'compra' },
        ];
        return (
            <div style={{ padding: '16px' }}>
                <button onClick={volverHome} style={S.backBtn}>← Volver</button>
                <h2 style={{ fontWeight: 800, fontSize: '1.4rem', margin: '0 0 16px' }}>¿Qué quieres registrar?</h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {MODULOS.map(q => (
                        <button key={q.m}
                            onClick={() => q.m === 'parcelas' ? setTuSubView('parcelas') : onOpenForm(q.m)}
                            style={{ background: 'var(--surface-container-low)', borderRadius: 'var(--radius-lg)', border: '1.5px solid var(--outline-variant)', padding: '20px 18px', textAlign: 'left', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 18 }}>
                            <div style={{ fontSize: 34 }}>{q.icon}</div>
                            <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{q.label}</div>
                        </button>
                    ))}
                </div>
            </div>
        );
    }

    // ════════════════════════════════════════════
    // PANTALLA: "Rellénalo tú" → Parcelas (importar / Excel / Sheets)
    // ════════════════════════════════════════════
    if (modalOpcion === 'tu' && tuSubView === 'parcelas') {
        const handleImport = async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            setImportando(true);
            setImportResult(null);
            let res;
            try {
                const fd = new FormData();
                fd.append('file', file);
                res = await fetch('/api/import/excel', { method: 'POST', body: fd, credentials: 'include' });
            } catch (err) {
                setImportResult({ ok: false, msg: `❌ Error de red: ${err.message}` });
                setImportando(false);
                e.target.value = '';
                return;
            }
            let json;
            try {
                json = await res.json();
            } catch {
                const txt = await res.text().catch(() => '');
                setImportResult({ ok: false, msg: `❌ Error del servidor (${res.status}): ${txt.slice(0, 120) || 'respuesta vacía'}` });
                setImportando(false);
                e.target.value = '';
                return;
            }
            if (json.ok) {
                setImportResult({ ok: true, msg: `✅ Importados ${json.total} registros: ${json.resumen || 'sin datos nuevos'}` });
            } else {
                setImportResult({ ok: false, msg: `❌ ${json.error}` });
            }
            setImportando(false);
            e.target.value = '';
        };

        return (
            <div style={{ padding: '16px' }}>
                <button onClick={() => setTuSubView(null)} style={S.backBtn}>← Volver</button>
                <h2 style={{ fontWeight: 800, fontSize: '1.5rem', margin: '0 0 6px' }}>Parcelas</h2>
                <p style={{ fontSize: '0.83rem', color: 'var(--on-surface-variant)', margin: '0 0 24px' }}>Importa tus parcelas o introdúcelas manualmente.</p>

                {/* ── Aviso formato importación ── */}
                <div style={{ background: '#fefce8', border: '1.5px solid #fde68a', borderRadius: 'var(--radius-lg)', padding: '14px 16px', marginBottom: 16 }}>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#78350f', marginBottom: 8 }}>📋 ¿Cómo preparar tu hoja de cálculo?</div>
                    <p style={{ margin: '0 0 10px', fontSize: '0.82rem', color: '#92400e', lineHeight: 1.6 }}>
                        Necesitas <strong>5 columnas</strong> en la primera fila de tu hoja:
                    </p>
                    <div style={{ background: '#fff', border: '1px solid #fde68a', borderRadius: 8, overflow: 'hidden', marginBottom: 10 }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                            <thead>
                                <tr style={{ background: '#fde68a' }}>
                                    {['Nombre', 'Provincia', 'Municipio', 'Polígono', 'Parcela'].map(h => (
                                        <th key={h} style={{ padding: '7px 10px', textAlign: 'left', color: '#78350f', fontWeight: 700 }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    {['El Río', 'Ciudad Real', 'Tomelloso', '12', '45'].map((v,i) => (
                                        <td key={i} style={{ padding: '7px 10px', color: '#92400e', borderTop: '1px solid #fde68a' }}>{v}</td>
                                    ))}
                                </tr>
                                <tr style={{ background: '#fffbeb' }}>
                                    {['La Loma', 'Ciudad Real', 'Tomelloso', '12', '46'].map((v,i) => (
                                        <td key={i} style={{ padding: '7px 10px', color: '#92400e', borderTop: '1px solid #fde68a' }}>{v}</td>
                                    ))}
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.78rem', color: '#78350f', lineHeight: 1.5 }}>
                        ✅ El resto (superficie, uso del suelo…) lo busca la app automáticamente en el SIGPAC.
                    </p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <input ref={fileRef} type="file" accept=".xlsx" style={{ display: 'none' }} onChange={handleImport} />
                    <button onClick={() => fileRef.current.click()} disabled={importando}
                        style={{ ...S.opcionCard, background: 'linear-gradient(135deg, #14532d, #16a34a)', opacity: importando ? 0.7 : 1 }}>
                        <div style={{ fontSize: 36 }}>{importando ? '⏳' : '📊'}</div>
                        <div>
                            <div style={{ fontWeight: 700, fontSize: '1rem' }}>{importando ? 'Importando…' : 'Importar desde Excel'}</div>
                            <div style={{ fontSize: '0.78rem', marginTop: 3, opacity: 0.85 }}>Sube tu hoja de cálculo en formato .xlsx</div>
                        </div>
                    </button>
                    {importResult && (
                        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-lg)', fontSize: '0.88rem', fontWeight: 600,
                            background: importResult.ok ? '#dcfce7' : '#fee2e2',
                            color: importResult.ok ? '#14532d' : '#7f1d1d' }}>
                            {importResult.msg}
                        </div>
                    )}

                    <button onClick={() => setGsheetActivo(v => !v)}
                        style={{ ...S.opcionCard, background: 'linear-gradient(135deg, #0f4c2a, #1a7a40)', color: '#fff' }}>
                        <div style={{ fontSize: 36 }}>📗</div>
                        <div>
                            <div style={{ fontWeight: 700, fontSize: '1rem' }}>Importar desde Google Sheets</div>
                            <div style={{ fontSize: '0.78rem', marginTop: 3, opacity: 0.85 }}>Pega el enlace de tu hoja de cálculo</div>
                        </div>
                    </button>
                    {gsheetActivo && (
                        <div style={{ background: 'var(--surface-container-low)', borderRadius: 'var(--radius-lg)', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--on-surface-variant)', lineHeight: 1.5 }}>
                                1. Abre tu Google Sheet<br/>
                                2. Archivo → Compartir → <strong>Cualquier persona con el enlace</strong><br/>
                                3. Pega aquí el enlace
                            </p>
                            <input
                                value={gsheetUrl}
                                onChange={e => setGsheetUrl(e.target.value)}
                                placeholder="https://docs.google.com/spreadsheets/d/..."
                                style={{ padding: '10px 12px', borderRadius: 'var(--radius-md)', border: '1.5px solid var(--outline-variant)', fontSize: '0.85rem', fontFamily: 'var(--font-body)' }}
                            />
                            <button
                                disabled={importando || !gsheetUrl.trim()}
                                onClick={async () => {
                                    setImportando(true); setImportResult(null);
                                    try {
                                        const res = await fetch('/api/import/gsheet', {
                                            method: 'POST',
                                            headers: { 'Content-Type': 'application/json' },
                                            credentials: 'include',
                                            body: JSON.stringify({ url: gsheetUrl }),
                                        });
                                        const json = await res.json();
                                        setImportResult(json.ok
                                            ? { ok: true, msg: `✅ Importados ${json.total} registros: ${json.resumen || 'sin datos nuevos'}` }
                                            : { ok: false, msg: `❌ ${json.error}` });
                                        if (json.ok) { setGsheetUrl(''); setGsheetActivo(false); }
                                    } catch { setImportResult({ ok: false, msg: '❌ Error de conexión' }); }
                                    finally { setImportando(false); }
                                }}
                                style={{ padding: '12px', borderRadius: 'var(--radius-md)', border: 'none', background: 'var(--primary)', color: '#fff', fontWeight: 700, fontSize: '0.95rem', cursor: 'pointer', opacity: importando || !gsheetUrl.trim() ? 0.6 : 1 }}>
                                {importando ? '⏳ Importando…' : '📥 Importar'}
                            </button>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // ════════════════════════════════════════════
    // PANTALLA: Home principal
    // ════════════════════════════════════════════
    return (
        <div style={{ paddingBottom: 32 }}>
            {/* Header usuario */}
            <div style={{ background: 'var(--secondary-fixed)', padding: '16px 20px 14px', position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', top: -40, right: -40, width: 140, height: 140, borderRadius: '50%', background: 'rgba(104,219,174,0.05)' }} />
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 28, height: 28, flexShrink: 0, borderRadius: 'var(--radius-md)', background: 'linear-gradient(135deg, var(--primary), var(--primary-container))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}>🌿</div>
                    <span style={{ color: '#fff', fontSize: '0.78rem', fontWeight: 500, flex: 1, lineHeight: 1.4 }}>{headerLine}</span>
                </div>
            </div>

            {/* ══ WIDGET METEOROLOGÍA ══ */}
            <div style={{ background: 'linear-gradient(170deg, #0f2d1e 0%, #1a4731 45%, #1D9E75 100%)', color: '#fff' }}>
              {/* Wrapper centrado para desktop */}
              <div style={{ maxWidth: 900, margin: '0 auto' }}>

                {/* ── PARTE SUPERIOR: día actual + alertas ── */}
                <div style={{ padding: '10px 16px 10px' }}>
                    {wxState === 'ok' && weather ? (
                        <>
                            {/* Temperatura + cajón lluvia en la misma fila */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                                {/* Izquierda: icono + temp + stats */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
                                    <span style={{ fontSize: 28, lineHeight: 1 }}>{wx[0]}</span>
                                    <div>
                                        <div style={{ fontWeight: 900, fontSize: '1.6rem', lineHeight: 1 }}>{weather.temp}°C</div>
                                        <div style={{ fontSize: '0.63rem', opacity: 0.8, marginTop: 1 }}>{wx[1]}</div>
                                        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                                            <span style={{ fontSize: '0.65rem', opacity: 0.75 }}>💧{weather.hum}%</span>
                                            <span style={{ fontSize: '0.65rem', opacity: 0.75 }}>💨{weather.wind}km/h</span>
                                            <span style={{ fontSize: '0.65rem', opacity: 0.75 }}>🌡️{weather.daily?.[0]?.tmax ?? '—'}°/{weather.daily?.[0]?.tmin ?? '—'}°</span>
                                        </div>
                                    </div>
                                </div>
                                {/* Derecha: cajón prob. lluvia */}
                                <div style={{ flexShrink: 0, background: 'rgba(255,255,255,0.12)', borderRadius: 12, padding: '6px 10px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                                    <div style={{ fontSize: '1.4rem', fontWeight: 900, lineHeight: 1, color: '#7dd3fc' }}>
                                        {weather.daily?.[0]?.prob_lluvia ?? 0}%
                                    </div>
                                    <div style={{ fontSize: '0.58rem', opacity: 0.75, textTransform: 'uppercase', letterSpacing: '0.04em' }}>prob. lluvia</div>
                                    <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#bae6fd' }}>
                                        {(weather.daily?.[0]?.lluvia_mm ?? 0) > 0 ? `${weather.daily[0].lluvia_mm} L/m²` : '0 L/m²'}
                                    </div>
                                </div>
                            </div>

                            {/* Alertas AEMET + avisos agrícolas */}
                            {(() => {
                                const alertas = weather.alertas || [];
                                const avisos  = weather.avisos  || [];
                                const hayAlgo = alertas.length > 0 || avisos.length > 0;
                                return (
                                    <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
                                        {alertas.map((a, i) => (
                                            <div key={`a${i}`} style={{ background: 'rgba(0,0,0,0.35)', borderLeft: `4px solid ${a.nivel==='rojo'?'#f87171':a.nivel==='naranja'?'#fb923c':'#fbbf24'}`, borderRadius: '0 8px 8px 0', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 7 }}>
                                                <span style={{ fontSize: 16 }}>{a.icon}</span>
                                                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: a.nivel==='rojo'?'#fca5a5':a.nivel==='naranja'?'#fdba74':'#fde68a', flex: 1 }}>
                                                    ⚠️ {a.texto}
                                                </span>
                                                {a.fuente === 'AEMET' && (
                                                    <span style={{ fontSize: '0.6rem', fontWeight: 800, background: 'rgba(255,255,255,0.15)', borderRadius: 4, padding: '1px 5px', letterSpacing: '0.05em', opacity: 0.9 }}>AEMET</span>
                                                )}
                                            </div>
                                        ))}
                                        {avisos.map((a, i) => (
                                            <div key={`v${i}`} style={{ background: 'rgba(0,0,0,0.25)', borderLeft: '4px solid #60a5fa', borderRadius: '0 8px 8px 0', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 7 }}>
                                                <span style={{ fontSize: 16 }}>{a.icon}</span>
                                                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#bfdbfe', flex: 1 }}>
                                                    {a.texto}
                                                </span>
                                            </div>
                                        ))}
                                        {!hayAlgo && (
                                            <div style={{ background: 'rgba(0,0,0,0.20)', borderLeft: '4px solid #4ade80', borderRadius: '0 8px 8px 0', padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 7 }}>
                                                <span style={{ fontSize: 16 }}>✅</span>
                                                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#bbf7d0', flex: 1 }}>Sin alertas meteorológicas activas</span>
                                            </div>
                                        )}
                                    </div>
                                );
                            })()}

                            <div style={{ marginTop: 6, fontSize: '0.62rem', fontWeight: 600, opacity: 0.6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                                📍 {weather.municipio}
                            </div>
                        </>
                    ) : (
                        <div style={{ padding: '16px 0' }}>
                            {wxState === 'loading' || wxState === 'idle' ? (
                                <span style={{ opacity: 0.8, fontSize: '0.88rem' }}>⏳ Cargando meteorología…</span>
                            ) : (
                                <div>
                                    <div style={{ fontSize: '0.88rem', opacity: 0.85, marginBottom: 10 }}>
                                        📍 Configura tu municipio para ver el tiempo local
                                    </div>
                                    <button onClick={() => onNavigate && onNavigate('mas')} style={{
                                        background: 'rgba(255,255,255,0.18)', border: '1px solid rgba(255,255,255,0.3)',
                                        borderRadius: 10, color: '#fff', padding: '8px 16px',
                                        fontSize: '0.82rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font-body)',
                                    }}>
                                        ⚙️ Ir a Datos → Explotación
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* ── PARTE INFERIOR: pronóstico horizontal ── */}
                {wxState === 'ok' && weather?.daily?.length > 0 && (
                    <div style={{ background: 'rgba(0,0,0,0.25)', paddingBottom: 4 }}>
                        {/* Toggle días / horas */}
                        <div style={{ display: 'flex', padding: '6px 12px 6px', gap: 6 }}>
                            {[['dias','📅 Días'],['horas','🕐 Horas']].map(([v,lbl]) => (
                                <button key={v} onClick={() => setWxView(v)} style={{
                                    border: 'none', borderRadius: 20, padding: '4px 12px',
                                    fontWeight: 700, fontSize: '0.7rem', cursor: 'pointer',
                                    background: wxView === v ? '#fff' : 'rgba(255,255,255,0.15)',
                                    color: wxView === v ? '#1a4731' : 'rgba(255,255,255,0.85)',
                                    transition: 'background 0.2s',
                                }}>{lbl}</button>
                            ))}
                        </div>

                        {/* Vista por DÍAS — scroll horizontal con drag */}
                        {wxView === 'dias' && (
                            <div ref={dragDias.ref} onMouseDown={dragDias.onMouseDown} onMouseUp={dragDias.onMouseUp} onMouseLeave={dragDias.onMouseLeave} onMouseMove={dragDias.onMouseMove} style={{ display: 'flex', gap: 8, overflowX: 'auto', padding: '0 16px 12px', scrollbarWidth: 'none', cursor: 'grab', userSelect: 'none' }}>
                                {weather.daily.map((d, i) => {
                                    const [ico] = wxIcon(d.code);
                                    return (
                                        <div key={i} style={{ flexShrink: 0, background: 'rgba(255,255,255,0.1)', borderRadius: 10, padding: '7px 8px', textAlign: 'center', minWidth: 64 }}>
                                            <div style={{ fontSize: '0.62rem', fontWeight: 700, marginBottom: 4, opacity: 0.9 }}>{_wxDiaLabel(d.fecha)}</div>
                                            <div style={{ fontSize: 20, marginBottom: 4 }}>{ico}</div>
                                            <div style={{ fontWeight: 900, fontSize: '0.85rem' }}>{d.tmax}°</div>
                                            <div style={{ fontSize: '0.65rem', opacity: 0.7, marginBottom: 4 }}>{d.tmin}°</div>
                                            <div style={{ borderTop: '1px solid rgba(255,255,255,0.2)', paddingTop: 5 }}>
                                                <div style={{ fontSize: '0.9rem', fontWeight: 900, color: '#7dd3fc' }}>💧{d.prob_lluvia}%</div>
                                                <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#bae6fd', marginTop: 1 }}>
                                                    {d.lluvia_mm > 0 ? `${d.lluvia_mm} L/m²` : '—'}
                                                </div>
                                                <div style={{ fontSize: '0.58rem', opacity: 0.65, marginTop: 2 }}>💨{d.viento}km/h</div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {/* Vista por HORAS — scroll horizontal con drag */}
                        {wxView === 'horas' && (
                            <div ref={dragHoras.ref} onMouseDown={dragHoras.onMouseDown} onMouseUp={dragHoras.onMouseUp} onMouseLeave={dragHoras.onMouseLeave} onMouseMove={dragHoras.onMouseMove} style={{ display: 'flex', gap: 8, overflowX: 'auto', padding: '0 16px 12px', scrollbarWidth: 'none', cursor: 'grab', userSelect: 'none' }}>
                                {weather.hourly.map((h, i) => {
                                    const [ico] = wxIcon(h.code);
                                    const hora = new Date(h.hora).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
                                    return (
                                        <div key={i} style={{ flexShrink: 0, background: 'rgba(255,255,255,0.1)', borderRadius: 14, padding: '10px 10px', textAlign: 'center', minWidth: 74 }}>
                                            <div style={{ fontSize: '0.62rem', fontWeight: 700, marginBottom: 4, opacity: 0.9 }}>{hora}</div>
                                            <div style={{ fontSize: 20, marginBottom: 4 }}>{ico}</div>
                                            <div style={{ fontWeight: 900, fontSize: '0.85rem' }}>{h.temp}°</div>
                                            <div style={{ borderTop: '1px solid rgba(255,255,255,0.2)', paddingTop: 4, marginTop: 4 }}>
                                                <div style={{ fontSize: '0.9rem', fontWeight: 900, color: '#7dd3fc' }}>💧{h.prob_lluvia}%</div>
                                                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#bae6fd', marginTop: 2 }}>
                                                    {h.lluvia_mm > 0 ? `${h.lluvia_mm} L/m²` : '—'}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                )}
              </div>{/* /wrapper centrado */}
            </div>

            {/* ¿Cómo quieres empezar? */}
            <div style={{ padding: '28px 16px 0' }}>
                <h2 style={{ fontFamily: 'var(--font-heading)', fontWeight: 800, fontSize: '1.4rem', margin: '0 0 6px' }}>¿Cómo quieres empezar?</h2>
                <p style={{ fontSize: '0.83rem', color: 'var(--on-surface-variant)', margin: '0 0 16px' }}>La forma más rápida de registrar lo que has hecho hoy.</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <button onClick={() => setModalOpcion('tu')}
                        style={{ background: 'linear-gradient(135deg, #1e3a5f, #1d4ed8)', borderRadius: 'var(--radius-xl)', padding: '24px 16px', minHeight: 150, display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center', justifyContent: 'center', border: 'none', cursor: 'pointer', color: '#fff', textAlign: 'center' }}>
                        <div style={{ fontSize: 44 }}>📝</div>
                        <div>
                            <div style={{ fontWeight: 700, fontSize: '1rem' }}>Rellénalo tú</div>
                            <div style={{ fontSize: '0.73rem', marginTop: 3, opacity: 0.85 }}>Formularios simples</div>
                        </div>
                    </button>
                    <button onClick={() => setModalOpcion('yo')}
                        style={{ background: 'linear-gradient(135deg, #00694c, #008560)', borderRadius: 'var(--radius-xl)', padding: '24px 16px', minHeight: 150, display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center', justifyContent: 'center', border: 'none', cursor: 'pointer', color: '#fff', textAlign: 'center' }}>
                        <div style={{ fontSize: 44 }}>🎤</div>
                        <div>
                            <div style={{ fontWeight: 700, fontSize: '1rem' }}>Habla que yo escribo</div>
                            <div style={{ fontSize: '0.73rem', marginTop: 3, opacity: 0.85 }}>Lenguaje libre</div>
                        </div>
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Componentes auxiliares ──────────────────────────────────


function NlpFila({ icono, label, valor, badge, alerta }) {
    return (
        <div style={{ background: 'var(--surface-container-low)', borderRadius: 'var(--radius-md)', padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 20, flexShrink: 0 }}>{icono}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--on-surface-variant)', marginBottom: 2 }}>{label}</div>
                {alerta
                    ? <div style={{ fontSize: '0.85rem', color: 'var(--error, #b00020)', fontWeight: 500 }}>{alerta}</div>
                    : <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{valor || <span style={{ opacity: 0.4 }}>No detectado</span>}</div>
                }
            </div>
            {badge && <span style={{ background: 'var(--primary)', color: '#fff', fontSize: '0.65rem', fontWeight: 700, padding: '2px 8px', borderRadius: 100 }}>{badge}</span>}
        </div>
    );
}

// Estilos reutilizables
const S = {
    backBtn: {
        background: 'none', border: 'none', color: 'var(--primary)',
        fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer',
        marginBottom: 16, padding: 0,
    },
    btn: {
        border: 'none', borderRadius: 'var(--radius-lg)', padding: '14px 20px',
        fontWeight: 700, fontSize: '0.95rem', cursor: 'pointer',
        fontFamily: 'var(--font-body)',
    },
    opcionCard: {
        borderRadius: 'var(--radius-xl)', padding: '20px 18px', minHeight: 80,
        display: 'flex', alignItems: 'center', gap: 16,
        border: '1.5px solid transparent', cursor: 'pointer', color: '#fff',
        textAlign: 'left',
    },
};
