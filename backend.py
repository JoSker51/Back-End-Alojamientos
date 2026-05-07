from flask import Blueprint, g, jsonify, request
from auth_utils import require_auth
from db import get_connection

contrataciones_bp = Blueprint("contrataciones", __name__)

@contrataciones_bp.post("/<cont_id>/irregularidad")
@require_auth("prestador")
def reportar(cont_id):
    descripcion = (request.get_json().get("descripcion") or "").strip()
    if not descripcion:
        return jsonify({"error": "descripcion requerida"}), 400
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT estado, arrendador_id FROM contratacion
               WHERE id=%s AND prestador_id=%s""",
            (cont_id, g.user_id),
        )
        cont = cur.fetchone()
        if not cont or cont["estado"] not in ("aceptada", "en_progreso"):
            return jsonify({"error": "Estado invalido"}), 409
        cur.execute(
            """INSERT INTO irregularidad (contratacion_id, prestador_id, descripcion)
               VALUES (%s, %s, %s) RETURNING id, descripcion, creado_en""",
            (cont_id, g.user_id, descripcion),
        )
        irr = cur.fetchone()
        # Notificar al arrendador
        cur.execute(
            """INSERT INTO notificacion (contratacion_id, destinatario_id, mensaje)
               VALUES (%s, %s, %s)""",
            (cont_id, cont["arrendador_id"], f"Queja reportada: {descripcion[:100]}"),
        )
        conn.commit()
    return jsonify({"irregularidad": dict(irr)}), 201
