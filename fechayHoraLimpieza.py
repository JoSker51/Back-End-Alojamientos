from flask import Blueprint, g, jsonify, request
from auth_utils import require_auth
from db import get_connection

contrataciones_bp = Blueprint("contrataciones", __name__)

@contrataciones_bp.post("")
@require_auth("arrendador")
def crear():
    data = request.get_json() or {}
    prestador_id = data.get("prestador_id")
    disponibilidad_id = data.get("disponibilidad_id")
    if not prestador_id or not disponibilidad_id:
        return jsonify({"error": "prestador_id y disponibilidad_id requeridos"}), 400

    with get_connection() as conn, conn.cursor() as cur:
        # Verifica que la disponibilidad existe y esta libre
        cur.execute(
            """SELECT id, estado, fecha, franja_horaria
               FROM disponibilidad
               WHERE id = %s AND prestador_id = %s""",
            (disponibilidad_id, prestador_id),
        )
        disp = cur.fetchone()
        if not disp:
            return jsonify({"error": "Disponibilidad no encontrada"}), 404
        if disp["estado"] != "disponible":
            return jsonify({"error": "Franja ya no disponible"}), 409

        # Crea la contratacion
        cur.execute(
            """INSERT INTO contratacion (arrendador_id, prestador_id, disponibilidad_id)
               VALUES (%s, %s, %s) RETURNING id, estado""",
            (g.user_id, prestador_id, disponibilidad_id),
        )
        cont = cur.fetchone()

        # Notifica al prestador
        cur.execute("SELECT nombre, apellido FROM usuario WHERE id=%s", (g.user_id,))
        arr = cur.fetchone()
        cur.execute(
            """INSERT INTO notificacion (contratacion_id, destinatario_id, mensaje)
               VALUES (%s, %s, %s)""",
            (cont["id"], prestador_id,
             f"{arr['nombre']} {arr['apellido']} solicita servicio "
             f"el {disp['fecha'].isoformat()} ({disp['franja_horaria']}).")
        )
        conn.commit()
    return jsonify({"contratacion": dict(cont)}), 201
