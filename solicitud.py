# Fragmento de routes/contrataciones.py
# Devuelve todas las contrataciones donde este prestador es el destinatario,
# con datos del arrendador, fecha y franja del servicio.
from flask import Blueprint, g, jsonify
from auth_utils import require_auth
from db import get_connection

contrataciones_bp = Blueprint("contrataciones", __name__)


@contrataciones_bp.get("/recibidas")
@require_auth("prestador")
def recibidas():
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.estado, c.solicitado_en, c.respondido_en,
                       c.iniciada_en, c.finalizada_en,
                       d.fecha, d.franja_horaria,
                       u.id       AS contraparte_id,
                       (u.nombre || ' ' || u.apellido) AS contraparte_nombre,
                       u.email    AS contraparte_email,
                       u.telefono AS contraparte_telefono,
                       cal.puntuacion, cal.comentario
                FROM contratacion c
                JOIN disponibilidad d ON d.id  = c.disponibilidad_id
                JOIN usuario u        ON u.id  = c.arrendador_id
                LEFT JOIN calificacion cal ON cal.contratacion_id = c.id
                WHERE c.prestador_id = %s
                ORDER BY c.solicitado_en DESC
                """,
                (g.user_id,),
            )
            rows = cur.fetchall()
        return jsonify({"contrataciones": [dict(r) for r in rows]})
    except Exception as e:
        print(f"[contrataciones/recibidas] {e}")
        return jsonify({"error": "Error del servidor"}), 500
