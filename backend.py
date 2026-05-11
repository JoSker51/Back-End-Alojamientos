from flask import Blueprint, g, jsonify
from auth_utils import require_auth
from db import get_connection

contrataciones_bp = Blueprint("contrataciones", __name__)

@contrataciones_bp.get("/recibidas")
@require_auth("prestador")
def recibidas():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT c.id, c.estado, c.solicitado_en, c.respondido_en,
                      c.iniciada_en, c.finalizada_en,
                      d.fecha, d.franja_horaria,
                      (u.nombre || ' ' || u.apellido) AS contraparte_nombre,
                      u.email AS contraparte_email, u.telefono AS contraparte_telefono
               FROM contratacion c
               JOIN disponibilidad d ON d.id = c.disponibilidad_id
               JOIN usuario u        ON u.id = c.arrendador_id
               WHERE c.prestador_id = %s
               ORDER BY c.solicitado_en DESC""",
            (g.user_id,),
        )
        rows = cur.fetchall()
    return jsonify({"contrataciones": [dict(r) for r in rows]})
