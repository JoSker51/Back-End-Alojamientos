import os, uuid
from pathlib import Path
from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.utils import secure_filename
from auth_utils import require_auth
from db import get_connection

archivos_bp = Blueprint("archivos", __name__)

TIPOS_VALIDOS = ("cv", "certificacion_laboral", "documento_identidad",
                 "foto_residencia", "otro")

@archivos_bp.post("")
@require_auth()
def subir():
    tipo = (request.form.get("tipo") or "otro").strip()
    f = request.files.get("archivo")
    if tipo not in TIPOS_VALIDOS:
        return jsonify({"error": "Tipo invalido"}), 400
    if not f: return jsonify({"error": "Falta archivo"}), 400

    nombre_disco = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
    user_dir = Path(current_app.root_path) / "uploads" / str(g.user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    f.save(str(user_dir / nombre_disco))

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO archivo (usuario_id, tipo, nombre_original, ruta, mime_type)
               VALUES (%s, %s, %s, %s, %s) RETURNING id, tipo""",
            (g.user_id, tipo, f.filename, f"{g.user_id}/{nombre_disco}", f.mimetype),
        )
        conn.commit()
        return jsonify({"archivo": dict(cur.fetchone())}), 201
