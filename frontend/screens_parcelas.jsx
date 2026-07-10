// Catálogo de cultivos con códigos IACS (Anexo VII FEGA — para SIEX 2027)
const CULTIVOS_IACS = [
    { cod: '980',  nombre: 'Barbecho',                 grupo: 'Barbecho' },
    { cod: '470',  nombre: 'Arroz',                    grupo: 'Cereales' },
    { cod: '440',  nombre: 'Avena',                    grupo: 'Cereales' },
    { cod: '430',  nombre: 'Cebada',                   grupo: 'Cereales' },
    { cod: '450',  nombre: 'Centeno',                  grupo: 'Cereales' },
    { cod: '454',  nombre: 'Maíz',                     grupo: 'Cereales' },
    { cod: '460',  nombre: 'Sorgo',                    grupo: 'Cereales' },
    { cod: '410',  nombre: 'Trigo blando',             grupo: 'Cereales' },
    { cod: '415',  nombre: 'Trigo duro',               grupo: 'Cereales' },
    { cod: '451',  nombre: 'Triticale',                grupo: 'Cereales' },
    { cod: '550',  nombre: 'Alfalfa',                  grupo: 'Forrajeras' },
    { cod: '560',  nombre: 'Esparceta / Zulla',        grupo: 'Forrajeras' },
    { cod: '100',  nombre: 'Ajo',                      grupo: 'Hortalizas' },
    { cod: '110',  nombre: 'Cebolla',                  grupo: 'Hortalizas' },
    { cod: '160',  nombre: 'Melón',                    grupo: 'Hortalizas' },
    { cod: '120',  nombre: 'Patata',                   grupo: 'Hortalizas' },
    { cod: '162',  nombre: 'Sandía',                   grupo: 'Hortalizas' },
    { cod: '140',  nombre: 'Tomate',                   grupo: 'Hortalizas' },
    { cod: '720',  nombre: 'Colza / Nabina',           grupo: 'Industriales' },
    { cod: '701',  nombre: 'Girasol',                  grupo: 'Industriales' },
    { cod: '780',  nombre: 'Remolacha azucarera',      grupo: 'Industriales' },
    { cod: '481',  nombre: 'Guisante proteaginoso',    grupo: 'Leguminosas' },
    { cod: '490',  nombre: 'Haba',                     grupo: 'Leguminosas' },
    { cod: '495',  nombre: 'Soja',                     grupo: 'Leguminosas' },
    { cod: '484',  nombre: 'Veza / Yeros',             grupo: 'Leguminosas' },
    { cod: '1710', nombre: 'Almendro',                 grupo: 'Leñosos' },
    { cod: '1770', nombre: 'Cerezo / Guindo',          grupo: 'Leñosos' },
    { cod: '1730', nombre: 'Ciruelo',                  grupo: 'Leñosos' },
    { cod: '1750', nombre: 'Higuera',                  grupo: 'Leñosos' },
    { cod: '1840', nombre: 'Limonero',                 grupo: 'Leñosos' },
    { cod: '1720', nombre: 'Melocotonero / Nectarino', grupo: 'Leñosos' },
    { cod: '1830', nombre: 'Naranjo',                  grupo: 'Leñosos' },
    { cod: '1760', nombre: 'Nogal',                    grupo: 'Leñosos' },
    { cod: '1820', nombre: 'Olivar',                   grupo: 'Leñosos' },
    { cod: '1740', nombre: 'Pistachero',               grupo: 'Leñosos' },
    { cod: '1712', nombre: 'Viñedo uva de mesa',       grupo: 'Leñosos' },
    { cod: '1711', nombre: 'Viñedo vinificación',      grupo: 'Leñosos' },
];

// ── Screen: Mis Parcelas — split panel + cascading SIGPAC ──

// Lista oficial INE de las 52 provincias españolas. Hardcoded porque
// es dato estable y el endpoint SIGPAC /provincias puede no estar accesible.
const PROVINCIAS_ES = [
    { cod: '15', nombre: 'A Coruña' },
    { cod: '01', nombre: 'Álava' },
    { cod: '02', nombre: 'Albacete' },
    { cod: '03', nombre: 'Alicante' },
    { cod: '04', nombre: 'Almería' },
    { cod: '33', nombre: 'Asturias' },
    { cod: '05', nombre: 'Ávila' },
    { cod: '06', nombre: 'Badajoz' },
    { cod: '08', nombre: 'Barcelona' },
    { cod: '48', nombre: 'Bizkaia' },
    { cod: '09', nombre: 'Burgos' },
    { cod: '10', nombre: 'Cáceres' },
    { cod: '11', nombre: 'Cádiz' },
    { cod: '39', nombre: 'Cantabria' },
    { cod: '12', nombre: 'Castellón' },
    { cod: '51', nombre: 'Ceuta' },
    { cod: '13', nombre: 'Ciudad Real' },
    { cod: '14', nombre: 'Córdoba' },
    { cod: '16', nombre: 'Cuenca' },
    { cod: '20', nombre: 'Gipuzkoa' },
    { cod: '17', nombre: 'Girona' },
    { cod: '18', nombre: 'Granada' },
    { cod: '19', nombre: 'Guadalajara' },
    { cod: '21', nombre: 'Huelva' },
    { cod: '22', nombre: 'Huesca' },
    { cod: '07', nombre: 'Illes Balears' },
    { cod: '23', nombre: 'Jaén' },
    { cod: '26', nombre: 'La Rioja' },
    { cod: '35', nombre: 'Las Palmas' },
    { cod: '24', nombre: 'León' },
    { cod: '25', nombre: 'Lleida' },
    { cod: '27', nombre: 'Lugo' },
    { cod: '28', nombre: 'Madrid' },
    { cod: '29', nombre: 'Málaga' },
    { cod: '52', nombre: 'Melilla' },
    { cod: '30', nombre: 'Murcia' },
    { cod: '31', nombre: 'Navarra' },
    { cod: '32', nombre: 'Ourense' },
    { cod: '34', nombre: 'Palencia' },
    { cod: '36', nombre: 'Pontevedra' },
    { cod: '37', nombre: 'Salamanca' },
    { cod: '38', nombre: 'Santa Cruz de Tenerife' },
    { cod: '40', nombre: 'Segovia' },
    { cod: '41', nombre: 'Sevilla' },
    { cod: '42', nombre: 'Soria' },
    { cod: '43', nombre: 'Tarragona' },
    { cod: '44', nombre: 'Teruel' },
    { cod: '45', nombre: 'Toledo' },
    { cod: '46', nombre: 'Valencia' },
    { cod: '47', nombre: 'Valladolid' },
    { cod: '49', nombre: 'Zamora' },
    { cod: '50', nombre: 'Zaragoza' },
];

// ── Modal: mapa SIGPAC embebido (Leaflet) ──
// Pinta la parcela DENTRO de la app (ortofoto PNOA + capa recintos SIGPAC +
// polígono de la parcela). No depende del visor externo → el zoom lo controla
// nuestro fitBounds, así que funciona igual en PC y en móvil.
// Pill de verificación SIGPAC. estado: 'verde'|'ambar'|'no_encontrada'|'sin_verificar'.
function sigpacBadge(estado) {
    const map = {
        verde:         { bg:'#dcfce7', fg:'#166534', bd:'#86efac', txt:'✓ Verificado' },
        ambar:         { bg:'#fef3c7', fg:'#92400e', bd:'#fde68a', txt:'⚠ Revisar' },
        no_encontrada: { bg:'#fef3c7', fg:'#92400e', bd:'#fde68a', txt:'⚠ No en SIGPAC' },
        sin_verificar: { bg:'#f3f4f6', fg:'#6b7280', bd:'#e5e7eb', txt:'Sin verificar' },
    };
    const s = map[estado];
    if (!s) return null;
    return (
        <span className="chip" style={{ background:s.bg, color:s.fg, border:`1px solid ${s.bd}`, fontSize:'0.7rem' }}>
            {s.txt}
        </span>
    );
}

function MapaSigpacModal({ parcela, onClose }) {
    const mapDivRef = React.useRef(null);
    const mapRef    = React.useRef(null);
    const [estado, setEstado] = React.useState('cargando'); // cargando|ok|error
    const [sigpacCaido, setSigpacCaido] = React.useState(false); // recintos WMS no responden

    React.useEffect(() => {
        if (typeof L === 'undefined' || !mapDivRef.current) {
            setEstado('error');
            return;
        }
        // Crear el mapa centrado en España; el fitBounds lo ajusta al cargar la geometría.
        const map = L.map(mapDivRef.current, { zoomControl: true }).setView([40.0, -3.7], 6);
        mapRef.current = map;

        // Capa base: ortofoto PNOA oficial (IGN) — lo que el agricultor reconoce del SIGPAC.
        L.tileLayer.wms('https://www.ign.es/wms-inspire/pnoa-ma', {
            layers: 'OI.OrthoimageCoverage',
            format: 'image/jpeg',
            attribution: 'PNOA © Instituto Geográfico Nacional',
        }).addTo(map);

        // Capa de recintos SIGPAC oficial (FEGA) — dibuja los perímetros de las parcelas.
        // Endpoint "SIGPAC en la Nube" (sigpac-hubcloud.es). El WMS antiguo
        // wms.mapa.gob.es/sigpac/wms quedó deprecado (devolvía 502). GeoServer
        // exige el nombre de capa cualificado 'AU.Sigpac:recinto', ruta /wms/ows
        // y version 1.3.0. Si el servicio de FEGA se cae, 'tileerror' activa un
        // aviso para que el agricultor sepa que es SIGPAC y no un error de su parcela.
        const capaRecinto = L.tileLayer.wms('https://sigpac-hubcloud.es/wms/ows', {
            layers: 'AU.Sigpac:recinto',
            format: 'image/png',
            transparent: true,
            version: '1.3.0',
            styles: '',
            attribution: 'SIGPAC © FEGA',
        });
        capaRecinto.on('tileerror', () => setSigpacCaido(true));
        capaRecinto.addTo(map);

        // Capa temática Red Natura 2000 (ZEPA + LIC/ZEC) — MITECO/IEPNB.
        // Relevante para fitosanitarios: hay restricciones de uso de productos
        // dentro de espacios protegidos. Apagada por defecto para no tapar la
        // ortofoto; el agricultor la enciende desde el control de capas.
        const capaRedNatura = L.tileLayer.wms('https://geoserver.iepnb.es/geoserver/RN2000/wms', {
            layers: 'rn2000_2024',
            format: 'image/png',
            transparent: true,
            opacity: 0.45,
            attribution: 'Red Natura 2000 © MITECO',
        });

        // Control de capas: casilla para encender/apagar Red Natura 2000.
        L.control.layers(null, { '🛡️ Red Natura 2000 (ZEPA)': capaRedNatura }, {
            collapsed: false, position: 'topright',
        }).addTo(map);

        // Leaflet mide mal el contenedor si se creó dentro del modal; forzar recálculo.
        setTimeout(() => map.invalidateSize(), 100);

        const q = new URLSearchParams({
            provincia: String(parcela.provincia_cod),
            municipio: String(parcela.municipio_cod),
            poligono:  String(parcela.poligono),
            parcela:   String(parcela.parcela_num),
        });
        fetch(`/api/sigpac/recinto-bbox?${q.toString()}`, { credentials: 'include' })
            .then(r => r.ok ? r.json() : Promise.reject())
            .then(data => {
                // Combinar los bbox de todos los recintos (Leaflet usa [lat, lng]).
                const bounds = L.latLngBounds([]);
                (data.recintos || []).forEach(rc => {
                    const [x1, y1, x2, y2] = rc.bbox; // x = lon, y = lat
                    bounds.extend([y1, x1]);
                    bounds.extend([y2, x2]);
                });
                if (!bounds.isValid()) { setEstado('error'); return; }
                map.fitBounds(bounds, { padding: [40, 40], maxZoom: 18 });
                // Marcador en el centro de la parcela: la referencia visible siempre,
                // aunque el overlay WMS de recintos de SIGPAC no responda.
                const c = bounds.getCenter();
                L.circleMarker(c, {
                    radius: 9, color: '#facc15', weight: 3, fillColor: '#eab308', fillOpacity: 0.9,
                }).addTo(map).bindTooltip('Tu parcela', { permanent: false, direction: 'top' });
                setEstado('ok');
            })
            .catch(() => setEstado('error'));

        return () => { map.remove(); mapRef.current = null; };
    }, [parcela]);

    return (
        <div style={{ position:'fixed', inset:0, zIndex:2000, background:'#000', display:'flex', flexDirection:'column' }}>
            <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'12px 16px', background:'#16a34a', color:'#fff', flexShrink:0 }}>
                <div style={{ minWidth:0 }}>
                    <div style={{ fontWeight:700, fontSize:'0.95rem', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>
                        🗺️ {parcela.nombre_finca || 'Mi parcela'}
                    </div>
                    <div style={{ fontSize:'0.72rem', opacity:0.9 }}>
                        Pol. {parcela.poligono} · Parc. {parcela.parcela_num}{parcela.recinto ? ` · Rec. ${parcela.recinto}` : ''}
                    </div>
                </div>
                <button onClick={onClose} aria-label="Cerrar"
                    style={{ background:'rgba(255,255,255,0.2)', border:'none', color:'#fff', borderRadius:8, minWidth:44, minHeight:44, fontSize:'1.2rem', cursor:'pointer', flexShrink:0 }}>
                    ✕
                </button>
            </div>
            <div style={{ flex:1, position:'relative' }}>
                <div ref={mapDivRef} style={{ position:'absolute', inset:0 }} />
                {estado === 'cargando' && (
                    <div style={{ position:'absolute', inset:0, display:'flex', alignItems:'center', justifyContent:'center', background:'rgba(0,0,0,0.4)', color:'#fff', pointerEvents:'none' }}>
                        Cargando mapa…
                    </div>
                )}
                {sigpacCaido && estado !== 'error' && (
                    <div style={{ position:'absolute', top:8, left:8, right:8, background:'#fffbeb', color:'#92400e', border:'1px solid #fcd34d', borderRadius:8, padding:'8px 12px', fontSize:'0.75rem', textAlign:'center', pointerEvents:'none', boxShadow:'0 1px 4px rgba(0,0,0,0.2)' }}>
                        ⚠️ Los perímetros de SIGPAC no están disponibles ahora mismo (servicio de FEGA). Tu parcela está bien; vuelve a intentarlo más tarde.
                    </div>
                )}
                {estado === 'error' && (
                    <div style={{ position:'absolute', left:0, right:0, bottom:0, background:'#fef2f2', color:'#991b1b', padding:'10px 14px', fontSize:'0.78rem', textAlign:'center' }}>
                        No se pudieron obtener las coordenadas de SIGPAC para esta parcela (el servicio puede estar caído). Revisa que el polígono y la parcela sean correctos e inténtalo de nuevo.
                    </div>
                )}
            </div>
        </div>
    );
}

function ScreenParcelas({ campana, showToast }) {
    const { useState, useEffect } = React;

    const [parcelas, setParcelas]   = useState([]);
    const [selected, setSelected]   = useState(null);
    const [showForm, setShowForm]   = useState(false);
    const [tab, setTab]             = useState('parcela');
    const [loading, setLoading]     = useState(true);

    // Parcela form state
    const EMPTY_FORM = {
        nombre_finca:'', comunidad:'07-Castilla-La Mancha',
        provincia_cod:'', provincia_nombre:'',
        municipio_cod:'', municipio_nombre:'',
        poligono:'', parcela_num:'', recinto:'',
        superficie_ha:'', uso_sigpac:'', referencia_cat:'', sistema_explotacion:'Secano',
        masa_agua_cercana:false, notas:'',
    };
    const [form, setForm]   = useState(EMPTY_FORM);
    const [editId, setEditId] = useState(null);
    const [saving, setSaving] = useState(false);
    const [sigpacSyncing, setSigpacSyncing] = useState(false);
    const [verificando, setVerificando] = useState(false);
    const [mapaAbierto, setMapaAbierto] = useState(false);

    // SIGPAC search (edit form)
    const [provincias, setProvincias]     = useState([]);
    const [municipios, setMunicipios]     = useState([]);
    const [poligonos, setPoligonos]       = useState([]);
    const [parcelasSig, setParcelasSig]   = useState([]);
    const [sigpacState, setSigpacState]   = useState('idle'); // idle|loading|ok|error

    // SIGPAC wizard (from detail banner)
    const [wiz, setWiz] = useState(null); // null | { step, prov_cod, prov_nombre, mun_cod, mun_nombre, pol, par }
    const [wizMunicipios, setWizMunicipios] = useState([]);
    const [wizSaving, setWizSaving] = useState(false);

    const openWizard = () => setWiz({ step: 1, prov_cod:'', prov_nombre:'', mun_cod:'', mun_nombre:'', pol:'', par:'', superficie:'', uso:'' });
    const closeWizard = () => { setWiz(null); setWizMunicipios([]); };

    const wizSave = async () => {
        setWizSaving(true);
        try {
            const body = {
                nombre_finca: selected.nombre_finca,
                provincia_cod: wiz.prov_cod, provincia_nombre: wiz.prov_nombre,
                municipio_cod: wiz.mun_cod, municipio_nombre: wiz.mun_nombre,
                poligono: wiz.pol, parcela_num: wiz.par, recinto: '',
                superficie_ha: wiz.superficie || '', uso_sigpac: wiz.uso || '',
                referencia_cat: wiz.ref_cat || '',
                sistema_explotacion: selected.sistema_explotacion || 'Secano',
                masa_agua_cercana: selected.masa_agua_cercana || false,
                notas: selected.notas || '',
            };
            await fetch(`/api/parcelas/${selected.id}`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body), credentials: 'include',
            });
            showToast('✅ Referencia SIGPAC guardada');
            closeWizard();
            fetchParcelas();
            setSelected(p => ({ ...p, ...body }));
        } catch { showToast('Error al guardar'); }
        finally { setWizSaving(false); }
    };

    // Códigos de provincia españoles (estáticos, no dependen de la API SIGPAC)
    const PROV_CODIGOS = {
        'alava':1,'albacete':2,'alicante':3,'almeria':4,'avila':5,'badajoz':6,
        'illes balears':7,'balears':7,'barcelona':8,'burgos':9,'caceres':10,
        'cadiz':11,'castellon':12,'ciudad real':13,'cordoba':14,'la coruna':15,
        'coruna':15,'cuenca':16,'girona':17,'granada':18,'guadalajara':19,
        'gipuzkoa':20,'huelva':21,'huesca':22,'jaen':23,'leon':24,'lleida':25,
        'la rioja':26,'rioja':26,'lugo':27,'madrid':28,'malaga':29,'murcia':30,
        'navarra':31,'ourense':32,'asturias':33,'palencia':34,'las palmas':35,
        'palmas':35,'pontevedra':36,'salamanca':37,'santa cruz de tenerife':38,
        'tenerife':38,'cantabria':39,'segovia':40,'sevilla':41,'soria':42,
        'tarragona':43,'teruel':44,'toledo':45,'valencia':46,'valladolid':47,
        'vizcaya':48,'bizkaia':48,'zamora':49,'zaragoza':50,'ceuta':51,'melilla':52,
    };
    const norm = s => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').trim();

    // Resuelve provincia_cod y municipio_cod para una parcela.
    const _resolveProvMun = async (p, munCache = new Map()) => {
        let provCod = p.provincia_cod || '';
        let munCod  = p.municipio_cod  || '';
        if (!provCod && p.provincia_nombre) {
            const key = norm(p.provincia_nombre);
            const cod = PROV_CODIGOS[key];
            if (cod) { provCod = String(cod); }
            else {
                try {
                    const r = await fetch('/api/sigpac/provincias', { credentials: 'include' });
                    const d = await r.json();
                    const found = (d.features || []).find(f => norm(f.properties?.nombre) === key);
                    provCod = found ? String(found.properties.codigo) : '';
                } catch { /* provCod stays empty */ }
            }
        }
        if (!munCod && provCod && p.municipio_nombre) {
            if (!munCache.has(provCod)) {
                const r = await fetch(`/api/sigpac/municipios?provincia_cod=${provCod}`, { credentials: 'include' });
                const lista = await r.json();
                munCache.set(provCod, Array.isArray(lista) ? lista : []);
            }
            const munNorm = norm(p.municipio_nombre);
            const found = munCache.get(provCod).find(m => norm(m.nombre) === munNorm);
            munCod = found ? String(found.codigo) : '';
        }
        return { provCod, munCod };
    };

    // Obtiene detalle de cada recinto (num, superficie_ha, uso_sigpac) para un pol/par.
    // Usa el endpoint /api/sigpac/recintos-detalle que llama a intersección + Catastro por recinto.
    const _getRecintosDetalle = async (provCod, munCod, pol, par) => {
        try {
            const r = await fetch(
                `/api/sigpac/recintos-detalle?provincia=${provCod}&municipio=${munCod}&poligono=${pol}&parcela=${par}`,
                { credentials: 'include' }
            );
            const d = await r.json();
            if (Array.isArray(d) && d.length > 0) return d;
        } catch { /* fallback below */ }
        return [{ num: 1, superficie_ha: null, uso_sigpac: '' }];
    };

    // Llama a /api/sigpac/datos para un recinto concreto y guarda el resultado en BD.
    const _guardarDatosSigpac = async (parcelaObj, provCod, munCod, recNum) => {
        const params = new URLSearchParams({
            provincia: provCod, municipio: munCod,
            poligono: parcelaObj.poligono, parcela: parcelaObj.parcela_num, recinto: String(recNum),
        });
        const res = await fetch(`/api/sigpac/datos?${params}`, { credentials: 'include' });
        const d = await res.json();
        if (d.error) return null;
        const body = {
            ...parcelaObj,
            provincia_cod: provCod,
            municipio_cod: munCod,
            recinto: String(recNum),
            superficie_ha: d.superficie_ha != null ? d.superficie_ha : parcelaObj.superficie_ha,
            uso_sigpac: d.uso_sigpac || parcelaObj.uso_sigpac,
            referencia_cat: d.referencia_cat || parcelaObj.referencia_cat,
        };
        await fetch(`/api/parcelas/${parcelaObj.id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body), credentials: 'include',
        });
        return body;
    };

    // Resuelve prov/mun y devuelve datos SIGPAC. Usado por "Actualizar todo".
    const _fetchSigpacParaUna = async (p, munCache = new Map()) => {
        const { provCod, munCod } = await _resolveProvMun(p, munCache);
        if (!provCod || !munCod) return { error: 'sin_codigos' };
        const params = new URLSearchParams({
            provincia: provCod, municipio: munCod,
            poligono: p.poligono, parcela: p.parcela_num, recinto: p.recinto || '1',
        });
        const res = await fetch(`/api/sigpac/datos?${params}`, { credentials: 'include' });
        const d = await res.json();
        if (d.error) return { error: d.error };
        return { ok: true, provCod, munCod, superficie_ha: d.superficie_ha, uso_sigpac: d.uso_sigpac };
    };

    const [syncingAll, setSyncingAll] = useState(false);
    const [syncProgress, setSyncProgress] = useState('');
    const [recintosPicker, setRecintosPicker] = useState(null);
    // null | { mode:'detail'|'form', provCod, munCod, poligono, parcela, nums:[1,3,4] }

    const [resumenMulti, setResumenMulti] = useState(null);
    // null | { ctx, recs, grupos:[{uso, nums, nombre, aceptado}], creando:bool }

    // "OV-Olivar" → "Olivar" (mismo criterio que el picker)
    const usoLabel = u => ((u || '').split('-').slice(1).join('-').trim() || u || '');

    // Agrupa recintos por uso SIGPAC; solo grupos de 2+ generan UHC propuesta.
    const abrirResumenMulti = () => {
        const ctx = recintosPicker;
        const recs = ctx.recintos || [];
        const by = new Map();
        recs.forEach(r => {
            const uso = (r.uso_sigpac || '').trim();
            if (!uso) return;
            if (!by.has(uso)) by.set(uso, []);
            by.get(uso).push(r.num);
        });
        const grupos = [...by.entries()]
            .filter(([, nums]) => nums.length >= 2)
            .map(([uso, nums]) => ({
                uso, nums,
                nombre: `${usoLabel(uso)} — Pol ${ctx.poligono} Par ${ctx.parcela}`,
                aceptado: true,
            }));
        setRecintosPicker(null);
        setResumenMulti({ ctx, recs, grupos, creando: false });
    };

    const confirmarMultirecinto = async () => {
        const rm = resumenMulti;
        if (rm.grupos.some(g => g.aceptado && !g.nombre.trim())) {
            showToast('Ponle un nombre a cada grupo (o desmárcalo)');
            return;
        }
        setResumenMulti(r => ({ ...r, creando: true }));
        const body = {
            nombre_base: (form.nombre_finca || '').trim() || `Pol ${rm.ctx.poligono} Par ${rm.ctx.parcela}`,
            comunidad: form.comunidad,
            provincia_cod: rm.ctx.provCod, provincia_nombre: form.provincia_nombre,
            municipio_cod: rm.ctx.munCod, municipio_nombre: form.municipio_nombre,
            poligono: rm.ctx.poligono, parcela_num: rm.ctx.parcela,
            sistema_explotacion: form.sistema_explotacion || 'Secano',
            campana: campana || '2025/2026',
            recintos: rm.recs.map(r => ({ num: r.num, uso_sigpac: r.uso_sigpac || '', superficie_ha: r.superficie_ha })),
            uhcs: rm.grupos.filter(g => g.aceptado)
                .map(g => ({ nombre: g.nombre.trim(), cultivo: usoLabel(g.uso), recintos: g.nums })),
        };
        try {
            const res = await fetch('/api/parcelas/alta-multirecinto', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body), credentials: 'include',
            });
            const d = await res.json().catch(() => ({}));
            if (!res.ok || !d.ok) {
                showToast(`⚠️ ${d.error || 'No se pudieron crear las parcelas'}`);
                setResumenMulti(r => r ? { ...r, creando: false } : r);
                return;
            }
            setResumenMulti(null);
            setShowForm(false);
            fetchParcelas();
            const np = d.data?.parcelas || 0, ng = d.data?.uhcs || 0;
            showToast(`✅ Creadas ${np} parcelas${ng ? ` y ${ng} grupo${ng > 1 ? 's' : ''}` : ''}`);
        } catch {
            showToast('Error de conexión');
            setResumenMulti(r => r ? { ...r, creando: false } : r);
        }
    };

    // Handler: usuario elige recinto del picker
    const onPickRecinto = async (recNum) => {
        const ctx = recintosPicker;
        setRecintosPicker(null);
        if (ctx.mode === 'detail') {
            setSigpacSyncing(true);
            try {
                const body = await _guardarDatosSigpac(selected, ctx.provCod, ctx.munCod, recNum);
                if (!body) { showToast('SIGPAC no devolvió datos para ese recinto'); return; }
                setSelected(body);
                fetchParcelas();
                showToast('✅ Datos SIGPAC actualizados');
            } catch { showToast('Error al consultar SIGPAC'); }
            finally { setSigpacSyncing(false); }
        } else {
            setSigpacState('loading');
            try {
                const rec = String(recNum);
                const res = await fetch(
                    `/api/sigpac/datos?provincia=${ctx.provCod}&municipio=${ctx.munCod}&poligono=${ctx.poligono}&parcela=${ctx.parcela}&recinto=${rec}`,
                    { credentials: 'include' }
                );
                const d = await res.json();
                const sup = d.superficie_ha ? String(d.superficie_ha) : '';
                const uso = d.uso_sigpac || '';
                if (sup || uso) {
                    setForm(f => ({ ...f, recinto: rec, superficie_ha: sup || f.superficie_ha, uso_sigpac: uso || f.uso_sigpac }));
                    setSigpacState('ok');
                    showToast(`✅ SIGPAC: ${[sup && `${sup} ha`, uso].filter(Boolean).join(' · ')}`);
                } else {
                    setSigpacState('error');
                    showToast('Sin datos para ese recinto');
                }
            } catch { setSigpacState('error'); showToast('Error al consultar SIGPAC'); }
        }
    };

    const syncSigpac = async () => {
        if (!selected.poligono || !selected.parcela_num) return;
        setSigpacSyncing(true);
        try {
            const { provCod, munCod } = await _resolveProvMun(selected);
            if (!provCod || !munCod) { showToast('⚠️ No se encontró el código de provincia/municipio'); return; }
            const recintos = await _getRecintosDetalle(provCod, munCod, selected.poligono, selected.parcela_num);
            if (recintos.length > 1) {
                setRecintosPicker({ mode:'detail', provCod, munCod, poligono: selected.poligono, parcela: selected.parcela_num, recintos });
                return;
            }
            const body = await _guardarDatosSigpac(selected, provCod, munCod, recintos[0].num || 1);
            if (!body) { showToast('⚠️ SIGPAC no devolvió datos'); return; }
            setSelected(body);
            fetchParcelas();
            showToast('✅ Datos SIGPAC actualizados');
        } catch { showToast('Error al consultar SIGPAC'); }
        finally { setSigpacSyncing(false); }
    };

    const reVerificarSigpac = async () => {
        if (!selected || !navigator.onLine) return;
        setVerificando(true);
        try {
            const r = await fetch(`/api/parcelas/${selected.id}/verificar-sigpac`, { method:'POST', credentials:'include' });
            const d = await r.json().catch(() => ({}));
            if (!r.ok || !d.ok) {
                showToast(`⚠️ ${d.error || 'No se pudo verificar con SIGPAC'}`);
            } else {
                setSelected(prev => prev ? { ...prev,
                    sigpac_superficie_ha: d.sigpac_superficie_ha,
                    sigpac_verificado_en: d.sigpac_verificado_en,
                    sigpac_estado: d.estado,
                    sigpac_diferencia_pct: d.diferencia_pct,
                } : prev);
                fetchParcelas();
            }
        } catch {
            showToast('⚠️ Error de conexión al verificar con SIGPAC');
        }
        setVerificando(false);
    };

    const syncAll = async () => {
        const candidatas = parcelas.filter(p => p.poligono && p.parcela_num);
        if (!candidatas.length) { showToast('No hay parcelas con polígono asignado'); return; }
        setSyncingAll(true);
        const munCache = new Map();
        let ok = 0, skip = 0;
        for (let i = 0; i < candidatas.length; i++) {
            const p = candidatas[i];
            setSyncProgress(`${i + 1}/${candidatas.length}`);
            try {
                const result = await _fetchSigpacParaUna(p, munCache);
                if (result.error) { skip++; continue; }
                const body = {
                    ...p,
                    provincia_cod: result.provCod,
                    municipio_cod: result.munCod,
                    superficie_ha: result.superficie_ha != null ? result.superficie_ha : p.superficie_ha,
                    uso_sigpac:    result.uso_sigpac || p.uso_sigpac,
                };
                await fetch(`/api/parcelas/${p.id}`, {
                    method: 'PUT', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body), credentials: 'include',
                });
                if (selected && selected.id === p.id) setSelected(body);
                ok++;
            } catch { skip++; }
        }
        setSyncingAll(false);
        setSyncProgress('');
        fetchParcelas();
        showToast(skip ? `SIGPAC: ${ok} actualizadas, ${skip} sin datos` : `✅ ${ok} parcelas actualizadas`);
    };

    const wizNext = async () => {
        if (wiz.step === 1) {
            if (!wiz.prov_cod) { showToast('Selecciona una provincia'); return; }
            const res = await fetch(`/api/sigpac/municipios?provincia_cod=${wiz.prov_cod}`, { credentials: 'include' });
            const data = await res.json();
            setWizMunicipios(Array.isArray(data?.data || data) ? (data?.data || data) : []);
            setWiz(w => ({ ...w, step: 2, mun_cod:'', mun_nombre:'' }));
        } else if (wiz.step === 2) {
            if (!wiz.mun_cod) { showToast('Selecciona un municipio'); return; }
            setWiz(w => ({ ...w, step: 3 }));
        } else if (wiz.step === 3) {
            if (!wiz.pol) { showToast('Introduce el número de polígono'); return; }
            setWiz(w => ({ ...w, step: 4 }));
        } else if (wiz.step === 4) {
            if (!wiz.par) { showToast('Introduce el número de parcela'); return; }
            // Consultar SIGPAC + Catastro para prellenar paso 5
            setWizSaving(true);
            try {
                const res = await fetch(`/api/sigpac/datos?provincia=${wiz.prov_cod}&municipio=${wiz.mun_cod}&poligono=${wiz.pol}&parcela=${wiz.par}`, { credentials: 'include' });
                const d = await res.json();
                setWiz(w => ({
                    ...w, step: 5,
                    superficie: d.superficie_ha ? String(d.superficie_ha) : '',
                    uso: d.uso_sigpac || '',
                    cultivo_catastro: d.cultivo_catastro || '',
                    ref_cat: d.referencia_cat || '',
                    num_recintos: d.num_recintos || 0,
                }));
            } catch {
                setWiz(w => ({ ...w, step: 5 }));
            } finally { setWizSaving(false); }
        } else if (wiz.step === 5) {
            await wizSave();
        }
    };

    const fetchParcelas = () => {
        setLoading(true);
        fetch('/api/parcelas', { credentials: 'include' }).then(r => r.json()).then(data => {
            const list = Array.isArray(data) ? data : [];
            setParcelas(list);
            setLoading(false);
            if (list.length > 0 && window.OfflineDB) {
                window.OfflineDB.cacheParcelas(list);
            }
        }).catch(() => {
            if (window.OfflineDB) {
                window.OfflineDB.getCachedParcelas().then(cached => {
                    setParcelas(cached);
                    setLoading(false);
                });
            } else {
                setLoading(false);
            }
        });
    };
    useEffect(() => { fetchParcelas(); }, []);


    // SIGPAC: load provincias on form open
    useEffect(() => {
        if (!showForm) return;
        fetch('/api/sigpac/provincias').then(r => r.json()).then(data => {
            const arr = data?.data || data || [];
            setProvincias(Array.isArray(arr) ? arr : []);
        }).catch(() => {});
    }, [showForm]);

    const loadMunicipios = (prov_cod) => {
        if (!prov_cod) return;
        fetch(`/api/sigpac/municipios?provincia_cod=${prov_cod}`)
            .then(r => r.json()).then(data => {
                setMunicipios(Array.isArray(data?.data||data) ? (data?.data||data) : []);
                setPoligonos([]); setParcelasSig([]);
            }).catch(() => {});
    };

    const loadPoligonos = (prov_cod, mun_cod) => {
        if (!prov_cod || !mun_cod) return;
        fetch(`/api/sigpac/poligonos?provincia_cod=${prov_cod}&municipio_cod=${mun_cod}`)
            .then(r => r.json()).then(data => {
                setPoligonos(Array.isArray(data?.data||data) ? (data?.data||data) : []);
                setParcelasSig([]);
            }).catch(() => {});
    };

    const loadParcelasSigpac = (prov_cod, mun_cod, pol) => {
        if (!pol) return;
        fetch(`/api/sigpac/parcelas?provincia_cod=${prov_cod}&municipio_cod=${mun_cod}&poligono=${pol}`)
            .then(r => r.json()).then(data => {
                setParcelasSig(Array.isArray(data?.data||data) ? (data?.data||data) : []);
            }).catch(() => {});
    };

    const buscarSigpac = async () => {
        if (!form.poligono || !form.parcela_num) {
            showToast('Introduce polígono y parcela para buscar');
            return;
        }
        if (!form.provincia_cod || !form.municipio_cod) {
            showToast('Selecciona provincia y municipio primero');
            return;
        }
        setSigpacState('loading');
        try {
            // Detectar recintos automáticamente
            const recintos = await _getRecintosDetalle(form.provincia_cod, form.municipio_cod, form.poligono, form.parcela_num);
            if (recintos.length > 1) {
                setRecintosPicker({ mode:'form', provCod: form.provincia_cod, munCod: form.municipio_cod, poligono: form.poligono, parcela: form.parcela_num, recintos });
                setSigpacState('idle');
                return;
            }
            const rec = String(recintos[0]?.num || form.recinto || '1');
            const res = await fetch(
                `/api/sigpac/datos?provincia=${form.provincia_cod}&municipio=${form.municipio_cod}&poligono=${form.poligono}&parcela=${form.parcela_num}&recinto=${rec}`,
                { credentials: 'include' }
            );
            const d = await res.json();
            if (d.error) { setSigpacState('error'); showToast(`Error SIGPAC: ${d.error}`); return; }
            const sup = d.superficie_ha ? String(d.superficie_ha) : '';
            const uso = d.uso_sigpac || '';
            const refCat = d.referencia_cat || '';
            if (sup || uso) {
                setForm(f => ({ ...f, recinto: rec, superficie_ha: sup || f.superficie_ha, uso_sigpac: uso || f.uso_sigpac, referencia_cat: refCat || f.referencia_cat }));
                setSigpacState('ok');
                showToast(`✅ SIGPAC: ${[sup && `${sup} ha`, uso].filter(Boolean).join(' · ')}`);
            } else {
                setSigpacState('error');
                showToast(`Sin datos SIGPAC. prov=${form.provincia_cod} mun=${form.municipio_cod} pol=${form.poligono} par=${form.parcela_num}`);
            }
        } catch {
            setSigpacState('error');
            showToast('Error al conectar con SIGPAC');
        }
    };

    const openNew = () => {
        setForm(EMPTY_FORM); setEditId(null);
        setShowForm(true); setSigpacState('idle');
        setProvincias([]); setMunicipios([]); setPoligonos([]); setParcelasSig([]);
    };
    const openEdit = async (p) => {
        const norm = s => (s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').trim();

        // Resolver provincia_cod desde nombre si falta
        let provCod = p.provincia_cod || '';
        if (!provCod && p.provincia_nombre) {
            const found = PROVINCIAS_ES.find(pr => norm(pr.nombre) === norm(p.provincia_nombre));
            if (found) provCod = found.cod;
        }

        // Resolver municipio_cod desde nombre si falta
        let munCod = p.municipio_cod || '';
        let munList = [];
        if (provCod) {
            try {
                const r = await fetch(`/api/sigpac/municipios?provincia_cod=${provCod}`, { credentials: 'include' });
                munList = await r.json();
                setMunicipios(Array.isArray(munList) ? munList : []);
                if (!munCod && p.municipio_nombre) {
                    const found = (munList||[]).find(m => norm(m.nombre) === norm(p.municipio_nombre));
                    if (found) munCod = String(found.codigo);
                }
            } catch {}
        }

        setForm({
            nombre_finca: p.nombre_finca||'', comunidad: p.comunidad||'07-Castilla-La Mancha',
            provincia_cod: provCod, provincia_nombre: p.provincia_nombre||'',
            municipio_cod: munCod, municipio_nombre: p.municipio_nombre||'',
            poligono: p.poligono||'', parcela_num: p.parcela_num||'', recinto: p.recinto||'',
            superficie_ha: p.superficie_ha||'', uso_sigpac: p.uso_sigpac||'',
            referencia_cat: p.referencia_cat||'',
            sistema_explotacion: p.sistema_explotacion||'Secano',
            masa_agua_cercana: !!p.masa_agua_cercana, notas: p.notas||'',
        });
        setPoligonos([]); setParcelasSig([]);
        setEditId(p.id); setShowForm(true); setSigpacState('idle');
    };

    const saveParcela = async () => {
        if (!form.nombre_finca.trim()) {
            showToast('Escribe un nombre para la parcela');
            return;
        }
        setSaving(true);
        const method = editId ? 'PUT' : 'POST';
        const url = editId ? `/api/parcelas/${editId}` : '/api/parcelas';
        let savedId = editId;
        try {
            const res = await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(form), credentials: 'include' });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                showToast(`❌ Error al guardar: ${err.error || res.status}`);
                setSaving(false);
                return;
            }
            if (!editId) {
                const data = await res.json().catch(() => ({}));
                savedId = data.id;
            }
        } catch {
            showToast('❌ Error de conexión al guardar');
            setSaving(false);
            return;
        }
        showToast(editId ? '✅ Parcela actualizada' : '✅ Parcela añadida');
        setSaving(false); setShowForm(false);
        fetchParcelas();
        if (editId) {
            setSelected(prev => prev ? { ...prev, ...form, id: prev.id } : prev);
        } else {
            setSelected(null);
        }
        // Auto-verificación con SIGPAC (no bloquea; refresca lista y ficha al volver).
        if (savedId && form.poligono && form.parcela_num && navigator.onLine) {
            fetch(`/api/parcelas/${savedId}/verificar-sigpac`, { method:'POST', credentials:'include' })
                .then(r => r.ok ? r.json() : null)
                .then(d => {
                    if (d && d.ok) {
                        setSelected(prev => (prev && prev.id === savedId) ? { ...prev,
                            sigpac_superficie_ha: d.sigpac_superficie_ha,
                            sigpac_verificado_en: d.sigpac_verificado_en,
                            sigpac_estado: d.estado,
                            sigpac_diferencia_pct: d.diferencia_pct,
                        } : prev);
                    }
                    fetchParcelas();
                })
                .catch(() => {});
        }
    };

    const deleteParcela = async (p) => {
        if (!confirm(`¿Eliminar "${p.nombre_finca}"? Los registros asociados se mantendrán.`)) return;
        await fetch(`/api/parcelas/${p.id}`, { method: 'DELETE', credentials: 'include' });
        showToast('Parcela eliminada');
        setSelected(null);
        fetchParcelas();
    };

    // PAC eligibility label
    const pacLabel = (uso) => {
        if (!uso) return null;
        const c = uso.split('-')[0].trim().toUpperCase();
        const PAC = ['IV','TA','TH','OP','CF','CI','CS','CV','FF','FL','FS','FV','FY','OC','OF','OV','VF','VI','VO','PA','PR','PS'];
        const ok = PAC.includes(c) && !uso.toUpperCase().includes('NO PAC');
        return <span className={`chip ${ok ? 'chip-green' : 'chip-grey'}`}>{ok ? '✓ PAC' : '— No PAC'}</span>;
    };

    const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;

    return (
        <div style={{ height: 'calc(100vh - 60px)', display: 'flex', overflow: 'hidden' }}>
            {/* ── LEFT: parcelas list ── */}
            <div style={{
                width: selected && !isMobile ? 320 : '100%',
                minWidth: selected && !isMobile ? 320 : 0,
                borderRight: selected && !isMobile ? '1px solid #e5e7eb' : 'none',
                display: selected && isMobile ? 'none' : 'flex',
                flexDirection: 'column', background: '#f8f9fb', overflow: 'hidden',
            }}>
                {/* Header */}
                <div style={{ background:'linear-gradient(135deg,#15785A,#1D9E75)', padding:'52px 16px 16px' }}>
                    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                        <div>
                            <h1 style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.3rem', color:'#fff', margin:'0 0 2px' }}>
                                Mis Parcelas
                            </h1>
                            <p style={{ color:'rgba(255,255,255,0.65)', fontSize:'0.78rem', margin:0 }}>
                                {loading ? '…' : `${parcelas.length} parcela(s) visibles`}
                            </p>
                        </div>
                        <div style={{ display:'flex', gap:8, alignItems:'center' }}>
                            {parcelas.length > 0 && (
                                <button
                                    onClick={syncAll}
                                    disabled={syncingAll}
                                    style={{ padding:'10px 12px', fontSize:'0.78rem', fontWeight:700,
                                        background: syncingAll ? '#6b7280' : '#1e3a5f',
                                        color:'#fff', border:'none', borderRadius:10, cursor: syncingAll ? 'default' : 'pointer' }}
                                >
                                    {syncingAll ? `⏳ ${syncProgress}` : '⟳ SIGPAC'}
                                </button>
                            )}
                            <button className="btn-primary" style={{ padding:'10px 14px', fontSize:'0.82rem' }} onClick={openNew}>
                                + Nueva
                            </button>
                            <HelpButton screenId="parcelas" />
                        </div>
                    </div>
                </div>

                {/* List */}
                <div style={{ flex:1, overflowY:'auto' }}>
                    {loading ? (
                        <div style={{ textAlign:'center', color:'#9ca3af', padding:'48px 0' }}>Cargando parcelas…</div>
                    ) : parcelas.length === 0 ? (
                        <div style={{ textAlign:'center', padding:'48px 16px', color:'#9ca3af' }}>
                            <div style={{ fontSize:40, marginBottom:8 }}>🗺️</div>
                            <p style={{ fontFamily:'Manrope', fontWeight:700, color:'#374151', margin:'0 0 6px' }}>Sin parcelas</p>
                            <p style={{ fontSize:'0.82rem' }}>Pulsa "+ Nueva" para añadir tu primera parcela</p>
                        </div>
                    ) : parcelas.map(p => (
                        <div key={p.id} className="list-row"
                            style={{ background: selected?.id===p.id ? '#fff7ed' : undefined, cursor:'pointer' }}
                            onClick={() => { setSelected(p); setTab('parcela'); }}>
                            <div className="accent-bar" style={{ background:'#1D9E75' }} />
                            <div style={{ flex:1, minWidth:0 }}>
                                <div style={{ fontWeight:700, fontSize:'0.9rem', color:'#111827' }}>{p.nombre_finca}</div>
                                {p.poligono ? (
                                    <div style={{ fontSize:'0.75rem', color:'#6b7280', marginTop:2 }}>
                                        Pol <strong>{p.poligono}</strong> · Par <strong>{p.parcela_num}</strong>{p.recinto ? ` · Rec ${p.recinto}` : ''}
                                    </div>
                                ) : (
                                    <div style={{ fontSize:'0.72rem', color:'#d97706', marginTop:2 }}>Sin datos SIGPAC</div>
                                )}
                                <div style={{ display:'flex', gap:6, marginTop:5, alignItems:'center', flexWrap:'wrap' }}>
                                    {pacLabel(p.uso_sigpac)}
                                    {p.superficie_ha ? <span className="chip chip-grey">{p.superficie_ha} ha</span> : null}
                                    {p.poligono && !p.uso_sigpac && (
                                        <span className="chip" style={{ background:'#fef3c7', color:'#92400e', border:'1px solid #fde68a', fontSize:'0.7rem' }}>⚠ Sin uso</span>
                                    )}
                                    {p.poligono && !p.superficie_ha && (
                                        <span className="chip" style={{ background:'#fef3c7', color:'#92400e', border:'1px solid #fde68a', fontSize:'0.7rem' }}>⚠ Sin sup.</span>
                                    )}
                                    {p.poligono && sigpacBadge(p.sigpac_estado)}
                                </div>
                            </div>
                            <span style={{ color:'#d1d5db', fontSize:18 }}>›</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* ── RIGHT: detail / form ── */}
            {selected && (
                <div style={{ flex:1, overflowY:'auto', background:'#fff', display:'flex', flexDirection:'column' }}>
                    {/* Detail header */}
                    <div style={{ background:'linear-gradient(135deg,#15785A,#1D9E75)', padding:'20px 16px 0' }}>
                        <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:12 }}>
                            <button className="back-btn" onClick={() => setSelected(null)} style={{ margin:0 }}>←</button>
                            <div>
                                <div style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', color:'#fff' }}>
                                    {selected.nombre_finca}
                                </div>
                                <div style={{ fontSize:'0.75rem', color:'rgba(255,255,255,0.65)' }}>
                                    {selected.municipio_nombre} · Pol {selected.poligono} / Par {selected.parcela_num}
                                </div>
                            </div>
                            <div style={{ marginLeft:'auto', display:'flex', gap:8 }}>
                                <button onClick={() => openEdit(selected)} style={{ background:'rgba(255,255,255,0.15)', border:'none', borderRadius:8, padding:'8px 12px', color:'#fff', cursor:'pointer', fontSize:'0.82rem', fontWeight:700 }}>✏️ Editar</button>
                                <button onClick={() => deleteParcela(selected)} style={{ background:'rgba(239,68,68,0.25)', border:'none', borderRadius:8, padding:'8px 12px', color:'#fff', cursor:'pointer', fontSize:'0.82rem', fontWeight:700 }}>🗑</button>
                            </div>
                        </div>
                        {/* Tabs */}
                        <div style={{ display:'flex', gap:0, borderTop:'1px solid rgba(255,255,255,0.15)' }}>
                            {[['parcela','📍 Parcela']].map(([id,label]) => (
                                <button key={id} onClick={() => setTab(id)} style={{
                                    background:'none', border:'none', borderBottom: tab===id ? '2px solid #fff' : '2px solid transparent',
                                    padding:'12px 16px', cursor:'pointer', color: tab===id ? '#fff' : 'rgba(255,255,255,0.6)',
                                    fontWeight: tab===id ? 700 : 500, fontSize:'0.85rem', fontFamily:'Work Sans',
                                }}>
                                    {label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Tab content */}
                    <div style={{ padding:'20px 16px', flex:1 }}>
                        {tab === 'parcela' && (
                            <div>
                                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginBottom:16 }}>
                                    {[
                                        ['Polígono', selected.poligono, false],
                                        ['Parcela', selected.parcela_num, false],
                                        ['Recinto', selected.recinto, false],
                                        ['Superficie', selected.superficie_ha ? `${selected.superficie_ha} ha` : '', true],
                                        ['Uso SIGPAC', selected.uso_sigpac, true],
                                        ['Ref. catastral', selected.referencia_cat, false],
                                        ['Sistema explot.', selected.sistema_explotacion, false],
                                        ['Masa agua <50m', selected.masa_agua_cercana ? 'Sí ⚠️' : 'No', false],
                                        ['Municipio', selected.municipio_nombre, false],
                                        ['Provincia', selected.provincia_nombre, false],
                                    ].map(([k, v, editable]) => {
                                        const needsInput = editable && !v;
                                        return (
                                            <div key={k}
                                                onClick={needsInput ? () => openEdit(selected) : undefined}
                                                style={{
                                                    background: needsInput ? '#fffbeb' : '#f8f9fb',
                                                    borderRadius: 10, padding: '12px',
                                                    border: needsInput ? '1.5px dashed #f59e0b' : '1.5px solid transparent',
                                                    cursor: needsInput ? 'pointer' : 'default',
                                                }}>
                                                <div style={{ fontSize:'0.65rem', fontWeight:700, color: needsInput ? '#92400e' : '#6b7280', textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:4 }}>{k}</div>
                                                {needsInput ? (
                                                    <div>
                                                        <div style={{ fontWeight:700, color:'#d97706', fontSize:'0.9rem' }}>Sin dato</div>
                                                        <div style={{ fontSize:'0.68rem', color:'#b45309', marginTop:2 }}>Toca para añadir →</div>
                                                    </div>
                                                ) : (
                                                    <div style={{ fontWeight:700, color:'#111827', fontSize:'0.9rem' }}>{v || '—'}</div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                                {selected.poligono && selected.parcela_num && (
                                    <div style={{ background:'#f8f9fb', border:'1px solid #e5e7eb', borderRadius:10, padding:'12px 14px', marginBottom:12 }}>
                                        <div style={{ display:'flex', alignItems:'center', gap:8, flexWrap:'wrap' }}>
                                            <span style={{ fontSize:'0.7rem', fontWeight:700, color:'#6b7280', textTransform:'uppercase', letterSpacing:'0.05em' }}>Verificación SIGPAC</span>
                                            {sigpacBadge(selected.sigpac_estado)}
                                            <button onClick={reVerificarSigpac} disabled={verificando || !navigator.onLine}
                                                title={!navigator.onLine ? 'Necesitas conexión para verificar con SIGPAC' : ''}
                                                style={{ marginLeft:'auto', background:'#16a34a', border:'none', borderRadius:8, padding:'8px 12px', color:'#fff', cursor:(verificando||!navigator.onLine)?'default':'pointer', fontWeight:700, fontSize:'0.78rem', opacity:(verificando||!navigator.onLine)?0.6:1 }}>
                                                {verificando ? '…' : '↻ Re-verificar'}
                                            </button>
                                        </div>
                                        {selected.sigpac_superficie_ha != null && (
                                            <div style={{ fontSize:'0.78rem', color:'#374151', marginTop:8 }}>
                                                SIGPAC: <strong>{selected.sigpac_superficie_ha} ha</strong>
                                                {selected.superficie_ha ? <> · tu dato: {selected.superficie_ha} ha</> : null}
                                                {selected.sigpac_diferencia_pct != null ? <> ({selected.sigpac_diferencia_pct > 0 ? '+' : ''}{selected.sigpac_diferencia_pct}%)</> : null}
                                            </div>
                                        )}
                                        {selected.sigpac_estado === 'no_encontrada' && (
                                            <div style={{ fontSize:'0.78rem', color:'#92400e', marginTop:8 }}>
                                                SIGPAC no encuentra esta parcela. Revisa el polígono, la parcela y el recinto.
                                            </div>
                                        )}
                                    </div>
                                )}
                                {selected.provincia_cod && selected.municipio_cod && selected.poligono && selected.parcela_num && (
                                    <button onClick={() => setMapaAbierto(true)}
                                        style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:8, width:'100%', minHeight:48, background:'#16a34a', color:'#fff', border:'none', borderRadius:10, padding:'12px', marginBottom:12, fontWeight:700, fontSize:'0.9rem', cursor:'pointer', fontFamily:'inherit' }}>
                                        🗺️ Ver mi parcela en el mapa
                                    </button>
                                )}
                                {selected.provincia_cod && selected.municipio_cod && selected.poligono && selected.parcela_num && (
                                    <div style={{ fontSize:'0.68rem', color:'#6b7280', textAlign:'center', marginTop:-6, marginBottom:12 }}>
                                        Ortofoto oficial (PNOA) con los recintos de SIGPAC. Se abre dentro de la app.
                                    </div>
                                )}
                                {selected.superficie_ha && (
                                    <div style={{ background:'#eff6ff', border:'1px solid #bfdbfe', borderRadius:10, padding:'10px 12px', marginBottom:12, display:'flex', gap:8, alignItems:'flex-start' }}>
                                        <span style={{ fontSize:'0.9rem', flexShrink:0 }}>ℹ️</span>
                                        <div style={{ fontSize:'0.75rem', color:'#1e40af', lineHeight:1.5 }}>
                                            Si esta parcela tiene varios recintos, la superficie mostrada es la <strong>suma total de la parcela catastral</strong>. SIGPAC no devuelve la superficie desglosada por recinto.
                                        </div>
                                    </div>
                                )}
                                {selected.poligono && selected.parcela_num && (!selected.superficie_ha || !selected.uso_sigpac) && (
                                    <div style={{ background:'#f0fdf4', border:'1px solid #86efac', borderRadius:10, padding:'14px', marginBottom:12, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                                        <div>
                                            <div style={{ fontWeight:700, fontSize:'0.85rem', color:'#166534' }}>Superficie o uso sin datos</div>
                                            <div style={{ fontSize:'0.75rem', color:'#15803d', marginTop:2 }}>Introdúcelos manualmente o actualiza desde SIGPAC</div>
                                        </div>
                                        <button onClick={syncSigpac} disabled={sigpacSyncing} style={{ background:'#16a34a', border:'none', borderRadius:8, padding:'8px 12px', color:'#fff', cursor: sigpacSyncing ? 'default' : 'pointer', fontWeight:700, fontSize:'0.78rem', opacity: sigpacSyncing ? 0.6 : 1 }}>
                                            {sigpacSyncing ? '…' : '🔄 Actualizar'}
                                        </button>
                                    </div>
                                )}
                                {!selected.poligono && (
                                    <div style={{ background:'#fffbeb', border:'1px solid #fde68a', borderRadius:10, padding:'14px', marginBottom:12, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                                        <div>
                                            <div style={{ fontWeight:700, fontSize:'0.85rem', color:'#92400e' }}>Sin referencia SIGPAC</div>
                                            <div style={{ fontSize:'0.75rem', color:'#78350f', marginTop:2 }}>Necesaria para el PDF oficial</div>
                                        </div>
                                        <button onClick={openWizard} style={{ background:'#f59e0b', border:'none', borderRadius:8, padding:'8px 12px', color:'#fff', cursor:'pointer', fontWeight:700, fontSize:'0.78rem' }}>
                                            Añadir
                                        </button>
                                    </div>
                                )}
                                {selected.notas && (
                                    <div style={{ background:'#fffbeb', border:'1px solid #fde68a', borderRadius:10, padding:'12px', fontSize:'0.84rem', color:'#374151' }}>
                                        📝 {selected.notas}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ── Mapa SIGPAC embebido ── */}
            {mapaAbierto && selected && (
                <MapaSigpacModal parcela={selected} onClose={() => setMapaAbierto(false)} />
            )}

            {/* ── Parcela Form Modal ── */}
            {showForm && (
                <div className="overlay" style={{ alignItems:'center', justifyContent:'center' }} onClick={() => setShowForm(false)}>
                    <div style={{
                        background:'#fff', borderRadius:20, maxWidth:640, width:'calc(100% - 24px)',
                        maxHeight:'92vh', overflowY:'auto', animation:'scaleIn 0.2s ease',
                    }} onClick={e => e.stopPropagation()}>
                        {/* Form header */}
                        <div style={{ background:'linear-gradient(135deg,#15785A,#1D9E75)', padding:'20px 20px 20px', borderRadius:'20px 20px 0 0' }}>
                            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                                <h2 style={{ fontFamily:'Manrope', fontWeight:800, color:'#fff', fontSize:'1.15rem', margin:0 }}>
                                    {editId ? '✏️ Editar parcela' : '➕ Nueva parcela'}
                                </h2>
                                <button onClick={() => setShowForm(false)} style={{ background:'rgba(255,255,255,0.15)', border:'none', borderRadius:'50%', width:36, height:36, color:'#fff', cursor:'pointer', fontSize:18 }}>✕</button>
                            </div>
                        </div>

                        <div style={{ padding:'20px' }}>
                            {/* Nombre finca */}
                            <div style={{ marginBottom:14 }}>
                                <label className="field-label">Nombre de la finca *</label>
                                <input className="input-field" value={form.nombre_finca} onChange={e => setForm(f=>({...f,nombre_finca:e.target.value}))} />
                            </div>

                            {/* SIGPAC */}
                            <div style={{ marginBottom:14 }}>
                                <div style={{ background:'#f0fdf4', borderRadius:12, padding:'14px', border:'1px solid #d1fae5' }}>
                                    <div style={{ fontFamily:'Manrope', fontWeight:700, fontSize:'0.85rem', color:'#065f46', marginBottom:12 }}>🗺 Datos SIGPAC</div>
                                    <div className="responsive-grid cols-2" style={{ gap:10 }}>
                                            {/* Provincia */}
                                            <div>
                                                <label className="field-label">Provincia</label>
                                                <select className="input-field"
                                                    value={form.provincia_cod}
                                                    onChange={e => {
                                                        const opt = PROVINCIAS_ES.find(p => p.cod === e.target.value);
                                                        setForm(f=>({
                                                            ...f,
                                                            provincia_cod: e.target.value,
                                                            provincia_nombre: opt?.nombre || '',
                                                            municipio_cod: '',
                                                            municipio_nombre: '',
                                                        }));
                                                        setMunicipios([]);
                                                        setPoligonos([]);
                                                        setParcelasSig([]);
                                                        loadMunicipios(e.target.value);
                                                    }}>
                                                    <option value="">Seleccionar provincia…</option>
                                                    {PROVINCIAS_ES.map(p => (
                                                        <option key={p.cod} value={p.cod}>{p.nombre}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            {/* Municipio */}
                                            <div>
                                                <label className="field-label">Municipio</label>
                                                <select className="input-field"
                                                    value={form.municipio_cod}
                                                    disabled={!form.provincia_cod || municipios.length === 0}
                                                    onChange={e => {
                                                        const opt = municipios.find(m => String(m.codigo) === e.target.value);
                                                        const nombre = opt?.nombre ? opt.nombre.charAt(0) + opt.nombre.slice(1).toLowerCase() : '';
                                                        setForm(f=>({...f, municipio_cod:e.target.value, municipio_nombre: nombre}));
                                                        setPoligonos([]);
                                                        setParcelasSig([]);
                                                        loadPoligonos(form.provincia_cod, e.target.value);
                                                    }}>
                                                    <option value="">
                                                        {!form.provincia_cod
                                                            ? 'Elige provincia primero'
                                                            : municipios.length === 0
                                                                ? 'Cargando…'
                                                                : 'Seleccionar municipio…'}
                                                    </option>
                                                    {municipios.map(m => {
                                                        const pretty = m.nombre.charAt(0) + m.nombre.slice(1).toLowerCase();
                                                        return <option key={m.codigo} value={m.codigo}>{pretty}</option>;
                                                    })}
                                                </select>
                                            </div>
                                            {/* Polígono */}
                                            <div>
                                                <label className="field-label">Polígono</label>
                                                <ZoomInput
                                                    label="Polígono" type="number" inputMode="numeric"
                                                    placeholder="" value={form.poligono}
                                                    onConfirm={val => {
                                                        setForm(f=>({...f,poligono:val}));
                                                        if (form.provincia_cod && form.municipio_cod) loadParcelasSigpac(form.provincia_cod, form.municipio_cod, val);
                                                    }} />
                                            </div>
                                            {/* Parcela */}
                                            <div>
                                                <label className="field-label">Parcela</label>
                                                <ZoomInput
                                                    label="Parcela" type="number" inputMode="numeric"
                                                    placeholder="" value={form.parcela_num}
                                                    onConfirm={val => setForm(f=>({...f,parcela_num:val}))} />
                                            </div>
                                            {/* Recinto */}
                                            <div>
                                                <label className="field-label">Recinto</label>
                                                <ZoomInput
                                                    label="Recinto" type="number" inputMode="numeric"
                                                    placeholder="" value={form.recinto}
                                                    onConfirm={val => setForm(f=>({...f,recinto:val}))} />
                                            </div>
                                            {/* Buscar botón */}
                                            <div style={{ display:'flex', alignItems:'flex-end' }}>
                                                <button onClick={buscarSigpac} style={{
                                                    background: sigpacState==='ok' ? '#1D9E75' : sigpacState==='error' ? '#dc2626' : '#1e3a5f',
                                                    color:'#fff', border:'none', borderRadius:10, padding:'14px 16px',
                                                    fontWeight:700, fontSize:'0.82rem', cursor:'pointer', width:'100%',
                                                }}>
                                                    {sigpacState==='loading' ? '⏳ Buscando…' : sigpacState==='ok' ? '✓ Datos SIGPAC' : sigpacState==='error' ? '✗ Sin datos' : '🔍 Buscar en SIGPAC'}
                                                </button>
                                            </div>
                                        </div>
                                </div>
                            </div>

                            {/* Datos adicionales */}
                            <div className="responsive-grid cols-2" style={{ marginBottom:14 }}>
                                <div>
                                    <label className="field-label">Superficie (ha)</label>
                                    <input type="number" step="0.0001" className="input-field" value={form.superficie_ha}
                                        onChange={e => setForm(f=>({...f,superficie_ha:e.target.value}))} />
                                </div>
                                <div>
                                    <label className="field-label">Uso SIGPAC</label>
                                    <input className="input-field" value={form.uso_sigpac}
                                        onChange={e => setForm(f=>({...f,uso_sigpac:e.target.value}))} />
                                </div>
                                <div>
                                    <label className="field-label">Sistema de explotación</label>
                                    <select className="input-field" value={form.sistema_explotacion} onChange={e => setForm(f=>({...f,sistema_explotacion:e.target.value}))}>
                                        {['Invernadero','Mixto','Regadío','Secano'].map(s => <option key={s}>{s}</option>)}
                                    </select>
                                </div>
                                <div style={{ display:'flex', alignItems:'center', gap:10, paddingTop:24 }}>
                                    <input type="checkbox" id="agua_cb" checked={!!form.masa_agua_cercana}
                                        onChange={e => setForm(f=>({...f,masa_agua_cercana:e.target.checked}))}
                                        style={{ width:18, height:18 }} />
                                    <label htmlFor="agua_cb" style={{ fontSize:'0.85rem', fontWeight:600, color:'#374151', cursor:'pointer' }}>
                                        Masa de agua a menos de 50 m
                                    </label>
                                </div>
                            </div>
                            <div style={{ marginBottom:20 }}>
                                <label className="field-label">Notas</label>
                                <textarea className="input-field" rows={3} value={form.notas} onChange={e => setForm(f=>({...f,notas:e.target.value}))} placeholder="Observaciones opcionales…" />
                            </div>

                            <div style={{ display:'flex', gap:10 }}>
                                <button className="btn-ghost" onClick={() => setShowForm(false)} style={{ flex:1 }}>Cancelar</button>
                                <button className="btn-primary" onClick={saveParcela} disabled={saving} style={{ flex:2 }}>
                                    {saving ? 'Guardando…' : (editId ? '💾 Actualizar' : '➕ Añadir parcela')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ── SIGPAC Wizard ── */}
            {wiz && (
                <div className="overlay" style={{ alignItems:'center', justifyContent:'center' }} onClick={closeWizard}>
                    <div style={{
                        background:'#fff', borderRadius:20, maxWidth:420, width:'calc(100% - 32px)',
                        animation:'scaleIn 0.2s ease', overflow:'hidden',
                    }} onClick={e => e.stopPropagation()}>
                        {/* Header */}
                        <div style={{ background:'linear-gradient(135deg,#15785A,#1D9E75)', padding:'20px' }}>
                            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                                <div>
                                    <div style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.05rem', color:'#fff' }}>
                                        Referencia SIGPAC
                                    </div>
                                    <div style={{ fontSize:'0.75rem', color:'rgba(255,255,255,0.7)', marginTop:2 }}>
                                        {selected?.nombre_finca}
                                    </div>
                                </div>
                                <button onClick={closeWizard} style={{ background:'rgba(255,255,255,0.15)', border:'none', borderRadius:'50%', width:32, height:32, color:'#fff', cursor:'pointer', fontSize:16 }}>✕</button>
                            </div>
                            {/* Progress dots */}
                            <div style={{ display:'flex', gap:6, marginTop:16 }}>
                                {[1,2,3,4,5].map(s => (
                                    <div key={s} style={{ flex:1, height:4, borderRadius:2, background: s <= wiz.step ? '#fff' : 'rgba(255,255,255,0.3)' }} />
                                ))}
                            </div>
                            <div style={{ fontSize:'0.7rem', color:'rgba(255,255,255,0.6)', marginTop:6 }}>
                                Paso {wiz.step} de 5
                            </div>
                        </div>

                        <div style={{ padding:'24px 20px 20px' }}>
                            {/* Step 1: Provincia */}
                            {wiz.step === 1 && (
                                <div>
                                    <div style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', color:'#111827', marginBottom:6 }}>¿En qué provincia está?</div>
                                    <p style={{ fontSize:'0.83rem', color:'#6b7280', marginBottom:16 }}>Selecciona la provincia donde se encuentra la parcela.</p>
                                    <select className="input-field" value={wiz.prov_cod}
                                        onChange={e => {
                                            const opt = PROVINCIAS_ES.find(p => p.cod === e.target.value);
                                            setWiz(w => ({ ...w, prov_cod: e.target.value, prov_nombre: opt?.nombre || '' }));
                                        }}>
                                        <option value="">Seleccionar provincia…</option>
                                        {PROVINCIAS_ES.map(p => <option key={p.cod} value={p.cod}>{p.nombre}</option>)}
                                    </select>
                                </div>
                            )}

                            {/* Step 2: Municipio */}
                            {wiz.step === 2 && (
                                <div>
                                    <div style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', color:'#111827', marginBottom:6 }}>¿En qué municipio?</div>
                                    <p style={{ fontSize:'0.83rem', color:'#6b7280', marginBottom:16 }}>Provincia: <strong>{wiz.prov_nombre}</strong></p>
                                    <select className="input-field" value={wiz.mun_cod}
                                        onChange={e => {
                                            const opt = wizMunicipios.find(m => String(m.codigo) === e.target.value);
                                            const nombre = opt?.nombre ? opt.nombre.charAt(0) + opt.nombre.slice(1).toLowerCase() : '';
                                            setWiz(w => ({ ...w, mun_cod: e.target.value, mun_nombre: nombre }));
                                        }}>
                                        <option value="">{wizMunicipios.length === 0 ? 'Cargando…' : 'Seleccionar municipio…'}</option>
                                        {wizMunicipios.map(m => {
                                            const pretty = m.nombre.charAt(0) + m.nombre.slice(1).toLowerCase();
                                            return <option key={m.codigo} value={m.codigo}>{pretty}</option>;
                                        })}
                                    </select>
                                </div>
                            )}

                            {/* Step 3: Polígono */}
                            {wiz.step === 3 && (
                                <div>
                                    <div style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', color:'#111827', marginBottom:6 }}>Número de polígono</div>
                                    <p style={{ fontSize:'0.83rem', color:'#6b7280', marginBottom:16 }}>
                                        {wiz.mun_nombre}, {wiz.prov_nombre}<br/>
                                        <span style={{ fontSize:'0.75rem' }}>Encuéntralo en tu recibo del IBI o en la web del SIGPAC.</span>
                                    </p>
                                    <input className="input-field" type="number" placeholder="Ej: 25"
                                        value={wiz.pol} onChange={e => setWiz(w => ({ ...w, pol: e.target.value }))}
                                        autoFocus style={{ fontSize:'1.4rem', fontWeight:700, textAlign:'center' }} />
                                </div>
                            )}

                            {/* Step 4: Parcela */}
                            {wiz.step === 4 && (
                                <div>
                                    <div style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', color:'#111827', marginBottom:6 }}>Número de parcela</div>
                                    <p style={{ fontSize:'0.83rem', color:'#6b7280', marginBottom:16 }}>
                                        Polígono <strong>{wiz.pol}</strong> · {wiz.mun_nombre}<br/>
                                        <span style={{ fontSize:'0.75rem' }}>Número de parcela dentro del polígono.</span>
                                    </p>
                                    <input className="input-field" type="number" placeholder="Ej: 62"
                                        value={wiz.par} onChange={e => setWiz(w => ({ ...w, par: e.target.value }))}
                                        autoFocus style={{ fontSize:'1.4rem', fontWeight:700, textAlign:'center' }} />
                                </div>
                            )}

                            {/* Step 5: Superficie y Uso */}
                            {wiz.step === 5 && (
                                <div>
                                    <div style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', color:'#111827', marginBottom:6 }}>Confirma los datos</div>
                                    <p style={{ fontSize:'0.83rem', color:'#6b7280', marginBottom:4 }}>
                                        Pol. <strong>{wiz.pol}</strong> · Par. <strong>{wiz.par}</strong> · {wiz.mun_nombre}
                                        {wiz.ref_cat && <span style={{ fontSize:'0.7rem', color:'#9ca3af' }}> · RC: {wiz.ref_cat}</span>}
                                    </p>
                                    {(wiz.superficie || wiz.uso) && (
                                        <div style={{ background:'#f0fdf4', border:'1px solid #bbf7d0', borderRadius:8, padding:'10px 12px', marginBottom:14, fontSize:'0.8rem', color:'#166534' }}>
                                            ✓ Datos obtenidos automáticamente de SIGPAC y Catastro
                                            {wiz.cultivo_catastro && <span> · {wiz.cultivo_catastro}</span>}
                                        </div>
                                    )}
                                    <div style={{ marginBottom:12 }}>
                                        <label className="field-label">Superficie (ha)</label>
                                        <input className="input-field" type="number" step="0.0001" placeholder="Ej: 3.2541"
                                            value={wiz.superficie} onChange={e => setWiz(w => ({ ...w, superficie: e.target.value }))}
                                            autoFocus />
                                    </div>
                                    <div>
                                        <label className="field-label">Uso SIGPAC</label>
                                        <select className="input-field" value={wiz.uso} onChange={e => setWiz(w => ({ ...w, uso: e.target.value }))}>
                                            <option value="">Seleccionar uso…</option>
                                            {['OV-OLIVAR','VI-VIÑEDO','TA-TIERRA ARABLE','CF-CITRICOS','FL-FRUTOS SECOS','FY-FRUTALES','PA-PASTO','PR-PASTO ARBUSTIVO','PS-PASTIZAL','CA-VIALES','IM-IMPRODUCTIVO','AG-CORRIENTES AGUA','ZU-ZONA URBANA','ED-EDIFICACIONES','Otro'].map(u => <option key={u} value={u}>{u}</option>)}
                                        </select>
                                        {!wiz.uso && <div style={{ fontSize:'0.72rem', color:'#9ca3af', marginTop:4 }}>No detectado automáticamente. Puedes dejarlo en blanco.</div>}
                                    </div>
                                </div>
                            )}

                            {/* Botones navegación */}
                            <div style={{ display:'flex', gap:10, marginTop:24 }}>
                                {wiz.step > 1 && (
                                    <button className="btn-ghost" onClick={() => setWiz(w => ({ ...w, step: w.step - 1 }))} style={{ flex:1 }}>
                                        ← Atrás
                                    </button>
                                )}
                                {wiz.step === 5 && (
                                    <button className="btn-ghost" onClick={wizSave} disabled={wizSaving} style={{ flex:1 }}>
                                        Saltar
                                    </button>
                                )}
                                <button className="btn-primary" onClick={wizNext} disabled={wizSaving}
                                    style={{ flex:2 }}>
                                    {wizSaving ? '⏳ Guardando…' : wiz.step === 5 ? '✅ Guardar' : 'Siguiente →'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Picker de recintos — aparece cuando SIGPAC detecta más de uno */}
            {recintosPicker && (() => {
                const recs = recintosPicker.recintos || [];
                // Comprueba si los datos de superficie son distintos entre recintos (subparcelas catastrales distintas)
                const sups = recs.map(r => r.superficie_ha).filter(s => s != null);
                const supIndividual = sups.length === recs.length && new Set(sups).size > 1;
                const supTotal = sups.length > 0 ? sups[0] : null; // todos iguales → es la parcela total
                const fmtSup = s => s != null ? (s >= 1 ? `${s.toFixed(4)} ha` : `${Math.round(s * 10000)} m²`) : null;
                return (
                    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.55)', zIndex:9999,
                        display:'flex', alignItems:'flex-end', justifyContent:'center' }}
                        onClick={() => setRecintosPicker(null)}>
                        <div style={{ background:'#fff', borderRadius:'20px 20px 0 0', padding:'28px 20px 36px',
                            width:'100%', maxWidth:480 }}
                            onClick={e => e.stopPropagation()}>
                            <div style={{ textAlign:'center', marginBottom:20 }}>
                                <div style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', color:'#1a2e1a' }}>
                                    Pol {recintosPicker.poligono} / Par {recintosPicker.parcela}
                                </div>
                                <div style={{ color:'#6b7280', fontSize:'0.83rem', marginTop:4 }}>
                                    {recs.length} recintos — elige el que corresponde a esta parcela
                                </div>
                                {!supIndividual && supTotal && (
                                    <div style={{ color:'#9ca3af', fontSize:'0.75rem', marginTop:4 }}>
                                        Parcela catastral: {fmtSup(supTotal)} en total
                                    </div>
                                )}
                            </div>
                            <div style={{ display:'flex', flexDirection:'column', gap:10, marginBottom:16 }}>
                                {recs.map(rec => (
                                    <button key={rec.num} onClick={() => onPickRecinto(rec.num)} style={{
                                        background:'#fff', border:'2px solid #00694c', color:'#00694c',
                                        borderRadius:12, padding:'14px 20px', fontSize:'1rem',
                                        fontWeight:700, cursor:'pointer', textAlign:'left',
                                        display:'flex', justifyContent:'space-between', alignItems:'center',
                                    }}>
                                        <span style={{ fontSize:'1.1rem', fontWeight:800 }}>Recinto {rec.num}</span>
                                        <span style={{ display:'flex', flexDirection:'column', alignItems:'flex-end', gap:2 }}>
                                            {supIndividual && rec.superficie_ha != null && (
                                                <span style={{ fontSize:'0.9rem', fontWeight:700, color:'#1a2e1a' }}>
                                                    {fmtSup(rec.superficie_ha)}
                                                </span>
                                            )}
                                            {rec.uso_sigpac && (
                                                <span style={{ fontSize:'0.75rem', color:'#6b7280', fontWeight:500 }}>
                                                    {rec.uso_sigpac.split('-').slice(1).join('-').trim() || rec.uso_sigpac}
                                                </span>
                                            )}
                                        </span>
                                    </button>
                                ))}
                            </div>
                            {recintosPicker.mode === 'form' && recs.length > 1 && (
                                <button onClick={abrirResumenMulti} style={{
                                    width:'100%', padding:'14px 20px', marginBottom:12,
                                    background:'#00694c', border:'none', borderRadius:12,
                                    color:'#fff', fontWeight:800, fontSize:'1rem', cursor:'pointer',
                                }}>
                                    ➕ Crear todas ({recs.length} trozos)
                                </button>
                            )}
                            {!supIndividual && (
                                <div style={{ fontSize:'0.72rem', color:'#9ca3af', textAlign:'center', marginBottom:12, lineHeight:1.4 }}>
                                    La API SIGPAC 2026 no devuelve superficie individual por recinto.
                                    Consulta tu ficha SIGPAC para identificar el recinto correcto.
                                </div>
                            )}
                            <button onClick={() => setRecintosPicker(null)} style={{
                                width:'100%', padding:'13px', background:'#f3f4f6',
                                border:'none', borderRadius:10, color:'#6b7280',
                                fontWeight:600, cursor:'pointer', fontSize:'0.9rem',
                            }}>
                                Cancelar
                            </button>
                        </div>
                    </div>
                );
            })()}

            {resumenMulti && (() => {
                const rm = resumenMulti;
                const fmtSup = s => s != null ? (s >= 1 ? `${s.toFixed(4)} ha` : `${Math.round(s * 10000)} m²`) : '—';
                const sinGrupos = rm.grupos.length === 0;
                const setGrupo = (i, patch) => setResumenMulti(r => ({
                    ...r, grupos: r.grupos.map((g, j) => j === i ? { ...g, ...patch } : g),
                }));
                return (
                    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.55)', zIndex:9999,
                        display:'flex', alignItems:'flex-end', justifyContent:'center' }}
                        onClick={() => !rm.creando && setResumenMulti(null)}>
                        <div style={{ background:'#fff', borderRadius:'20px 20px 0 0', padding:'24px 20px 32px',
                            width:'100%', maxWidth:480, maxHeight:'88vh', overflowY:'auto' }}
                            onClick={e => e.stopPropagation()}>

                            <div style={{ fontFamily:'Manrope', fontWeight:800, fontSize:'1.1rem', color:'#1a2e1a', textAlign:'center' }}>
                                Vamos a crear {rm.recs.length} parcelas
                            </div>
                            <div style={{ color:'#6b7280', fontSize:'0.83rem', textAlign:'center', marginTop:4, marginBottom:14 }}>
                                Pol {rm.ctx.poligono} / Par {rm.ctx.parcela} — una parcela por cada trozo (recinto)
                            </div>

                            <div style={{ display:'flex', flexDirection:'column', gap:6, marginBottom:16 }}>
                                {rm.recs.map(r => (
                                    <div key={r.num} style={{ display:'flex', justifyContent:'space-between',
                                        padding:'10px 14px', background:'#f9fafb', borderRadius:10, fontSize:'0.9rem' }}>
                                        <span style={{ fontWeight:700, color:'#1a2e1a' }}>Trozo {r.num}</span>
                                        <span style={{ color:'#6b7280' }}>
                                            {usoLabel(r.uso_sigpac) || 'Sin uso conocido'} · {fmtSup(r.superficie_ha)}
                                        </span>
                                    </div>
                                ))}
                            </div>

                            {sinGrupos ? (
                                <div style={{ background:'#f0fdf4', borderRadius:12, padding:'14px 16px',
                                    fontSize:'0.85rem', color:'#374151', lineHeight:1.5, marginBottom:16 }}>
                                    Cada trozo tiene un cultivo distinto, así que no hay nada que agrupar.
                                    Se crearán las {rm.recs.length} parcelas por separado.
                                </div>
                            ) : (
                                <div style={{ background:'#f0fdf4', borderRadius:12, padding:'16px', marginBottom:16 }}>
                                    <div style={{ fontWeight:800, fontSize:'1rem', color:'#1a2e1a', marginBottom:8 }}>
                                        ¿Juntamos los trozos que se trabajan igual?
                                    </div>
                                    <div style={{ fontSize:'0.83rem', color:'#374151', lineHeight:1.55 }}>
                                        <p style={{ margin:'0 0 8px' }}>
                                            Los trozos que tienen <b>el mismo cultivo</b> puedes juntarlos en un <b>grupo</b>.
                                            <b> ¿Qué ganas con eso?</b> Que las faenas se apuntan <b>una sola vez</b>:
                                        </p>
                                        <ul style={{ margin:'0 0 8px', paddingLeft:18 }}>
                                            <li>Si sulfatas el olivar, apuntas el tratamiento <b>una vez</b> y queda
                                                registrado en todos los trozos del grupo a la vez. Sin grupo, tendrías
                                                que apuntarlo trozo por trozo.</li>
                                            <li>Lo mismo con el abonado y las labores: una anotación vale para todo el grupo.</li>
                                            <li>Tu cuaderno queda igual de completo y correcto ante una inspección:
                                                cada trozo tiene sus datos, solo que tú escribes menos.</li>
                                        </ul>
                                        <p style={{ margin:0 }}>
                                            A ese grupo la administración lo llama "Unidad Homogénea de Cultivo (UHC)".
                                            Para ti es, simplemente, un grupo de trozos que se trabajan igual. Tú decides:
                                            agrúpalos ahora o déjalos sueltos (podrás agruparlos más adelante desde la
                                            pantalla de Grupos).
                                        </p>
                                    </div>
                                </div>
                            )}

                            {rm.grupos.map((g, i) => (
                                <div key={g.uso} style={{ border:'2px solid ' + (g.aceptado ? '#00694c' : '#e5e7eb'),
                                    borderRadius:12, padding:'14px 16px', marginBottom:12 }}>
                                    <div style={{ fontSize:'0.8rem', color:'#6b7280', marginBottom:6 }}>
                                        Junta los trozos {g.nums.join(', ')} ({usoLabel(g.uso)})
                                    </div>
                                    <input value={g.nombre} disabled={!g.aceptado || rm.creando}
                                        aria-label={`Nombre del grupo ${usoLabel(g.uso)}`}
                                        onChange={e => setGrupo(i, { nombre: e.target.value })}
                                        style={{ width:'100%', padding:'12px', borderRadius:8, fontSize:'1rem',
                                            border:'1px solid #d1d5db', marginBottom:10, boxSizing:'border-box' }} />
                                    <div style={{ display:'flex', gap:8 }}>
                                        <button onClick={() => setGrupo(i, { aceptado: true })} disabled={rm.creando} style={{
                                            flex:1, padding:'14px 12px', borderRadius:10, fontWeight:700, cursor:'pointer',
                                            border:'2px solid #00694c', fontSize:'0.9rem',
                                            background: g.aceptado ? '#00694c' : '#fff',
                                            color: g.aceptado ? '#fff' : '#00694c' }}>
                                            Sí, agrupar
                                        </button>
                                        <button onClick={() => setGrupo(i, { aceptado: false })} disabled={rm.creando} style={{
                                            flex:1, padding:'14px 12px', borderRadius:10, fontWeight:700, cursor:'pointer',
                                            border:'2px solid ' + (!g.aceptado ? '#6b7280' : '#e5e7eb'), fontSize:'0.9rem',
                                            background: !g.aceptado ? '#6b7280' : '#fff',
                                            color: !g.aceptado ? '#fff' : '#9ca3af' }}>
                                            No, dejar sueltos
                                        </button>
                                    </div>
                                </div>
                            ))}

                            <button onClick={confirmarMultirecinto} disabled={rm.creando} style={{
                                width:'100%', padding:'15px', background: rm.creando ? '#9ca3af' : '#00694c',
                                border:'none', borderRadius:12, color:'#fff', fontWeight:800,
                                fontSize:'1.05rem', cursor: rm.creando ? 'wait' : 'pointer', marginBottom:10 }}>
                                {rm.creando ? 'Creando…' : '✓ Confirmar y crear'}
                            </button>
                            <button onClick={() => setResumenMulti(null)} disabled={rm.creando} style={{
                                width:'100%', padding:'13px', background:'#f3f4f6', border:'none',
                                borderRadius:10, color:'#6b7280', fontWeight:600, cursor:'pointer', fontSize:'0.9rem' }}>
                                Cancelar
                            </button>
                        </div>
                    </div>
                );
            })()}
        </div>
    );
}
