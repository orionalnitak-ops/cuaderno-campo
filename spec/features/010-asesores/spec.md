# Diseño: Ficha de Asesor Fitosanitario

**Estado:** aprobado
**Origen:** petición de Cristóbal (agricultor piloto, julio 2026) — "igual que guarda los datos del aplicador, ¿se podrían guardar los datos del técnico del asesoramiento?"

**Motivación:** el asesor fitosanitario es un campo exigido por la **Orden APA/204/2023** en el registro de tratamientos. Hoy se guarda como **texto libre** en `tratamientos.asesor`, tecleado a mano en cada tratamiento. Eso produce tres problemas:

1. **Erratas.** El mismo técnico aparece como "Mª Jose", "María José", "M. José" en el PDF oficial.
2. **No se guarda su nº ROPO.** El carnet ROPO tiene sección de *asesor*, distinta de la de aplicador. Hoy ese dato no existe en ninguna parte de la app, pese a que identifica legalmente al técnico.
3. **Mala compatibilidad SIEX.** Una cadena de texto no es exportable de forma estructurada; un asesor con NIF + ROPO sí.

El aplicador ya resuelve esto correctamente (tabla `aplicadores`, selector, validación ROPO). Esta feature lleva el asesor al mismo nivel.

---

## Alcance

### Incluido

- Tabla `asesores` como entidad reutilizable por usuario.
- Columna `tratamientos.asesor_id` (FK lógica), **conservando** la columna `asesor` TEXT existente.
- CRUD `/api/asesores` (blueprint propio).
- Selector de asesor en el formulario de tratamiento, con alta rápida inline (mismo patrón que aplicador).
- Sección "Asesores" en Configuración.
- Exports PDF y Excel: nombre + nº ROPO del asesor, con **fallback** al texto antiguo.
- Caché offline (PWA) igual que aplicadores.

### No incluido

- **Panel de asesor** (cuenta desde la que un técnico ve a varios agricultores). Es otra feature distinta que se llama parecido — ver `CONTEXTO.md:38`.
- Firma digital del asesor en el plan de abonado (RD 934/2025, zonas vulnerables). Plazo ≥ sept 2027; esta tabla será su cimiento cuando toque.
- Validación del nº ROPO contra el registro oficial (no hay API pública).
- Migración automática del texto libre existente a fichas. Los datos antiguos se conservan y se muestran, pero no se convierten solos.

---

## Decisiones de diseño

### 1. Tabla nueva `asesores`, no reutilizar `aplicadores` con un campo "rol"

**Motivo:** la sección del carnet ROPO es distinta, la validación es distinta (ver decisión 2), los campos propios del asesor no aplican al aplicador (titulación, empresa asesora), y `aplicadores` ya arrastra su propia caché en IndexedDB. El coste extra de una tabla separada es mínimo y evita un modelo confuso para el agricultor.

Nota: que la misma persona sea aplicador y asesor es posible y se resuelve dándola de alta en las dos secciones. Es intencionado — son dos roles legales distintos.

```
asesores: id, user_id, nombre, nif, num_ropo, titulacion, empresa, telefono, email, activo
```

### 2. El nº ROPO del asesor avisa, pero NO bloquea

A diferencia del aplicador, que sí bloquea el guardado si no tiene ROPO ([tratamientos.py:133-143](../../../backend/blueprints/tratamientos.py)).

**Motivo:** el agricultor casi siempre sabe el ROPO de su propio carnet, pero el de su técnico externo no lo tiene a mano. Si bloqueamos, el agricultor no puede registrar el tratamiento y el módulo se vuelve inusable justo en el momento en que está en la parcela. Se muestra un aviso visible en la ficha y en Configuración.

### 3. Se conserva la columna `asesor` TEXT — no se sustituye

**Motivo:** los pilotos (Lourdes, Cristóbal) ya tienen tratamientos con texto en esa columna. El PDF debe seguir mostrándolos.

**Patrón de lectura, en este orden:**
1. Si hay `asesor_id` y la ficha existe → nombre de la ficha (+ ROPO).
2. Si no → valor de la columna `asesor` TEXT.
3. Si no → vacío.

El formulario deja de escribir en `asesor` TEXT para registros nuevos que usen ficha, pero el campo de texto libre sigue disponible como salida de emergencia.

### 4. Aislamiento por usuario (IDOR)

Toda query filtra por `user_id`. Al guardar un tratamiento con `asesor_id`, se verifica que el asesor pertenece al usuario efectivo antes de aceptar el registro — mismo patrón que `aplicador_id` y que los fixes IDOR de los PRs #27-30.

---

## Criterios de aceptación

- [ ] Puedo dar de alta un asesor desde Configuración → Asesores con nombre, NIF, ROPO, titulación y empresa.
- [ ] En el formulario de tratamiento aparece un desplegable con mis asesores; si no tengo ninguno, puedo crear uno sin salir del formulario.
- [ ] El asesor **no** es obligatorio para guardar un tratamiento (no lo era antes y no debe serlo ahora).
- [ ] Si el asesor elegido no tiene ROPO, el tratamiento **se guarda igual** y se muestra un aviso.
- [ ] Enviar un `asesor_id` de otro usuario devuelve error y no guarda.
- [ ] El PDF oficial muestra "Asesor: NOMBRE (ROPO nnn)" en la fila gris de trazabilidad.
- [ ] Los tratamientos antiguos con texto libre siguen mostrando ese texto en PDF y Excel.
- [ ] El Excel incluye columna "Nº ROPO Asesor" junto a la de "Asesor".
- [ ] Sin conexión, el desplegable de asesores se rellena desde la caché.
- [ ] La pantalla de ayuda documenta la sección de asesores.
