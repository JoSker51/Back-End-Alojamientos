# Fragmento de auth_utils.py - bcrypt + JWT + decorador @require_auth
import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import bcrypt
import jwt
from flask import g, jsonify, request


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _expiration_delta() -> timedelta:
    raw = os.getenv("JWT_EXPIRES_IN", "7d").strip().lower()
    try:
        if raw.endswith("d"): return timedelta(days=int(raw[:-1]))
        if raw.endswith("h"): return timedelta(hours=int(raw[:-1]))
        if raw.endswith("m"): return timedelta(minutes=int(raw[:-1]))
        return timedelta(seconds=int(raw))
    except ValueError:
        return timedelta(days=7)


def make_token(user_id, rol: str) -> str:
    secret = os.getenv("JWT_SECRET", "change-me-in-prod")
    payload = {
        "sub": str(user_id),
        "rol": rol,
        "exp": datetime.now(timezone.utc) + _expiration_delta(),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    secret = os.getenv("JWT_SECRET", "change-me-in-prod")
    return jwt.decode(token, secret, algorithms=["HS256"])


def require_auth(*allowed_roles):
    """Decorador: valida JWT, opcionalmente filtra por rol."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return jsonify({"error": "No autorizado"}), 401
            token = header[7:].strip()
            try:
                payload = decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expirado"}), 401
            except jwt.PyJWTError:
                return jsonify({"error": "Token invalido"}), 401
            rol = payload.get("rol")
            if allowed_roles and rol not in allowed_roles:
                return jsonify({"error": "Permiso denegado"}), 403
            g.user_id  = payload.get("sub")
            g.user_rol = rol
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# Endpoint de verificacion: el frontend lo llama al cargar para confirmar el token
# Fragmento de routes/auth.py
@auth_bp.get("/me")
@require_auth()
def me():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, nombre, apellido, email, rol FROM usuario WHERE id = %s",
            (g.user_id,),
        )
        user = cur.fetchone()
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    return jsonify({"user": dict(user)})
