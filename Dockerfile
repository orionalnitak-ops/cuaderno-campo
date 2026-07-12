FROM node:20-slim AS js-build
WORKDIR /build
COPY frontend/package.json .
RUN npm install
COPY frontend/*.jsx ./src/
RUN npx babel src --out-dir dist --presets @babel/preset-react

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY scripts/ ./scripts/
# Reemplazar JSX originales con JS pre-compilados
COPY --from=js-build /build/dist/ ./frontend/dist/

# Ejecutar como usuario no-root (defensa en profundidad: si un fallo permitiera
# ejecución de código, no sería como root del contenedor). gunicorn escucha en
# el 8000 (puerto no privilegiado) y la app no escribe en disco en producción
# (usa PostgreSQL/Supabase), así que no necesita permisos de root.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/backend
EXPOSE 8000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--preload"]
