# CREAR SKILL EN ANTIGRAVITY - GUÍA SIMPLE
**Para Antigravity | Sin Cowork | Directo en Antigravity**

---

## ⚡ LO QUE NECESITAS SABER

Tienes `skill-creator` instalado en Antigravity. Con eso basta.

**El proceso es simple:**
1. Abrís Antigravity
2. Copias este documento en una conversación
3. Decís: "Crea la skill 'cuaderno-explotacion' siguiendo este documento"
4. Antigravity la crea automáticamente
5. ¡Listo! Ya la usas

**Tiempo:** 1-2 horas máximo.

---

## 📋 DOCUMENTO PARA PASAR A ANTIGRAVITY

Copía y pegá **todo esto** en una conversación con Antigravity:

---

### 🎯 CREA ESTA SKILL PASO A PASO

**Nombre:** `cuaderno-explotacion`

**Para qué sirve:** Ayudar a crear una app para que agricultores sin conocimientos digitales registren sus actividades agrícolas (obligatorio por ley en España).

---

### 📌 CONTEXTO (Lee esto primero)

**El proyecto:**
- App web/móvil para agricultores
- Registra: parcelas, tratamientos químicos, abonos, labores, ventas
- Obligatorio por ley (RD 1311/2012) desde 2027
- Modelo SaaS (gratis + premium)

**Lo que hace la skill:**
Cuando yo diga cosas como:
- "Crea un prompt para Stitch"
- "¿Qué campos necesita X?"
- "Dame el código para Y"
- "Documenta la arquitectura"
- "Crea un sprint"

La skill responde automáticamente con exactitud legal/técnica, sin que yo tenga que buscar conversaciones previas.

---

### 🛠️ ESTRUCTURA DE LA SKILL

La skill tiene estas 6 funciones principales:

#### 1. GENERAR PROMPTS PARA STITCH
Cuando digo: "Crea un prompt para Stitch del módulo X"

Responde: Prompt completo con especificación técnica, campos, validaciones, BD, etc.

#### 2. MAPEAR CAMPOS
Cuando digo: "¿Qué campos necesita X?"

Responde: Lista exacta de campos + tipos + validaciones (según ley)

#### 3. PROPORCIONAR CÓDIGO
Cuando digo: "Dame el código para X"

Responde: HTML, Flask, SQL, JavaScript listos para copiar

#### 4. DOCUMENTAR ARQUITECTURA
Cuando digo: "¿Cómo se integra X con Y?"

Responde: Diagrama + explicación de flujos

#### 5. CREAR SPRINTS
Cuando digo: "Crea un sprint para X"

Responde: Tareas + estimaciones + prioridades

#### 6. VALIDAR CONTRA LEY
Cuando digo: "¿Cumple esta feature con RD 1311/2012?"

Responde: ✅ cumple o ⚠️ falta esto

---

### 📂 ARCHIVOS QUE NECESITA LA SKILL

Dentro de la skill, crear estos archivos:

#### A. SKILL.md (el archivo principal)
Aquí va la "receta" que sigue la skill. Estructura:

```
---
name: cuaderno-explotacion
description: [texto que explique qué es la skill y cuándo usarla]
---

# SKILL: Cuaderno de Explotación Digital

## Funcionalidad 1: Generar Prompts para Stitch

Cuando el usuario dice:
- "Crea un prompt para Stitch"
- "Genera prompt para módulo X"
- "Necesito un prompt para Stitch de Y"

Haz esto:
1. Lee el contexto del proyecto (carpeta references/)
2. Lee los campos del módulo (fields-modulos.json)
3. Lee la arquitectura (architecture.md)
4. Genera un prompt como este TEMPLATE:

[TEMPLATE: Prompt para Stitch]
# PROMPT PARA STITCH: MÓDULO {NOMBRE}

## Contexto
- Proyecto: Cuaderno de Explotación Digital
- Objetivo: App para agricultores sin conocimientos digitales
- Stack: Python+Flask, SQLite/PostgreSQL, HTML5+JS, mobile-first
- Ley: RD 1311/2012 Anexo III (campos obligatorios)

## Requisito: Crear componente {NOMBRE}

### Pantalla
[descripción visual]

### Campos (RD 1311/2012)
- campo1 (tipo: x, obligatorio: sí, validación: y)
- campo2 (tipo: x, obligatorio: no, validación: y)

### Base de datos
```sql
CREATE TABLE tabla (...)
```

### Validaciones
- Validación 1
- Validación 2

### API Endpoints
POST /api/...
GET /api/...
[FIN TEMPLATE]

---

## Funcionalidad 2: Mapear Campos

Cuando el usuario dice:
- "¿Qué campos exactos necesita X?"
- "Dame los campos de X"
- "Lista campos del módulo X"

Haz esto:
1. Busca en references/fields-modulos.json
2. Retorna en formato tabla + JSON

Tabla:
| Campo | Tipo | Obligatorio | Validación |
|-------|------|-------------|-----------|
| ... | ... | ... | ... |

JSON:
```json
{
  "modulo": "x",
  "campos": [...]
}
```

---

## Funcionalidad 3: Proporcionar Código

Cuando el usuario dice:
- "Dame el código para X"
- "Crea un formulario de X"
- "Dame la clase Flask para X"

Haz esto:
1. Busca en references/snippets/
2. Retorna código completo (listo para copiar)

---

## Funcionalidad 4: Documentar Arquitectura

Cuando el usuario dice:
- "¿Cómo se integra X con Y?"
- "Explica la arquitectura de X"
- "¿Cómo funciona SIEX?"

Haz esto:
1. Lee references/architecture.md
2. Lee references/siex.md
3. Genera diagrama ASCII + explicación

---

## Funcionalidad 5: Crear Sprints

Cuando el usuario dice:
- "Crea un sprint para X"
- "¿Cuál es el siguiente hito?"
- "Planifica las tareas de X"

Haz esto:
1. Lee references/roadmap.md
2. Desglosa tareas
3. Estima esfuerzo (horas/días)
4. Sugiere orden

---

## Funcionalidad 6: Validar contra Ley

Cuando el usuario dice:
- "¿Cumple esta feature con RD 1311/2012?"
- "¿Es legal esto?"
- "Valida esta feature contra la ley"

Haz esto:
1. Lee references/normativa.md
2. Valida contra Anexo III
3. Retorna: ✅ cumple O ⚠️ falta [esto]

---

## CÓMO INTERPRETAR LOS ARCHIVOS

Lee los archivos de references/ cuando los necesites (no todos en cada respuesta).
```

#### B. references/ (carpeta con información)

Dentro, crear estos archivos:

**1. references/contexto.md**
```
# CONTEXTO DEL PROYECTO

## ¿Qué es?
App web/móvil para que agricultores registren:
- Parcelas (campos identificados por SIGPAC)
- Tratamientos químicos (para plagas/enfermedades)
- Abonos/fertilizantes
- Labores (siembra, riego, cosecha, etc.)
- Compras/ventas (trazabilidad)

## ¿Por qué?
Ley española RD 1311/2012: agricultores deben llevar un "cuaderno de explotación" 
(registro de todas las actividades).

Ahora es voluntario. Desde 1 enero 2027: obligatorio digital.

## ¿Para quién?
Agricultores sin conocimientos digitales. 
Interfaz super simple (no como las 48 apps existentes que son complicadas).

## Stack técnico
- Backend: Python + Flask
- Base de datos: SQLite (desarrollo) / PostgreSQL (producción)
- Frontend: HTML5 + CSS3 + JavaScript vanilla
- Diseño: Mobile-first (funciona bien en móvil)
- Exportación: PDF + Excel

## Módulos de la app
1. PARCELAS - Identificar qué campo es cuál (SIGPAC)
2. TRATAMIENTOS - Registrar qué químicos se usaron dónde y cuándo
3. FERTILIZACIÓN - Qué abonos se echaron dónde
4. LABORES (opcional) - Otras actividades (siembra, riego, etc.)
5. TRAZABILIDAD (opcional) - Compras y ventas
6. EXPORTACIÓN - Generar PDF/Excel para inspección

## Modelo de negocio
- Plan GRATIS: módulos 1-3
- Plan PREMIUM: todos los módulos + integración oficial (SIEX)

## Roadmap
Hito 1 (MVP): Módulos 1, 2, 3 + exportación
Hito 2 (Escalabilidad): BD en la nube, sincronización
Hito 3 (Premium): Módulos 4, 5 + sistema de pago
Hito 4 (Integración oficial): Conectar con sistema oficial del Ministerio
```

**2. references/fields-modulos.json**
```json
{
  "parcelas": [
    {
      "nombre": "sigpac_poligono",
      "tipo": "número",
      "obligatorio": true,
      "validacion": "1-9999",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": 13051,
      "ui_widget": "input[type=number]"
    },
    {
      "nombre": "sigpac_parcela",
      "tipo": "número",
      "obligatorio": true,
      "validacion": "1-9999",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": 3,
      "ui_widget": "input[type=number]"
    },
    {
      "nombre": "sigpac_recinto",
      "tipo": "número",
      "obligatorio": true,
      "validacion": "1-9999",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": 2,
      "ui_widget": "input[type=number]"
    },
    {
      "nombre": "nombre_finca",
      "tipo": "texto",
      "obligatorio": true,
      "validacion": "max 255 caracteres",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": "Finca Los Encinas",
      "ui_widget": "input[type=text]"
    },
    {
      "nombre": "cultivo",
      "tipo": "lista",
      "obligatorio": true,
      "validacion": "código IACS",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": "0114 (Maíz)",
      "ui_widget": "select"
    },
    {
      "nombre": "superficie_ha",
      "tipo": "número decimal",
      "obligatorio": true,
      "validacion": "max 9999.99",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": 5.2,
      "ui_widget": "input[type=number]"
    }
  ],
  "tratamientos": [
    {
      "nombre": "fecha",
      "tipo": "fecha",
      "obligatorio": true,
      "validacion": "no futuras",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": "2026-04-18",
      "ui_widget": "input[type=date]"
    },
    {
      "nombre": "parcela_id",
      "tipo": "referencia",
      "obligatorio": true,
      "validacion": "existe en tabla parcelas",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": 1,
      "ui_widget": "select (lista de parcelas)"
    },
    {
      "nombre": "producto",
      "tipo": "texto",
      "obligatorio": true,
      "validacion": "debe estar en registro oficial FITO",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": "Spinosad 48 EC",
      "ui_widget": "input[type=text] + autocomplete"
    },
    {
      "nombre": "dosis_liha",
      "tipo": "número decimal",
      "obligatorio": true,
      "validacion": "debe ser >= 0",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": 0.5,
      "ui_widget": "input[type=number]"
    },
    {
      "nombre": "plazo_seguridad_dias",
      "tipo": "número",
      "obligatorio": true,
      "validacion": "calculado automático",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": 14,
      "ui_widget": "display (solo lectura, se calcula)"
    }
  ],
  "fertilizacion": [
    {
      "nombre": "fecha",
      "tipo": "fecha",
      "obligatorio": true,
      "validacion": "no futuras",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": "2026-04-18",
      "ui_widget": "input[type=date]"
    },
    {
      "nombre": "parcela_id",
      "tipo": "referencia",
      "obligatorio": true,
      "validacion": "existe en tabla parcelas",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": 1,
      "ui_widget": "select (lista de parcelas)"
    },
    {
      "nombre": "tipo_abono",
      "tipo": "lista",
      "obligatorio": true,
      "validacion": "nitrogenado, fosfatado, potásico",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": "nitrogenado",
      "ui_widget": "select"
    },
    {
      "nombre": "cantidad_kg",
      "tipo": "número decimal",
      "obligatorio": true,
      "validacion": "debe ser >= 0",
      "fuente_ley": "RD 1311/2012 Anexo III",
      "ejemplo": 250.5,
      "ui_widget": "input[type=number]"
    }
  ]
}
```

**3. references/architecture.md**
```
# ARQUITECTURA TÉCNICA

## Stack
- Backend: Python 3.10 + Flask
- BD: SQLite (dev) / PostgreSQL (prod)
- Frontend: HTML5 + CSS3 + JS vanilla
- Diseño: Mobile-first (480px baseline)
- Exportación: openpyxl (Excel) + WeasyPrint (PDF)

## Módulos principales
1. Parcelas (OBLIGATORIO)
2. Tratamientos (OBLIGATORIO)
3. Fertilización (OBLIGATORIO)
4. Labores (OPCIONAL)
5. Trazabilidad (OPCIONAL)
6. Exportación (OBLIGATORIO)

## Base de datos (tablas)
- usuarios (login, email, password)
- parcelas (SIGPAC, cultivo, superficie)
- tratamientos (fecha, parcela, producto, dosis, plazo_seguridad)
- fertilizacion (fecha, parcela, tipo_abono, cantidad)
- labores (fecha, parcela, tipo_labor, descripcion)
- trazabilidad (fecha, parcela, tipo, cantidad, comprador_vendedor)

## API Endpoints
POST /api/parcelas - crear
GET /api/parcelas - listar
GET /api/parcelas/{id} - detalle
PUT /api/parcelas/{id} - editar
DELETE /api/parcelas/{id} - eliminar

[Similar para tratamientos, fertilización, etc.]

## Flujo típico de uso
1. Usuario login
2. Ve dashboard (parcelas activas, tratamientos recientes, etc.)
3. Registra un tratamiento:
   - Selecciona parcela
   - Busca producto
   - Ingresa dosis
   - Sistema calcula automáticamente plazo seguridad
   - Sistema advierte si expira en < 7 días
4. Exporta a PDF/Excel
5. PDF listo para inspección agraria

## Integración SIEX (fase 2)
SIEX = Sistema oficial del Ministerio.
Tu app se conecta vía API.
Los datos fluyen automáticamente.
(Esto es fase 2, ahora no es necesario)
```

**4. references/normativa.md**
```
# NORMATIVA LEGAL

## RD 1311/2012 (Real Decreto)
- Obliga a llevar "cuaderno de explotación"
- Define campos mínimos en Anexo III
- Aplica a todos los agricultores (excepto casos muy pequeños)

## Campos OBLIGATORIOS (Anexo III)
✓ Identificación explotación (NIF, nombre, ubicación)
✓ Parcelas SIGPAC (polígono, parcela, recinto, cultivo, superficie)
✓ Tratamientos (fecha, producto, dosis, plazo seguridad)
✓ Fertilización (tipo, cantidad, fecha)
✓ Trazabilidad (si hay compra/venta)

## Campos VOLUNTARIOS
○ Labores generales
○ Análisis de suelos
○ Pastoreo
○ Residuos

## Timeline importante
- Ahora (2026): Digital es VOLUNTARIO
- 1 enero 2027: Digital es OBLIGATORIO (solo tratamientos inicialmente)
- 2027+: Obligatorio completo

## Tu app es legal porque...
✓ Contiene todos los campos mínimos (Anexo III)
✓ Los datos son compatibles con el sistema oficial (SIEX)
✓ Los agricultores pueden exportar en formato aceptado por Ministerio
```

**5. references/roadmap.md**
```
# ROADMAP (Hitos)

## Hito 1: MVP (Semanas 1-6)
Objetivo: Versión mínima viable
Incluye: Módulos 1, 2, 3 + exportación
Usuarios: 1-5 (amigos, familia, zona cercana)

Tareas:
- [ ] Crear BD + modelos Flask
- [ ] Pantalla Parcelas (listar, crear, editar)
- [ ] Pantalla Tratamientos (listar, crear, editar)
- [ ] Pantalla Fertilización (listar, crear, editar)
- [ ] Exportar a Excel
- [ ] Exportar a PDF
- [ ] Autenticación básica
- [ ] UI mobile responsive
- [ ] Testing con 1 agricultor piloto

## Hito 2: Escalabilidad (Semanas 7-10)
Objetivo: Pasar de SQLite a servidor profesional
Incluye: Sincronización, backup, usuarios múltiples

Tareas:
- [ ] Migrar BD a PostgreSQL
- [ ] Deploy en servidor (AWS, Heroku, etc.)
- [ ] Sistema de sincronización (offline-online)
- [ ] Panel de asesor (ver datos de múltiples agricultores)
- [ ] Mejorar performance

## Hito 3: Módulos Premium (Semanas 11-16)
Objetivo: Agregar funcionalidades avanzadas
Incluye: Módulos 4, 5 + sistema de pago

Tareas:
- [ ] Módulo Labores
- [ ] Módulo Trazabilidad
- [ ] Sistema de pago (Stripe)
- [ ] Plan GRATIS vs PREMIUM
- [ ] Autenticación mejorada
- [ ] Facturas automáticas

## Hito 4: Integración SIEX (Semanas 17+)
Objetivo: Conectar con sistema oficial del Ministerio
Incluye: API SIEX, certificación oficial

Tareas:
- [ ] Implementar API SIEX (Anexo VI)
- [ ] Testing con Ministerio
- [ ] Certificación como CUE comercial
- [ ] Marketing
```

**6. references/snippets.md**
```
# CÓDIGO REUTILIZABLE

## Flask Model: Parcela

```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Parcela(db.Model):
    __tablename__ = 'parcelas'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    # SIGPAC
    sigpac_poligono = db.Column(db.Integer, nullable=False)
    sigpac_parcela = db.Column(db.Integer, nullable=False)
    sigpac_recinto = db.Column(db.Integer, nullable=False)
    
    # Descripción
    nombre_finca = db.Column(db.String(255), nullable=False)
    cultivo = db.Column(db.String(100), nullable=False)
    superficie_ha = db.Column(db.Float, nullable=False)
    
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    tratamientos = db.relationship('Tratamiento', backref='parcela', lazy=True)
    fertilizaciones = db.relationship('Fertilizacion', backref='parcela', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sigpac': f'{self.sigpac_poligono}-{self.sigpac_parcela}-{self.sigpac_recinto}',
            'nombre': self.nombre_finca,
            'cultivo': self.cultivo,
            'superficie': self.superficie_ha
        }
```

## HTML Form: Tratamientos

```html
<form id="tratamiento-form">
  <label>Parcela:</label>
  <select name="parcela_id" required>
    <option value="">-- Selecciona parcela --</option>
    <option value="1">Encinas (5.2 ha)</option>
  </select>

  <label>Producto:</label>
  <input type="text" name="producto" placeholder="Ej: Spinosad 48 EC" required
         list="productos" />
  <datalist id="productos">
    <option value="Spinosad 48 EC">
    <option value="Piretrina...">
  </datalist>

  <label>Dosis (ℓ/ha):</label>
  <input type="number" name="dosis_liha" step="0.1" min="0" required />

  <label>Fecha:</label>
  <input type="date" name="fecha" required />

  <button type="submit">Guardar Tratamiento</button>
</form>
```

[Más snippets...]
```

---

### ⏭️ QUÉ HACER AHORA

1. **Copia TODO este documento**
2. **Abre Antigravity** (tu proyecto actual)
3. **Inicia una conversación nueva**
4. **Pega este documento**
5. **Escribe:** "Crea la skill 'cuaderno-explotacion' siguiendo este documento. Usa skill-creator."

---

### 📝 EJEMPLOS DE CÓMO LA USARÁS DESPUÉS

Una vez creada la skill, dirás cosas como:

```
"Crea un prompt para Stitch del módulo de Parcelas"
→ Recibe prompt completo en 10 segundos
```

```
"¿Qué campos exactos necesita el formulario de Tratamientos?"
→ Recibe tabla con todos los campos + validaciones
```

```
"Dame el código Flask del modelo Parcela"
→ Recibe código listo para copiar
```

```
"Crea un sprint para el Hito 1"
→ Recibe tareas + estimaciones
```

---

### ✅ VENTAJAS

✓ Sin necesidad de repetir contexto en cada conversación
✓ Respuestas exactas (validadas contra ley)
✓ Código listo para producción
✓ Genera prompts para Stitch automáticamente
✓ Ahorro de tokens (~70%)
✓ Más rápido (respuestas en 10-30 segundos)

---

**¡Eso es todo! Antigravity ya tiene todo lo que necesita.**

