# 029 — Checklist de ejecución

Rama: `029-exportar-por-secciones` sobre `main`.
Un commit por bloque. El backend se termina y se prueba antes de tocar el frontend.

---

## Backend

- [ ] **T1** `backend/helpers.py`: constante `SECCIONES` (8 claves) y función
      `parse_secciones(arg) -> (set, completo)`. Nunca devuelve conjunto vacío.
- [ ] **T2** `backend/blueprints/imports_exports.py`: las dos rutas leen
      `request.args.get('secciones')` y pasan `(secciones, completo)`.
      No se toca nada más de las rutas.
- [ ] **T3** `backend/exports.py`: `export_excel(..., secciones=None)`.
      Un `if` por `create_sheet`. `PORTADA` siempre. `COMPRAS-VENTAS` conserva
      su condición actual **y** suma la nueva.
- [ ] **T4** Tests de Excel (casos 1-5 del plan). Pasan en verde.
- [ ] **T5** `backend/export_pdf.py`: `export_pdf(..., secciones=None, completo=True)`.
      Un `if` por `_section_*()`. Los `Spacer` solo si la sección anterior salió.
      Portada siempre.
- [ ] **T6** `backend/export_pdf.py`: **marca de Extracto, los tres sitios a la vez**
      — pie de página (`_PageTemplate`), subtítulo de portada (`_cover_page`) y
      metadatos (`SimpleDocTemplate`). Commit propio.
      Los subtítulos de cada sección NO se tocan.
- [ ] **T7** Tests de PDF (casos 6-8 del plan). Pasan en verde.

## Frontend

- [ ] **T8** `screens_settings.jsx`: `BotonPdfOficial` → `BotonExportar({ formato, ... })`.
      Tres pasos internos: `nif?` → `lista` → descarga.
      Textos: "Guardar y continuar" / "Continuar sin el NIF".
- [ ] **T9** El aviso del NIF pasa a saltar **también en Excel**. Sigue sin bloquear.
- [ ] **T10** La lista: "Todas" marcado al abrir + la máquina de estados de la spec.
      Filas de 44 px mínimo.
- [ ] **T11** Los cinco puntos de entrada usan `BotonExportar`:
      `screens_settings.jsx:677` (pdf), `:687` (excel), `app.jsx:792` (pdf),
      `:796` (excel), `screens_history.jsx:107` (excel, con `fCampana || campana`).
- [ ] **T12** `grep -rn "api/export" frontend/*.jsx` no devuelve nada.

## Cierre

- [ ] **T13** `cd frontend && npm run build`.
- [ ] **T14** Prueba manual en local **y desde el móvil**:
      (a) descargar sin tocar nada y comparar con un PDF/Excel de antes del cambio;
      (b) solo fitosanitarios → PDF dice "Extracto" en portada y pie, Excel con 2 hojas;
      (c) marcar las ocho a mano → vuelve el sello oficial;
      (d) cuenta sin NIF → el aviso salta en los dos formatos, antes de la lista.
- [ ] **T15** `ruff` limpio (el hook avisa, no bloquea: mirar `returncode`, no el texto).
- [ ] **T16** PR contra `main`. Recordar: producción devuelve 502 un par de
      minutos tras el merge — es EasyPanel reiniciando, no un fallo.

---

## Invariantes que no se negocian

1. Sin `?secciones`, el PDF y el Excel salen **idénticos a hoy**.
2. Nunca se genera un fichero vacío ni un libro sin hojas.
3. El sello del Anexo III cae **en los tres sitios** o no cae en ninguno.
4. El filtro decide **qué tablas**, nunca **qué filas**: `parcela_scope_clause`
   y el `user_id` de cada consulta no se tocan.
5. El aviso del NIF avisa, no impide.
