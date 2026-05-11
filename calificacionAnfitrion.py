from flask import Blueprint, g, jsonify
from auth_utils import require_auth
from db import get_connection

prestadores_bp = Blueprint("prestadores", __name__)

@prestadores_bp.get("/mi-rating")
@require_auth("prestador")
def mi_rating():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT cal.puntuacion, cal.comentario, cal.creado_en,
                      (u.nombre || ' ' || u.apellido) AS arrendador_nombre
               FROM calificacion cal
               JOIN usuario u ON u.id = cal.arrendador_id
               WHERE cal.prestador_id = %s
               ORDER BY cal.creado_en DESC""",
            (g.user_id,),
        )
        return jsonify({"comentarios": [dict(c) for c in cur.fetchall()]})
