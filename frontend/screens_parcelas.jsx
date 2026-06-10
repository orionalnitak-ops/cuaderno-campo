// Catálogo de cultivos con códigos IACS (Anexo VII FEGA — para SIEX 2027)
const CULTIVOS_IACS = [
    { cod: '1820', nombre: 'Olivar',                   grupo: 'Leñosos' },
    { cod: '1711', nombre: 'Viñedo vinificación',      grupo: 'Leñosos' },
    { cod: '1712', nombre: 'Viñedo uva de mesa',       grupo: 'Leñosos' },
    { cod: '1710', nombre: 'Almendro',                 grupo: 'Leñosos' },
    { cod: '1740', nombre: 'Pistachero',               grupo: 'Leñosos' },
    { cod: '1750', nombre: 'Higuera',                  grupo: 'Leñosos' },
    { cod: '1760', nombre: 'Nogal',                    grupo: 'Leñosos' },
    { cod: '1770', nombre: 'Cerezo / Guindo',          grupo: 'Leñosos' },
    { cod: '1720', nombre: 'Melocotonero / Nectarino', grupo: 'Leñosos' },
    { cod: '1730', nombre: 'Ciruelo',                  grupo: 'Leñosos' },
    { cod: '1830', nombre: 'Naranjo',                  grupo: 'Leñosos' },
    { cod: '1840', nombre: 'Limonero',                 grupo: 'Leñosos' },
    { cod: '410',  nombre: 'Trigo blando',             grupo: 'Cereales' },
    { cod: '415',  nombre: 'Trigo duro',               grupo: 'Cereales' },
    { cod: '430',  nombre: 'Cebada',                   grupo: 'Cereales' },
    { cod: '440',  nombre: 'Avena',                    grupo: 'Cereales' },
    { cod: '450',  nombre: 'Centeno',                  grupo: 'Cereales' },
    { cod: '454',  nombre: 'Maíz',                     grupo: 'Cereales' },
    { cod: '460',  nombre: 'Sorgo',                    grupo: 'Cereales' },
    { cod: '470',  nombre: 'Arroz',                    grupo: 'Cereales' },
    { cod: '701',  nombre: 'Girasol',                  grupo: 'Industriales' },
    { cod: '720',  nombre: 'Colza / Nabina',           grupo: 'Industriales' },
    { cod: '780',  nombre: 'Remolacha azucarera',      grupo: 'Industriales' },
    { cod: '481',  nombre: 'Guisante proteaginoso',    grupo: 'Leguminosas' },
    { cod: '484',  nombre: 'Veza / Yeros',             grupo: 'Leguminosas' },
    { cod: '490',  nombre: 'Haba',                     grupo: 'Leguminosas' },
    { cod: '495',  nombre: 'Soja',                     grupo: 'Leguminosas' },
    { cod: '100',  nombre: 'Ajo',                      grupo: 'Hortalizas' },
    { cod: '110',  nombre: 'Cebolla',                  grupo: 'Hortalizas' },
    { cod: '120',  nombre: 'Patata',                   grupo: 'Hortalizas' },
    { cod: '140',  nombre: 'Tomate',                   grupo: 'Hortalizas' },
    { cod: '160',  nombre: 'Melón',                    grupo: 'Hortalizas' },
    { cod: '162',  nombre: 'Sandía',                   grupo: 'Hortalizas' },
    { cod: '550',  nombre: 'Alfalfa',                  grupo: 'Forrajeras' },
    { cod: '560',  nombre: 'Esparceta / Zulla',        grupo: 'Forrajeras' },
    { cod: '980',  nombre: 'Barbecho',                 grupo: 'Barbecho' },
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

function ScreenParcelas({ campana, showToast }) {
    const { useState, useEffect } = React;

    const [parcelas, setParcelas]   = useState([]);
    const [selected, setSelected]   = useState(null);
    const [showForm, setShowForm]   = useState(false);
    const [tab, setTab]             = useState('parcela'); // parcela | cultivos
    const [loading, setLoading]     = useState(true);
    const [cultivo, setCultivo]     = useState({});
    const [savingCultivo, setSavingCultivo] = useState(false);

    // Parcela form state
    const EMPTY_FORM = {
        nombre_finca:'', comunidad:'07-Castilla-La Mancha',
        provincia_cod:'', provincia_nombre:'',
        municipio_cod:'', municipio_nombre:'',
        poligono:'', parcela_num:'', recinto:'',
        superficie_ha:'', uso_sigpac:'', sistema_explotacion:'Secano',
        masa_agua_cercana:false, notas:'',
    };
    const [form, setForm]   = useState(EMPTY_FORM);
    const [editId, setEditId] = useState(null);
    const [saving, setSaving] = useState(false);
    const [sigpacSyncing, setSigpacSyncing] = useState(false);

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
            setParcelas(Array.isArray(data) ? data : []);
            setLoading(false);
        }).catch(() => setLoading(false));
    };
    useEffect(() => { fetchParcelas(); }, []);

    // Load cultivo when parcel selected
    useEffect(() => {
        if (!selected) return;
        fetch(`/api/cultivos-campana?parcela_id=${selected.id}&campana=${encodeURIComponent(campana)}`, { credentials: 'include' })
            .then(r => r.json()).then(data => {
                const arr = Array.isArray(data) ? data : [];
                setCultivo(arr[0] || { parcela_id: selected.id, campana });
            });
    }, [selected, campana]);

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
            if (sup || uso) {
                setForm(f => ({ ...f, recinto: rec, superficie_ha: sup || f.superficie_ha, uso_sigpac: uso || f.uso_sigpac }));
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
        try {
            const res = await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(form), credentials: 'include' });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                showToast(`❌ Error al guardar: ${err.error || res.status}`);
                setSaving(false);
                return;
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
    };

    const deleteParcela = async (p) => {
        if (!confirm(`¿Eliminar "${p.nombre_finca}"? Los registros asociados se mantendrán.`)) return;
        await fetch(`/api/parcelas/${p.id}`, { method: 'DELETE', credentials: 'include' });
        showToast('Parcela eliminada');
        setSelected(null);
        fetchParcelas();
    };

    const saveCultivo = async () => {
        setSavingCultivo(true);
        await fetch('/api/cultivos-campana', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ ...cultivo, parcela_id: selected.id, campana }),
            credentials: 'include',
        });
        showToast('Cultivo de campaña guardado');
        setSavingCultivo(false);
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
                        <div style={{ display:'flex', gap:8 }}>
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
                            {[['parcela','📍 Parcela'],['cultivos','🌱 Cultivo campaña']].map(([id,label]) => (
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
                        {tab === 'parcela' ? (
                            <div>
                                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginBottom:16 }}>
                                    {[
                                        ['Polígono', selected.poligono, false],
                                        ['Parcela', selected.parcela_num, false],
                                        ['Recinto', selected.recinto, false],
                                        ['Superficie', selected.superficie_ha ? `${selected.superficie_ha} ha` : '', true],
                                        ['Uso SIGPAC', selected.uso_sigpac, true],
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
                        ) : (
                            <div>
                                <h2 className="section-title">Cultivo campaña {campana}</h2>
                                <div className="responsive-grid cols-2" style={{ marginBottom:16 }}>
                                    <div style={{ gridColumn: '1/-1' }}>
                                        <label className="field-label">Cultivo (código IACS)</label>
                                        <select className="input-field"
                                            value={cultivo.cultivo_iacs_cod || ''}
                                            onChange={e => {
                                                const cod = e.target.value;
                                                const entry = CULTIVOS_IACS.find(c => c.cod === cod);
                                                setCultivo(c => ({ ...c,
                                                    cultivo_iacs_cod: cod,
                                                    cultivo: entry ? entry.nombre : c.cultivo,
                                                }));
                                            }}>
                                            <option value="">Seleccionar cultivo…</option>
                                            {Object.entries(
                                                CULTIVOS_IACS.reduce((acc, c) => {
                                                    (acc[c.grupo] = acc[c.grupo] || []).push(c);
                                                    return acc;
                                                }, {})
                                            ).map(([grupo, items]) => (
                                                <optgroup key={grupo} label={grupo}>
                                                    {items.map(c => (
                                                        <option key={c.cod} value={c.cod}>{c.nombre}</option>
                                                    ))}
                                                </optgroup>
                                            ))}
                                        </select>
                                        {cultivo.cultivo_iacs_cod && (
                                            <div style={{ fontSize:'0.75rem', color:'#6b7280', marginTop:4 }}>
                                                Código IACS: <strong>{cultivo.cultivo_iacs_cod}</strong>
                                            </div>
                                        )}
                                    </div>
                                    {[
                                        ['variedad','Variedad','text','Picual, Tempranillo…'],
                                        ['fecha_siembra','Fecha de siembra','date',''],
                                        ['fecha_recoleccion_prevista','Fecha recol. prevista','date',''],
                                        ['superficie_cultivada_ha','Superficie cultivada (ha)','number',''],
                                    ].map(([k,l,t,ph]) => (
                                        <div key={k}>
                                            <label className="field-label">{l}</label>
                                            <input type={t} className="input-field" placeholder={ph}
                                                value={cultivo[k]||''}
                                                onChange={e => setCultivo(c => ({...c,[k]:e.target.value}))} />
                                        </div>
                                    ))}
                                </div>
                                <div style={{ marginBottom:16 }}>
                                    <label className="field-label">Notas</label>
                                    <textarea className="input-field" rows={3} value={cultivo.notas||''} onChange={e => setCultivo(c => ({...c,notas:e.target.value}))} />
                                </div>
                                <button className="btn-primary" onClick={saveCultivo} disabled={savingCultivo}>
                                    {savingCultivo ? 'Guardando…' : '💾 Guardar cultivo'}
                                </button>
                            </div>
                        )}
                    </div>
                </div>
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
        </div>
    );
}
