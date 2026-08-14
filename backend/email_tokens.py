"""email_tokens.py — Tokens de un solo uso para verificación y reset de contraseña.

Guardados en la tabla `email_tokens`. La comparación de caducidad se hace en
Python (no con funciones de fecha del motor) para que se comporte igual en SQLite
y PostgreSQL, igual que el resto del proyecto trata `trial_ends_at` como texto.
"""
import secrets
import datetime

from db import one

_FMT = '%Y-%m-%d %H:%M:%S'


def crear_token(conn, user_id, tipo, ttl_horas):
    """Crea un token nuevo y devuelve su cadena. De paso, limpia tokens caducados
    para que la tabla no crezca sin límite. No hace commit (lo hace quien llama)."""
    ahora = datetime.datetime.utcnow().strftime(_FMT)
    conn.execute("DELETE FROM email_tokens WHERE expires_at < ?", (ahora,))
    token = secrets.token_urlsafe(32)
    expires = (datetime.datetime.utcnow() + datetime.timedelta(hours=ttl_horas)).strftime(_FMT)
    conn.execute(
        "INSERT INTO email_tokens (token, user_id, tipo, expires_at) VALUES (?,?,?,?)",
        (token, user_id, tipo, expires),
    )
    return token


def consumir_token(conn, token, tipo):
    """Valida un token del tipo dado y lo sella de forma atómica (el UPDATE lleva
    su propia condición used_at IS NULL, así que dos peticiones concurrentes con
    el mismo token no pueden colarse las dos). Devuelve el user_id o None.
    Rechaza: inexistente, tipo distinto, ya usado, caducado. No hace commit."""
    if not token:
        return None
    fila = one(conn,
               "SELECT id, user_id, expires_at FROM email_tokens WHERE token=? AND tipo=?",
               (token, tipo))
    if not fila:
        return None
    try:
        exp = datetime.datetime.strptime(str(fila['expires_at'])[:19], _FMT)
    except (ValueError, TypeError):
        return None
    if exp < datetime.datetime.utcnow():
        return None
    ahora = datetime.datetime.utcnow().strftime(_FMT)
    cursor = conn.execute(
        "UPDATE email_tokens SET used_at=? WHERE id=? AND used_at IS NULL",
        (ahora, fila['id']))
    if cursor.rowcount == 0:
        return None
    return fila['user_id']
