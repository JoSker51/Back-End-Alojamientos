from flask import Blueprint, jsonify
from auth_utils import require_auth
from db import get_connection

prestadores_bp = Blueprint("prestadores", __name__)

@prestadores_bp.get("")
@require_auth("arrendador")
def listar():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT u.id, u.nombre, u.apellido, u.email, u.telefono,
                      AVG(cal.puntuacion)::numeric(10,2) AS rating_promedio,
                      COUNT(cal.id) AS rating_total
               FROM usuario u
               LEFT JOIN calificacion cal ON cal.prestador_id = u.id
               WHERE u.rol = 'prestador'
               GROUP BY u.id ORDER BY u.nombre"""
        )
        prestadores = cur.fetchall()
        resultado = []
        for p in prestadores:
            cur.execute(
                """SELECT id, fecha, franja_horaria
                   FROM disponibilidad
                   WHERE prestador_id = %s
                     AND estado = 'disponible'
                     AND fecha >= CURRENT_DATE
                   ORDER BY fecha ASC""",
                (p["id"],),
            )
            resultado.append({**dict(p), "disponibilidades": [dict(d) for d in cur.fetchall()]})
    return jsonify({"prestadores": resultado})
