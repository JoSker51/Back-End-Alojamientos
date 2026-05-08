from flask import Blueprint, g, jsonify
from auth_utils import require_auth
from db import get_connection

prestadores_bp = Blueprint("prestadores", __name__)

@prestadores_bp.get("/mi-rating")
@require_auth("prestador")
def mi_rating():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT AVG(puntuacion)::numeric(10,2) AS promedio,
                      COUNT(*) AS total,
                      COUNT(*) FILTER (WHERE puntuacion=5) AS cinco,
                      COUNT(*) FILTER (WHERE puntuacion=4) AS cuatro,
                      COUNT(*) FILTER (WHERE puntuacion=3) AS tres,
                      COUNT(*) FILTER (WHERE puntuacion=2) AS dos,
                      COUNT(*) FILTER (WHERE puntuacion=1) AS uno
               FROM calificacion WHERE prestador_id = %s""",
            (g.user_id,),
        )
        s = cur.fetchone()
        cur.execute(
            """SELECT cal.puntuacion, cal.comentario, cal.creado_en,
                      (u.nombre || ' ' || u.apellido) AS arrendador_nombre
               FROM calificacion cal JOIN usuario u ON u.id = cal.arrendador_id
               WHERE cal.prestador_id = %s
               ORDER BY cal.creado_en DESC LIMIT 50""",
            (g.user_id,),
        )
        comentarios = cur.fetchall()
    return jsonify({
        "promedio": float(s["promedio"]) if s["promedio"] else None,
        "total": int(s["total"] or 0),
        "distribucion": {"5":int(s["cinco"]or 0),"4":int(s["cuatro"]or 0),
                         "3":int(s["tres"]or 0),"2":int(s["dos"]or 0),"1":int(s["uno"]or 0)},
        "comentarios": [dict(c) for c in comentarios],
    })
