// ── Sistema de ayuda: guía de inicio + ayuda contextual por pantalla ──

// ── Contenido de ayuda por pantalla ──
const HELP_SCREENS = {
    inicio: {
        title: '🏡 Pantalla de inicio',
        intro: 'Desde aquí controlas todo: el tiempo, lo que hiciste últimamente y el acceso rápido a anotar.',
        steps: [
            {
                icon: '✏️',
                title: 'Botón ✏️ — Anotar actividad',
                desc: 'El botón verde ✏️ de la barra inferior es el más importante. Púlsalo para registrar cualquier actividad: tratamientos, riego, fertilización, labores, cosecha...',
            },
            {
                icon: '🎤',
                title: 'Habla que yo escribo',
                desc: 'En la pantalla de inicio hay dos opciones: "Rellénalo tú" (formularios) y "Habla que yo escribo". Con la segunda, di en voz alta lo que hiciste — "apliqué herbicida en el olivar" — y el cuaderno lo registra solo.',
            },
            {
                icon: '🌡️',
                title: 'Previsión del tiempo',
                desc: 'Muestra la previsión de los próximos días según tu municipio. Muy útil para planificar tratamientos y riegos.',
            },
            {
                icon: '⚠️',
                title: 'Alertas y avisos meteorológicos',
                desc: 'El cuaderno cruza la previsión con los avisos oficiales de AEMET/METEOALARM y te marca en rojo, naranja o amarillo los días con tormenta, granizo, lluvia intensa, calor extremo, heladas o viento fuerte. Los avisos verdes (💨 viento, 🌧️ lluvia) te indican cuándo NO conviene tratar. Pulsa una alerta para ver el detalle.',
            },
            {
                icon: '🏡',
                title: 'Cambiar de explotación',
                desc: 'Si gestionas varias explotaciones (plan Pro), en la barra superior "Explotación" eliges con cuál estás trabajando. Todo lo que registres —parcelas, tratamientos, cuaderno— queda asociado a la explotación activa.',
            },
            {
                icon: '📋',
                title: 'Últimas actividades',
                desc: 'Aparecen los últimos registros para que veas de un vistazo qué has hecho recientemente. Pulsa en uno para editarlo.',
            },
        ],
    },
    parcelas: {
        title: '🗺️ Mis parcelas',
        intro: 'Aquí registras todas tus parcelas SIGPAC. Sin parcelas no puedes anotar actividades correctamente.',
        steps: [
            {
                icon: '➕',
                title: '+ Nueva parcela',
                desc: 'Pulsa el botón "+ Nueva parcela" para añadir una. Necesitas la referencia SIGPAC: provincia, municipio, polígono, parcela y recinto.',
            },
            {
                icon: '🔍',
                title: 'Buscar en SIGPAC',
                desc: 'Dentro del formulario hay un buscador que conecta con el SIGPAC oficial. Selecciona provincia, municipio, polígono y parcela de los desplegables.',
            },
            {
                icon: '✂️',
                title: 'Parcela dividida en varios trozos',
                desc: 'Si tu parcela del SIGPAC está dividida en varios trozos (recintos), al buscarla te ofrecemos "➕ Crear todas": se crea una parcela por cada trozo de una sola vez. Y si varios trozos tienen el mismo cultivo, te proponemos juntarlos en un grupo para apuntar las faenas una sola vez. Tú decides si agrupar o no.',
            },
            {
                icon: '✅',
                title: 'Verificado con SIGPAC',
                desc: 'Al guardar una parcela, el cuaderno comprueba su superficie contra el SIGPAC oficial. Si cuadra, verás la marca verde "✓ Verificado con SIGPAC". Si hay mucha diferencia, un aviso ámbar te lo señala para que revises los datos. También puedes volver a verificar desde la ficha de la parcela.',
            },
            {
                icon: '🌾',
                title: 'Cultivo de campaña',
                desc: 'Asigna el cultivo actual a cada parcela. Es obligatorio para el cuaderno oficial — el PDF debe reflejar qué se cultiva en cada recinto.',
            },
            {
                icon: '🗺️',
                title: 'Vista en el mapa',
                desc: 'El mapa muestra la ubicación de cada parcela sobre la foto aérea oficial. Puedes activar la capa Red Natura 2000 para ver si tu parcela está en zona protegida (afecta a qué productos puedes aplicar). Pulsa sobre una parcela para ver sus detalles y su historial.',
            },
        ],
    },
    historial: {
        title: '📋 Historial',
        intro: 'Todos tus registros en un solo sitio: tratamientos, riegos, labores, cosechas...',
        steps: [
            {
                icon: '🔍',
                title: 'Filtrar por tipo o fecha',
                desc: 'Usa los filtros de la parte superior para buscar registros por tipo de actividad, parcela concreta o rango de fechas.',
            },
            {
                icon: '✏️',
                title: 'Editar un registro',
                desc: 'Pulsa sobre cualquier registro de la lista para abrirlo y editarlo. También puedes eliminarlo desde ahí.',
            },
            {
                icon: '📄',
                title: 'Exportar el cuaderno',
                desc: 'Para descargar el PDF oficial, ve a Ajustes → Datos y exportación. El historial es la base de ese PDF.',
            },
        ],
    },
    mas: {
        title: '⚙️ Ajustes',
        intro: 'Todo está organizado en pestañas: Explotación, Equipos, Aplicadores, Datos y exportación, Mi cuenta, Suscripción y Legal.',
        steps: [
            {
                icon: '🏡',
                title: 'Explotación (obligatorio)',
                desc: 'Rellena el nombre del titular, NIF, REGA, municipio y provincia. Son datos legales obligatorios que aparecen en el PDF oficial. Aquí también fijas la campaña activa.',
            },
            {
                icon: '🚜',
                title: 'Equipos de aplicación',
                desc: 'Registra tus máquinas con número de registro ROMA y fecha de la última ITEAF. Es obligatorio para los tratamientos fitosanitarios.',
            },
            {
                icon: '👤',
                title: 'Aplicadores ROPO',
                desc: 'Añade los aplicadores con su número ROPO. Cada tratamiento debe tener un aplicador registrado con carnet vigente.',
            },
            {
                icon: '📄',
                title: 'Descargar PDF y Excel',
                desc: 'En "Datos y exportación" descargas el Cuaderno de Explotación en PDF oficial (válido para inspecciones, conforme al RD 1311/2012) o en Excel con 7 hojas: portada, parcelas, cultivos, tratamientos, abono, labores y cosecha.',
            },
            {
                icon: '💳',
                title: 'Suscripción y cuenta',
                desc: 'En "Suscripción" ves tu plan actual y puedes cambiarlo. En "Mi cuenta" cambias la contraseña o cierras sesión. En "Legal y privacidad" tienes la normativa aplicable y tus derechos RGPD.',
            },
            {
                icon: '📖',
                title: 'Volver a ver la guía',
                desc: 'Arriba del todo tienes el botón "Ver guía de inicio" para repasar los primeros pasos cuando quieras, y "¿Tienes un problema? Escríbenos" para contactar con soporte.',
            },
        ],
    },
    explotacion: {
        title: '🏡 Explotaciones',
        intro: 'La barra superior te permite trabajar con una o varias explotaciones desde la misma cuenta.',
        steps: [
            {
                icon: '🔄',
                title: 'Explotación activa',
                desc: 'El selector "Explotación" de la barra superior indica con cuál estás trabajando. Todo lo que registres —parcelas, tratamientos, cuaderno, exportaciones— pertenece a la explotación activa. Cambia de una a otra en cualquier momento.',
            },
            {
                icon: '＋',
                title: 'Añadir otra explotación',
                desc: 'Con el plan Pro puedes gestionar varias explotaciones (por ejemplo, la tuya y la de un familiar) sin duplicar cuentas. Pulsa "＋ Nueva" para dar de alta otra con su propio titular, NIF y REGA.',
            },
            {
                icon: '🏷️',
                title: 'Nombre corto',
                desc: 'En los datos de cada explotación puedes ponerle un "nombre corto" (ej: "Emilio", "Robert"…). Es la etiqueta que aparece en el selector para distinguirlas de un vistazo.',
            },
            {
                icon: '⭐',
                title: '¿Solo tienes el plan Básico?',
                desc: 'El plan Básico gestiona una única explotación. Si necesitas más de una, el botón "⭐ Multi-explotación" te lleva a los planes para pasarte a Pro.',
            },
        ],
    },
    tratamiento: {
        title: '🌿 Tratamiento Fitosanitario',
        intro: 'Registra cada aplicación de productos fitosanitarios. Es el módulo más exigido en una inspección.',
        steps: [
            {
                icon: '🗺️',
                title: 'Parcela',
                desc: 'Selecciona la parcela SIGPAC donde se aplicó el producto. Si tratas varias a la vez, crea un Grupo UHC y selecciónalo aquí.',
            },
            {
                icon: '🧪',
                title: 'Producto y materia activa',
                desc: 'Escribe el nombre comercial del fitosanitario y su materia activa (ingrediente principal). Ambos son obligatorios por el RD 1311/2012.',
            },
            {
                icon: '📏',
                title: 'Dosis aplicada',
                desc: 'Indica cuánto producto usaste por hectárea (L/ha o kg/ha). Debe coincidir con la etiqueta del producto.',
            },
            {
                icon: '👤',
                title: 'Aplicador ROPO',
                desc: 'Pon el número de carnet del aplicador que realizó el tratamiento. Si no tienes aplicadores registrados, añádelos primero en Ajustes.',
            },
            {
                icon: '🚜',
                title: 'Equipo ROMA',
                desc: 'Selecciona la maquinaria usada para aplicar. El equipo debe tener número de registro ROMA y la revisión ITEAF en vigor.',
            },
        ],
    },
    fertilizacion: {
        title: '🌱 Fertilización',
        intro: 'Anota cada aportación de abonos o enmiendas. El tipo y dosis quedan registrados en el cuaderno oficial.',
        steps: [
            {
                icon: '🗺️',
                title: 'Parcela',
                desc: 'Indica en qué parcela se aplicó el fertilizante.',
            },
            {
                icon: '🧪',
                title: 'Tipo y producto',
                desc: 'Elige si es fertilizante mineral, orgánico o una enmienda. Luego escribe el nombre comercial del producto.',
            },
            {
                icon: '📏',
                title: 'Dosis y método',
                desc: 'Indica la cantidad aplicada (kg/ha o L/ha) y cómo se aplicó: incorporado al suelo, localizado, fertirrigación o foliar.',
            },
            {
                icon: '📅',
                title: 'Fecha',
                desc: 'La fecha de aplicación es obligatoria. Si aplicaste en varios días, registra una entrada por día.',
            },
        ],
    },
    labor: {
        title: '🚜 Labor Agrícola',
        intro: 'Registra cualquier labor que hagas en la finca: siembra, poda, laboreo, tratamientos manuales, etc.',
        steps: [
            {
                icon: '🗺️',
                title: 'Parcela',
                desc: 'Selecciona la parcela donde realizaste la labor.',
            },
            {
                icon: '🔧',
                title: 'Tipo de labor',
                desc: 'Elige el tipo: laboreo de suelo, siembra, trasplante, poda, aclareo, recolección manual, tratamiento manual u otros.',
            },
            {
                icon: '📝',
                title: 'Descripción',
                desc: 'Añade los detalles que consideres útiles: maquinaria usada, incidencias, condiciones del campo, etc.',
            },
        ],
    },
    riego: {
        title: '💧 Riego',
        intro: 'Anota cada aplicación de agua por parcela. Sirve para justificar el consumo hídrico y cumplir con los planes de riego.',
        steps: [
            {
                icon: '🗺️',
                title: 'Parcela',
                desc: 'Selecciona la parcela regada.',
            },
            {
                icon: '💧',
                title: 'Tipo de riego',
                desc: 'Indica el sistema: goteo, aspersión, pivot, gravedad u otro. Si usas varios en la misma parcela, registra una entrada por sistema.',
            },
            {
                icon: '⏱️',
                title: 'Horas y volumen',
                desc: 'Pon las horas que estuvo el riego en marcha. Si dispones del contador, añade también el volumen en m³ — es el dato más preciso.',
            },
        ],
    },
    cosecha: {
        title: '📦 Cosecha / Producción',
        intro: 'Registra lo que recolectas: cantidad, destino y número de lote para la trazabilidad.',
        steps: [
            {
                icon: '🗺️',
                title: 'Parcela',
                desc: 'Indica de qué parcela proviene la cosecha.',
            },
            {
                icon: '⚖️',
                title: 'Producción',
                desc: 'Escribe los kilogramos (o toneladas) recolectados. Si pesaste en báscula, usa ese dato; si no, una estimación razonable.',
            },
            {
                icon: '📦',
                title: 'Destino y lote',
                desc: 'Indica el destino (venta, autoconsumo, almacén) y el número de lote si lo tienes. El lote permite rastrear el producto en caso de alerta sanitaria.',
            },
        ],
    },
    compra: {
        title: '🛒 Compras',
        intro: 'Registra las compras de fitosanitarios, fertilizantes y semillas. Es obligatorio conservar la trazabilidad de los productos usados.',
        steps: [
            {
                icon: '🧪',
                title: 'Tipo y producto',
                desc: 'Indica si es un fitosanitario, fertilizante, semilla u otro insumo, y escribe el nombre comercial exacto.',
            },
            {
                icon: '📏',
                title: 'Cantidad',
                desc: 'Anota las unidades compradas (litros, kg, sacos…). Debe cuadrar con las dosis que registres en los tratamientos y fertilizaciones.',
            },
            {
                icon: '🏪',
                title: 'Proveedor y albarán',
                desc: 'Guarda el nombre del proveedor y el número de factura o albarán. Si hay una inspección, pueden pedir los justificantes de compra.',
            },
        ],
    },
    abonado: {
        title: '📋 Plan de Abonado',
        intro: 'Planifica las necesidades de nutrientes (N, P, K) de cada parcela para toda la campaña, según el RD 934/2025.',
        steps: [
            {
                icon: '🗺️',
                title: 'Parcela y cultivo',
                desc: 'Selecciona la parcela y confirma el cultivo de la campaña. El plan de abonado se calcula para ese cultivo concreto.',
            },
            {
                icon: '🌱',
                title: 'Necesidades NPK',
                desc: 'Indica las unidades fertilizantes de nitrógeno (N), fósforo (P₂O₅) y potasio (K₂O) previstas. Puedes basarte en análisis de suelo o en las tablas de referencia del cultivo.',
            },
            {
                icon: '📅',
                title: 'Fraccionamiento',
                desc: 'Si aplicas el abono en varias pasadas, registra cada aplicación por separado en el módulo de Fertilización. El plan de abonado es la previsión; los registros de fertilización son lo que realmente hiciste.',
            },
        ],
    },
    cultivo_campana: {
        title: '🌾 Cultivo de Campaña',
        intro: 'Asigna el cultivo y variedad a cada parcela para la campaña activa. Es obligatorio para que el cuaderno oficial sea correcto.',
        steps: [
            {
                icon: '🗺️',
                title: 'Parcela',
                desc: 'Selecciona la parcela a la que vas a asignar el cultivo de esta campaña.',
            },
            {
                icon: '🌾',
                title: 'Cultivo y variedad',
                desc: 'Elige la especie (trigo, olivar, viñedo…) y escribe la variedad si la conoces. Estos datos aparecen en el PDF oficial del cuaderno.',
            },
            {
                icon: '📐',
                title: 'Superficie cultivada',
                desc: 'Indica los hectáreas dedicadas a este cultivo en la parcela. Puede ser menor que la superficie total si parte está en barbecho.',
            },
        ],
    },
    uhc: {
        title: '🌱 Grupos UHC',
        intro: 'Un grupo junta parcelas que se trabajan igual (mismo cultivo) para que apuntes las faenas una sola vez. La administración lo llama "Unidad Homogénea de Cultivo (UHC)".',
        steps: [
            {
                icon: '➕',
                title: 'Crear un grupo',
                desc: 'Pulsa "+ Nuevo grupo", dale un nombre (ej: "Olivar norte") y selecciona las parcelas que lo forman. Todas deben tener el mismo cultivo.',
            },
            {
                icon: '✂️',
                title: 'Grupos al crear la parcela',
                desc: 'Si das de alta una parcela del SIGPAC dividida en varios trozos (recintos), el cuaderno te propone crear el grupo automáticamente con los trozos que comparten cultivo. Si en ese momento los dejaste sueltos, puedes agruparlos aquí cuando quieras.',
            },
            {
                icon: '🌿',
                title: 'Usar el grupo en un tratamiento',
                desc: 'Cuando registres un tratamiento fitosanitario, podrás seleccionar el grupo UHC en vez de una sola parcela. El sistema replica el registro en todas las parcelas del grupo.',
            },
            {
                icon: '✏️',
                title: 'Editar y deshacer',
                desc: 'Pulsa sobre cualquier grupo para editarlo: cambiar el nombre, añadir o quitar parcelas. Y si te arrepientes, elimínalo sin miedo: las parcelas no se tocan y las faenas ya apuntadas se quedan en el cuaderno de cada trozo.',
            },
        ],
    },
    planes: {
        title: '💳 Planes y suscripción',
        intro: 'Elige el plan que mejor se adapta a tu explotación. Puedes cambiar en cualquier momento.',
        steps: [
            {
                icon: '🆓',
                title: 'Plan Básico',
                desc: 'Incluye todas las funciones del cuaderno de campo: parcelas SIGPAC, tratamientos, fertilización, labores, riego y exportación PDF. Suficiente para la mayoría de explotaciones.',
            },
            {
                icon: '⚡',
                title: 'Plan Pro — compatible con SIEX',
                desc: 'Tu cuaderno es compatible con el SIEX (Sistema de Información de Explotaciones) y con lo que exige la ley, preparado para la obligatoriedad del 1 de enero de 2027. Si necesitas cumplir con esa obligación, elige Pro.',
            },
            {
                icon: '📅',
                title: 'Anual vs mensual',
                desc: 'El pago anual tiene descuento respecto al mensual. Puedes cancelar en cualquier momento; el acceso se mantiene hasta el final del período pagado.',
            },
        ],
    },
};

// ── Slides para la guía de inicio ──
const QUICKSTART_SLIDES = [
    {
        id: 1,
        emoji: '🌿',
        gradient: 'linear-gradient(160deg, #00694c 0%, #008560 100%)',
        title: '¡Bienvenido a tu cuaderno!',
        desc: 'Registra aquí todo lo que haces en la finca: tratamientos, riegos, abonados, cosechas... y cumple con la ley sin papeles.',
        preview: null,
        action: null,
    },
    {
        id: 2,
        emoji: '🗺️',
        gradient: 'linear-gradient(160deg, #1e3a5f 0%, #1d4ed8 100%)',
        title: '1. Primero, añade tus parcelas',
        desc: 'Sin parcelas no puedes registrar actividades. Ve a "Parcelas", pulsa "+ Nueva parcela" y busca tu referencia SIGPAC.',
        preview: 'parcelas',
        action: 'parcelas',
        actionLabel: 'Ir a Parcelas →',
    },
    {
        id: 3,
        emoji: '✏️',
        gradient: 'linear-gradient(160deg, #3730a3 0%, #4f46e5 100%)',
        title: '2. Anota cada actividad',
        desc: 'Pulsa el botón ✏️ del centro de la barra inferior. Elige el tipo de actividad y rellena el formulario.',
        preview: 'anotar',
        action: null,
    },
    {
        id: 4,
        emoji: '🎤',
        gradient: 'linear-gradient(160deg, #9f1239 0%, #db2777 100%)',
        title: '3. O simplemente habla',
        desc: '"Hoy apliqué herbicida en el olivar, 2 litros por hectárea." El cuaderno entiende lenguaje natural y lo registra solo.',
        preview: 'voz',
        action: null,
    },
    {
        id: 5,
        emoji: '⚠️',
        gradient: 'linear-gradient(160deg, #7c2d12 0%, #ea580c 100%)',
        title: '4. Vigila el tiempo',
        desc: 'En la pantalla de inicio verás alertas de AEMET (tormenta, granizo, calor, heladas, viento) y avisos que te dicen cuándo NO conviene tratar. Todo cruzado con tu municipio.',
        preview: 'alertas',
        action: null,
    },
    {
        id: 6,
        emoji: '📄',
        gradient: 'linear-gradient(160deg, #78350f 0%, #b45309 100%)',
        title: '5. Descarga el PDF oficial',
        desc: 'Cuando necesites el cuaderno para inspección, ve a Ajustes → Datos y exportación → Descargar PDF.',
        preview: 'pdf',
        action: 'mas',
        actionLabel: 'Ir a Ajustes →',
    },
];

// ── Mini-UI previews para los slides ──
function SlidePreview({ type }) {
    const cardStyle = {
        width: '100%',
        maxWidth: 240,
        margin: '0 auto',
        borderRadius: 14,
        overflow: 'hidden',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        background: '#f8f9fb',
    };

    if (type === 'parcelas') {
        return (
            <div style={cardStyle}>
                <div style={{ background: 'linear-gradient(135deg,#111827,#1f2937)', padding: '10px 13px' }}>
                    <div style={{ color: '#fff', fontFamily: 'Manrope', fontWeight: 800, fontSize: '0.78rem' }}>🗺️ Mis Parcelas</div>
                </div>
                <div style={{ padding: '8px 10px' }}>
                    {[
                        { label: 'Olivar norte', info: '3,2 ha · Leñosos', icon: '🌳' },
                        { label: 'Viñedo sur', info: '1,8 ha · Leñosos', icon: '🍇' },
                        { label: 'Cereal este', info: '12,4 ha · Cereales', icon: '🌾' },
                    ].map((p, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '6px 0', borderBottom: i < 2 ? '1px solid #f3f4f6' : 'none' }}>
                            <div style={{ width: 28, height: 28, background: 'linear-gradient(135deg,#00694c,#008560)', borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, flexShrink: 0 }}>{p.icon}</div>
                            <div>
                                <div style={{ fontSize: '0.66rem', color: '#111827', fontWeight: 700, lineHeight: 1.2 }}>{p.label}</div>
                                <div style={{ fontSize: '0.58rem', color: '#6b7280' }}>{p.info}</div>
                            </div>
                        </div>
                    ))}
                    <div style={{ marginTop: 8, background: 'linear-gradient(135deg,#00694c,#008560)', borderRadius: 16, padding: '6px 10px', textAlign: 'center', color: '#fff', fontSize: '0.62rem', fontWeight: 700 }}>+ Nueva parcela</div>
                </div>
            </div>
        );
    }

    if (type === 'anotar') {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, maxWidth: 200 }}>
                    {[
                        { emoji: '🌿', label: 'Fitosanitario', bg: 'linear-gradient(135deg,#00694c,#008560)' },
                        { emoji: '💧', label: 'Riego', bg: 'linear-gradient(135deg,#0369a1,#0ea5e9)' },
                        { emoji: '🌱', label: 'Fertilización', bg: 'linear-gradient(135deg,#3730a3,#4f46e5)' },
                        { emoji: '🚜', label: 'Labor agrícola', bg: 'linear-gradient(135deg,#1e3a5f,#1d4ed8)' },
                    ].map((m, i) => (
                        <div key={i} style={{ background: m.bg, borderRadius: 12, padding: '10px 8px', textAlign: 'center', boxShadow: '0 4px 12px rgba(0,0,0,0.25)' }}>
                            <div style={{ fontSize: 20 }}>{m.emoji}</div>
                            <div style={{ color: '#fff', fontSize: '0.58rem', fontWeight: 700, marginTop: 3, lineHeight: 1.2 }}>{m.label}</div>
                        </div>
                    ))}
                </div>
                <div style={{ background: 'linear-gradient(135deg,#68dbae,#86f8c9)', borderRadius: '50%', width: 48, height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, boxShadow: '0 4px 16px rgba(0,105,76,0.5)' }}>✏️</div>
            </div>
        );
    }

    if (type === 'voz') {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                <div style={{ background: 'rgba(255,255,255,0.15)', borderRadius: 14, padding: '12px 16px', maxWidth: 230, backdropFilter: 'blur(4px)' }}>
                    <div style={{ color: 'rgba(255,255,255,0.92)', fontSize: '0.75rem', fontStyle: 'italic', lineHeight: 1.55, textAlign: 'center' }}>
                        "Hoy apliqué herbicida en el olivar, 2 litros por hectárea..."
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    {[10, 18, 26, 18, 10, 22, 14].map((h, i) => (
                        <div key={i} style={{ width: 3, height: h, background: 'rgba(255,255,255,0.75)', borderRadius: 2 }} />
                    ))}
                </div>
                <div style={{ background: '#dc2626', borderRadius: '50%', width: 50, height: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, boxShadow: '0 4px 16px rgba(220,38,38,0.55)' }}>🎤</div>
            </div>
        );
    }

    if (type === 'alertas') {
        const rows = [
            { icon: '🔴', bg: 'rgba(120,20,20,0.92)', bc: '#f87171', tc: '#fca5a5', txt: 'Calor extremo (42°C) — mañana' },
            { icon: '🟠', bg: 'rgba(110,50,0,0.92)', bc: '#fb923c', tc: '#fdba74', txt: 'Lluvia intensa (35mm) — jueves' },
            { icon: '💨', bg: 'rgba(30,58,95,0.92)', bc: '#60a5fa', tc: '#93c5fd', txt: 'Viento fuerte — no tratar hoy' },
        ];
        return (
            <div style={{ ...cardStyle, background: 'linear-gradient(135deg,#111827,#1f2937)' }}>
                <div style={{ padding: '10px 12px' }}>
                    <div style={{ color: '#fff', fontFamily: 'Manrope', fontWeight: 800, fontSize: '0.74rem', marginBottom: 8 }}>⚠️ Avisos de tu zona</div>
                    {rows.map((r, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, background: r.bg, border: `1px solid ${r.bc}`, borderRadius: 9, padding: '7px 9px', marginBottom: 6 }}>
                            <span style={{ fontSize: 13 }}>{r.icon}</span>
                            <span style={{ color: r.tc, fontSize: '0.6rem', fontWeight: 700, lineHeight: 1.25 }}>{r.txt}</span>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (type === 'pdf') {
        return (
            <div style={cardStyle}>
                <div style={{ background: 'linear-gradient(135deg,#111827,#1f2937)', padding: '10px 13px' }}>
                    <div style={{ color: '#fff', fontFamily: 'Manrope', fontWeight: 800, fontSize: '0.78rem' }}>⚙️ Ajustes</div>
                </div>
                <div style={{ padding: '8px 10px' }}>
                    <div style={{ background: '#f0fdf4', borderRadius: 10, padding: '9px 10px', marginBottom: 7 }}>
                        <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#166534', marginBottom: 3 }}>📄 Exportar PDF oficial</div>
                        <div style={{ fontSize: '0.58rem', color: '#6b7280', marginBottom: 7 }}>Conforme a RD 1311/2012</div>
                        <div style={{ background: 'linear-gradient(135deg,#00694c,#008560)', borderRadius: 12, padding: '5px 10px', color: '#fff', fontSize: '0.6rem', fontWeight: 700, textAlign: 'center' }}>⬇ Descargar PDF</div>
                    </div>
                    <div style={{ background: '#f0f9ff', borderRadius: 10, padding: '9px 10px' }}>
                        <div style={{ fontSize: '0.65rem', fontWeight: 700, color: '#1e3a5f', marginBottom: 7 }}>📊 Exportar Excel</div>
                        <div style={{ background: 'linear-gradient(135deg,#1e3a5f,#1d4ed8)', borderRadius: 12, padding: '5px 10px', color: '#fff', fontSize: '0.6rem', fontWeight: 700, textAlign: 'center' }}>⬇ Descargar Excel</div>
                    </div>
                </div>
            </div>
        );
    }

    return null;
}

// ── QuickStartModal — carousel de guía de inicio ──
function QuickStartModal({ onClose, onNavigate }) {
    const { useState, useRef } = React;
    const [current, setCurrent] = useState(0);
    const touchStartX = useRef(null);

    const slide = QUICKSTART_SLIDES[current];
    const isLast = current === QUICKSTART_SLIDES.length - 1;

    const next = () => { if (isLast) { onClose(); return; } setCurrent(c => c + 1); };
    const prev = () => setCurrent(c => Math.max(0, c - 1));

    const handleTouchStart = (e) => { touchStartX.current = e.touches[0].clientX; };
    const handleTouchEnd = (e) => {
        if (touchStartX.current === null) return;
        const diff = touchStartX.current - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 50) { if (diff > 0) next(); else prev(); }
        touchStartX.current = null;
    };

    const goAndClose = (screenId) => { onClose(); if (onNavigate && screenId) onNavigate(screenId); };

    return (
        <div
            style={{ position: 'fixed', inset: 0, zIndex: 300, background: slide.gradient, display: 'flex', flexDirection: 'column', animation: 'fadeIn 0.25s ease' }}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
        >
            {/* Botón saltar */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '52px 20px 0' }}>
                <button onClick={onClose} style={{
                    background: 'rgba(255,255,255,0.18)', border: 'none',
                    borderRadius: 20, padding: '6px 14px',
                    color: '#fff', fontSize: '0.8rem', fontWeight: 600,
                    cursor: 'pointer', fontFamily: 'Work Sans, sans-serif',
                }}>Saltar ✕</button>
            </div>

            {/* Contenido central */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '16px 28px', textAlign: 'center', gap: 24 }}>
                {slide.preview ? (
                    <SlidePreview type={slide.preview} />
                ) : (
                    <div style={{ fontSize: 72, filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.3))' }}>{slide.emoji}</div>
                )}
                <div>
                    <h2 style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 800, fontSize: '1.5rem', color: '#fff', margin: '0 0 10px', lineHeight: 1.2, textShadow: '0 2px 8px rgba(0,0,0,0.2)' }}>
                        {slide.title}
                    </h2>
                    <p style={{ color: 'rgba(255,255,255,0.88)', fontSize: '0.95rem', lineHeight: 1.65, margin: 0, maxWidth: 320 }}>
                        {slide.desc}
                    </p>
                </div>
                {slide.action && (
                    <button onClick={() => goAndClose(slide.action)} style={{
                        background: 'rgba(255,255,255,0.18)', border: '1.5px solid rgba(255,255,255,0.38)',
                        borderRadius: 20, padding: '10px 20px',
                        color: '#fff', fontWeight: 700, fontSize: '0.88rem',
                        cursor: 'pointer', fontFamily: 'Work Sans, sans-serif',
                    }}>{slide.actionLabel}</button>
                )}
            </div>

            {/* Dots indicadores */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: 6, paddingBottom: 12 }}>
                {QUICKSTART_SLIDES.map((_, i) => (
                    <button key={i} onClick={() => setCurrent(i)} style={{
                        width: i === current ? 20 : 6, height: 6, borderRadius: 3, border: 'none',
                        background: i === current ? '#fff' : 'rgba(255,255,255,0.32)',
                        cursor: 'pointer', padding: 0, transition: 'all 0.22s',
                    }} />
                ))}
            </div>

            {/* Botones navegación */}
            <div style={{ display: 'flex', gap: 10, padding: '0 20px 48px' }}>
                {current > 0 && (
                    <button onClick={prev} style={{
                        flex: 1, background: 'rgba(255,255,255,0.14)', border: '1.5px solid rgba(255,255,255,0.28)',
                        borderRadius: 20, padding: '14px', color: '#fff', fontWeight: 700, fontSize: '0.9rem',
                        cursor: 'pointer', fontFamily: 'Work Sans, sans-serif',
                    }}>← Anterior</button>
                )}
                <button onClick={next} style={{
                    flex: 2, background: 'rgba(255,255,255,0.95)', border: 'none',
                    borderRadius: 20, padding: '14px', color: '#111827', fontWeight: 800, fontSize: '0.95rem',
                    cursor: 'pointer', fontFamily: 'Manrope, sans-serif',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.22)',
                }}>
                    {isLast ? '¡Empezar! 🚀' : 'Siguiente →'}
                </button>
            </div>
        </div>
    );
}

// ── HelpModal — ayuda contextual por pantalla ──
function HelpModal({ screenId, onClose }) {
    const content = HELP_SCREENS[screenId];
    if (!content) return null;

    return (
        <div className="overlay" onClick={onClose}>
            <div className="module-sheet" onClick={e => e.stopPropagation()} style={{ paddingBottom: 40 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                    <div style={{ flex: 1 }}>
                        <h3 style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 800, fontSize: '1.1rem', margin: 0 }}>{content.title}</h3>
                        <p style={{ fontSize: '0.82rem', color: '#6b7280', margin: '4px 0 0', lineHeight: 1.5 }}>{content.intro}</p>
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280', flexShrink: 0, marginLeft: 12, padding: 0 }}>✕</button>
                </div>

                <div style={{ borderTop: '1px solid #f3f4f6', marginTop: 16, paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {content.steps.map((step, i) => (
                        <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                            <div style={{
                                width: 38, height: 38, borderRadius: '50%',
                                background: 'linear-gradient(135deg,#00694c,#008560)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: 17, flexShrink: 0,
                                boxShadow: '0 2px 8px rgba(0,105,76,0.25)',
                            }}>{step.icon}</div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 700, fontSize: '0.88rem', color: '#111827', marginBottom: 2 }}>{step.title}</div>
                                <div style={{ fontSize: '0.8rem', color: '#6b7280', lineHeight: 1.6 }}>{step.desc}</div>
                            </div>
                        </div>
                    ))}
                </div>

                <button onClick={onClose} className="btn-primary" style={{ width: '100%', marginTop: 22, minHeight: 48, fontSize: '0.95rem' }}>
                    ¡Entendido!
                </button>
            </div>
        </div>
    );
}

// ── HelpButton — botón "?" reutilizable para cabeceras ──
function HelpButton({ screenId, style }) {
    const [show, setShow] = React.useState(false);
    return (
        <>
            <button
                onClick={() => setShow(true)}
                title="Ayuda"
                style={{
                    background: 'rgba(255,255,255,0.14)', border: 'none',
                    borderRadius: '50%', width: 32, height: 32,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff', fontSize: '0.85rem', fontWeight: 800,
                    cursor: 'pointer', fontFamily: 'Manrope, sans-serif',
                    flexShrink: 0,
                    ...(style || {}),
                }}
            >{'?'}</button>
            {show && <HelpModal screenId={screenId} onClose={() => setShow(false)} />}
        </>
    );
}
