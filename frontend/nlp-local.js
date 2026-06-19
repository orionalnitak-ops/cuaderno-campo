// NLP parsing engine (mirror of blueprints/nlp.py) — runs fully offline
// exposes window.NLPLocal.parse(texto) → same JSON format as /api/parse
(function () {
  function _norm(s) {
    return String(s).toLowerCase()
      .normalize('NFD').replace(/[̀-ͯ]/g, '').trim();
  }

  function extraerAccion(texto) {
    const tnorm = _norm(texto);
    const acciones = {
      tratamiento: ['tratado','tratamiento','tratamos','trate','pulverizado','pulverice','fumigado','fumigue','fumigaci','spray','insecticida','fungicida','herbicida','fitosanitario','plaguicida','mata','mato'],
      fertilizacion: ['abonado','abone','abonamos','fertilizado','fertilice','abono','nutrientes','nitrogeno','fosforo','potasio','npk','urea','sulfato','superfosfato','estiercol','compost','purines'],
      riego: ['regado','regue','rege','regamos','rego','riego','riegos','inundado','goteo','aspersion','pivote'],
      cosecha: ['cosechado','cosechamos','coseche','cosecho','cosecha ','recolectado','recogie','vendimiado','vendimia','trillado','trilla','recogi'],
      labor: ['labor','labrado','labre','laboreo','arado','are ','are,','cave','cavado','poda','pode','podamos','desyerbado','desherbado','desbroz','sembrado','siembre','siembra','sembre','sembré','he sembrado','sembramos','sembrar','siembro','fresado','subsolado','cultivado','he cultivado','cultivé','cultivamos','gradeo','pase de','pase ','limpie','limpieza','plantado','plante','planté','plantamos','plantación'],
    };
    for (const [tipo, palabras] of Object.entries(acciones)) {
      for (const palabra of palabras) {
        if (tnorm.includes(_norm(palabra))) {
          return { tipo, confianza: 0.9, palabra_clave: palabra };
        }
      }
    }
    return { tipo: null, confianza: 0, palabra_clave: null };
  }

  function extraerProducto(texto) {
    const tnorm = _norm(texto);
    const productos = [
      ['yero','Yeros'],['yeros','Yeros'],['trigo','Trigo'],['cebada','Cebada'],['avena','Avena'],
      ['centeno','Centeno'],['triticale','Triticale'],['girasol','Girasol'],['colza','Colza'],
      ['maiz','Maíz'],['soja','Soja'],['guisante','Guisante'],['garbanzo','Garbanzo'],
      ['lenteja','Lenteja'],['almorta','Almorta'],['veza','Veza'],['alfalfa','Alfalfa'],
      ['remolacha','Remolacha'],['patata','Patata'],['tomate','Tomate'],['pimiento','Pimiento'],
      ['cebolla','Cebolla'],['ajo','Ajo'],['olivo','Olivo'],['vid','Vid'],['viña','Vid'],
      ['almendro','Almendro'],['pistachero','Pistachero'],
      ['cobre','Cobre'],['azufre','Azufre'],['mancozeb','Mancozeb'],['captan','Captán'],
      ['clorotalonil','Clorotalonil'],['tebuconazol','Tebuconazol'],['iprodiona','Iprodiona'],
      ['metalaxil','Metalaxil'],['fosetil','Fosetil-Al'],['ziram','Ziram'],['metiram','Metiram'],
      ['oxicloruro','Oxicloruro de cobre'],['clorpirifos','Clorpirifos'],['deltametrina','Deltametrina'],
      ['lambda','Lambda-cihalotrin'],['imidacloprid','Imidacloprid'],['spinosad','Spinosad'],
      ['abamectina','Abamectina'],['dimetoato','Dimetoato'],['piretrinas','Piretrinas'],
      ['glifosato','Glifosato'],['diquat','Diquat'],['terbutilazina','Terbutilazina'],
      ['s-metolacloro','S-metolacloro'],['pendimetalina','Pendimetalina'],
      ['urea','Urea'],['npk','NPK'],['nitrato amonico','Nitrato amónico'],
      ['sulfato amonico','Sulfato amónico'],['superfosfato','Superfosfato'],
      ['cloruro potasico','Cloruro potásico'],['estiercol','Estiércol'],
      ['compost','Compost'],['purines','Purines'],
    ];
    for (const [clave, nombre] of productos) {
      if (tnorm.includes(_norm(clave))) return { nombre, confianza: 0.85 };
    }
    return { nombre: null, confianza: 0 };
  }

  function extraerDosis(texto) {
    const patrones = [
      [/(\d+[.,]?\d*)\s*(cc|centilitro)/i, 'cc'],
      [/(\d+[.,]?\d*)\s*(l|litro|litros|ℓ)\b/i, 'L'],
      [/(\d+[.,]?\d*)\s*(kg|kilo|kilos)\b/i, 'kg'],
      [/(\d+[.,]?\d*)\s*(g|gramo|gramos)\b/i, 'g'],
      [/(\d+[.,]?\d*)\s*(t|tonelada|toneladas)\b/i, 't'],
    ];
    for (const [patron, unidad] of patrones) {
      const m = texto.match(patron);
      if (m) return { valor: parseFloat(m[1].replace(',', '.')), unidad, texto_original: m[0] };
    }
    return { valor: null, unidad: null, texto_original: null };
  }

  function extraerFecha(texto) {
    const tl = texto.toLowerCase();
    const hoy = new Date();

    if (tl.includes('anteayer')) {
      const d = new Date(hoy); d.setDate(d.getDate() - 2);
      return d.toISOString().slice(0, 10);
    }
    if (tl.includes('ayer')) {
      const d = new Date(hoy); d.setDate(d.getDate() - 1);
      return d.toISOString().slice(0, 10);
    }

    const MESES = {enero:1,febrero:2,marzo:3,abril:4,mayo:5,junio:6,julio:7,agosto:8,septiembre:9,octubre:10,noviembre:11,diciembre:12};
    const mMes = tl.match(new RegExp('\\b(\\d{1,2})\\s+de\\s+(' + Object.keys(MESES).join('|') + ')\\b'));
    if (mMes) {
      const dia = parseInt(mMes[1]), mes = MESES[mMes[2]];
      for (const yr of [hoy.getFullYear(), hoy.getFullYear() - 1]) {
        const f = new Date(yr, mes - 1, dia);
        if (!isNaN(f) && f <= new Date(hoy.getTime() + 86400000)) return f.toISOString().slice(0, 10);
      }
    }

    const mNum = tl.match(/\b(\d{1,2})[/-](\d{1,2})\b/);
    if (mNum) {
      const dia = parseInt(mNum[1]), mes = parseInt(mNum[2]);
      for (const yr of [hoy.getFullYear(), hoy.getFullYear() - 1]) {
        const f = new Date(yr, mes - 1, dia);
        if (!isNaN(f) && f <= new Date(hoy.getTime() + 86400000)) return f.toISOString().slice(0, 10);
      }
    }

    const DIAS = {lunes:1,martes:2,'miércoles':3,miercoles:3,jueves:4,viernes:5,'sábado':6,sabado:6,domingo:0};
    for (const [nombre, num] of Object.entries(DIAS)) {
      if (tl.includes(nombre)) {
        let atras = (hoy.getDay() - num + 7) % 7;
        if (atras === 0) atras = 7;
        const d = new Date(hoy); d.setDate(d.getDate() - atras);
        return d.toISOString().slice(0, 10);
      }
    }

    return hoy.toISOString().slice(0, 10);
  }

  function extraerTipoRiego(texto) {
    const tnorm = _norm(texto);
    if (['goteo','gota a gota','exudacion'].some(k => tnorm.includes(_norm(k)))) return 'Goteo';
    if (['aspersion','aspersor','rociador','lluvia'].some(k => tnorm.includes(_norm(k)))) return 'Aspersión';
    if (['pivot','pivote'].some(k => tnorm.includes(_norm(k)))) return 'Pivot';
    if (['gravedad','inundacion','inundado','manta','surcos'].some(k => tnorm.includes(_norm(k)))) return 'Gravedad';
    return null;
  }

  function extraerCantidadRiego(texto) {
    const mH = texto.match(/(\d+[.,]?\d*)\s*hora/i);
    if (mH) return { horas_riego: parseFloat(mH[1].replace(',', '.')), volumen_m3: null };
    const mM = texto.match(/(\d+[.,]?\d*)\s*(m3|m³|metro|metros cubicos)/i);
    if (mM) return { horas_riego: null, volumen_m3: parseFloat(mM[1].replace(',', '.')) };
    return { horas_riego: null, volumen_m3: null };
  }

  function extraerParcela(texto, parcelas) {
    const tnorm = _norm(texto);
    for (const p of parcelas) {
      if (tnorm.includes(_norm(p.nombre_finca))) return { id: p.id, nombre: p.nombre_finca };
    }
    for (const p of parcelas) {
      const partes = _norm(p.nombre_finca).split(/[\s\-\/]+/).filter(w => w.length > 3);
      if (partes.length > 0 && partes.every(parte => tnorm.includes(parte))) return { id: p.id, nombre: p.nombre_finca };
    }
    return null;
  }

  function extraerNombreCandidato(texto) {
    const STOP_FIN = new Set(['hoy','ayer','esta','este','manana','por','he','con','sin','y']);
    const SKIP_LOW = new Set(['el','la','los','las','un','una','unos','unas','parcela','finca','campo','terreno']);

    function limpiar(palabras) {
      while (palabras.length && STOP_FIN.has(_norm(palabras[palabras.length - 1]))) palabras.pop();
      while (palabras.length && palabras[0][0] === palabras[0][0].toLowerCase() && SKIP_LOW.has(palabras[0].toLowerCase())) palabras.shift();
      return palabras.join(' ');
    }

    const m1 = texto.match(/(?:en|finca|parcela|campo)\s+([\w][\w\s]{1,30}?)(?=\s+con\s|\s*[,.]|\s*$)/i);
    if (m1) {
      const c = limpiar(m1[1].trim().split(/\s+/));
      if (c.length > 2 && c.length < 40) return c.toUpperCase();
    }

    const VERBOS = 'trat\\w{1,6}|abon\\w{1,6}|reg\\w{1,6}|pod\\w{1,6}|cosech\\w{1,6}|fumig\\w{1,6}|sembr\\w{1,6}|siembr\\w{1,5}|labr\\w{1,6}|vendimi\\w{1,6}|recog\\w{1,6}|arad\\w{1,5}|cav\\w{1,5}|desbroz\\w{1,5}|pulver\\w{1,5}|trilla\\w{1,4}|recolect\\w{1,5}|subsolad\\w{1,4}|grad\\w{1,5}|cultiv\\w{1,5}';
    const m2 = texto.match(new RegExp(
      '(?:' + VERBOS + ')\\s+(?:el\\s+|la\\s+|los\\s+|las\\s+)?([\\w][\\w\\s]{1,33}?)(?=\\s+en\\s|\\s+con\\s|\\s*[,.]|\\s+(?:hoy|ayer|esta|este|por|de\\s+|$)|\\s*$)',
      'i'
    ));
    if (m2) {
      const c = limpiar(m2[1].trim().split(/\s+/));
      if (c.length > 2 && c.length < 40) return c.toUpperCase();
    }

    return null;
  }

  window.NLPLocal = {
    async parse(texto) {
      let parcelas = [];
      if (window.OfflineDB) {
        try { parcelas = await window.OfflineDB.getCachedParcelas(); } catch {}
      }

      const parcela_data = extraerParcela(texto, parcelas);
      const accion_data  = extraerAccion(texto);
      const producto_data = extraerProducto(texto);
      const dosis_data   = extraerDosis(texto);
      const nombre_candidato = parcela_data ? null : extraerNombreCandidato(texto);
      const fecha = extraerFecha(texto);
      const es_riego = accion_data.tipo === 'riego';
      const cantidad_riego = es_riego ? extraerCantidadRiego(texto) : { horas_riego: null, volumen_m3: null };

      return {
        status: 'success',
        texto_original: texto,
        _offline: true,
        parseo: {
          parcela: {
            id: parcela_data ? parcela_data.id : null,
            nombre: parcela_data ? parcela_data.nombre : null,
            nombre_candidato,
            es_nueva: !parcela_data && !!nombre_candidato,
            requiere_seleccion: !parcela_data && !nombre_candidato,
            confianza: parcela_data ? 1.0 : 0.0,
          },
          accion:   { tipo: accion_data.tipo, palabra_clave: accion_data.palabra_clave, confianza: accion_data.confianza },
          producto: { nombre: producto_data.nombre, confianza: producto_data.confianza },
          dosis:    { valor: dosis_data.valor, unidad: dosis_data.unidad },
          fecha,
          riego: {
            tipo_riego:  es_riego ? extraerTipoRiego(texto) : null,
            horas_riego: cantidad_riego.horas_riego,
            volumen_m3:  cantidad_riego.volumen_m3,
          },
        },
        requiere_confirmacion: !parcela_data && !nombre_candidato,
      };
    },
  };
})();
