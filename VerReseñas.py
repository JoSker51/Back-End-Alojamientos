# Fragmento de routes/contrataciones.py + routes/prestadores.py
from flask import Blueprint, g, jsonify, request
from auth_utils import require_auth
from db import get_connection

contrataciones_bp = Blueprint("contrataciones", __name__)
prestadores_bp    = Blueprint("prestadores",    __name__)


# --- Calificar (arrendador) ------------------------------------
@contrataciones_bp.post("/<cont_id>/calificar")
@require_auth("arrendador")
def calificar(cont_id):
    data = request.get_json(silent=True) or {}
    try:
        puntuacion = int(data.get("puntuacion"))
    except (TypeError, ValueError):
        return jsonify({"error": "puntuacion debe ser entero 1-5"}), 400
    if puntuacion < 1 or puntuacion > 5:
        return jsonify({"error": "puntuacion debe estar entre 1 y 5"}), 400
    comentario = (data.get("comentario") or "").strip() or None

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT estado, prestador_id FROM contratacion
               WHERE id = %s AND arrendador_id = %s""",
            (cont_id, g.user_id),
        )
        cont = cur.fetchone()
        if not cont or cont["estado"] != "finalizada":
            return jsonify({"error": "Solo se califica trabajo finalizado"}), 409

        cur.execute(
            """INSERT INTO calificacion
                  (contratacion_id, arrendador_id, prestador_id, puntuacion, comentario)
               VALUES (%s, %s, %s, %s, %s)""",
            (cont_id, g.user_id, cont["prestador_id"], puntuacion, comentario),
        )
        cur.execute("UPDATE contratacion SET estado = 'calificada' WHERE id = %s", (cont_id,))
        conn.commit()

    return jsonify({"mensaje": "Calificacion guardada", "puntuacion": puntuacion})


# --- Mi rating (prestador ve su reputacion) --------------------
@prestadores_bp.get("/mi-rating")
@require_auth("prestador")
def mi_rating():
    with get_connection() as conn, conn.cursor() as cur:
        # Promedio + distribucion
        cur.execute(
            """SELECT AVG(puntuacion)::numeric(10,2) AS promedio,
                      COUNT(*) AS total,
                      COUNT(*) FILTER (WHERE puntuacion = 5) AS cinco,
                      COUNT(*) FILTER (WHERE puntuacion = 4) AS cuatro,
                      COUNT(*) FILTER (WHERE puntuacion = 3) AS tres,
                      COUNT(*) FILTER (WHERE puntuacion = 2) AS dos,
                      COUNT(*) FILTER (WHERE puntuacion = 1) AS uno
               FROM calificacion WHERE prestador_id = %s""",
            (g.user_id,),
        )
        stats = cur.fetchone()

        # Comentarios mas recientes
        cur.execute(
            """SELECT cal.id, cal.puntuacion, cal.comentario, cal.creado_en,
                      (u.nombre || ' ' || u.apellido) AS arrendador_nombre
               FROM calificacion cal
               JOIN usuario u ON u.id = cal.arrendador_id
               WHERE cal.prestador_id = %s
               ORDER BY cal.creado_en DESC LIMIT 50""",
            (g.user_id,),
        )
        comentarios = cur.fetchall()

    return jsonify({
        "promedio": float(stats["promedio"]) if stats["promedio"] else None,
        "total":    int(stats["total"] or 0),
        "distribucion": {str(k): int(stats[v] or 0)
                         for k, v in [(5,"cinco"),(4,"cuatro"),(3,"tres"),(2,"dos"),(1,"uno")]},
        "comentarios": [dict(c) for c in comentarios],
    })
