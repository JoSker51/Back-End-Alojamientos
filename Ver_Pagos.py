# Endpoint personalizado para listar trabajos finalizados con datos de pago
from flask import Blueprint, g, jsonify
from auth_utils import require_auth
from db import get_connection

prestadores_bp = Blueprint("prestadores", __name__)

@prestadores_bp.get("/mis-pagos")
@require_auth("prestador")
def mis_pagos():
    with get_connection() as conn, conn.cursor() as cur:
        # Datos de pago del prestador
        cur.execute(
            "SELECT metodo_pago, datos_pago FROM perfil_prestador WHERE usuario_id = %s",
            (g.user_id,),
        )
        perfil = cur.fetchone() or {}

        # Trabajos finalizados o calificados
        cur.execute(
            """SELECT c.id, c.estado, c.iniciada_en, c.finalizada_en,
                      d.fecha, d.franja_horaria,
                      (u.nombre || ' ' || u.apellido) AS arrendador
               FROM contratacion c
               JOIN disponibilidad d ON d.id = c.disponibilidad_id
               JOIN usuario u        ON u.id = c.arrendador_id
               WHERE c.prestador_id = %s
                 AND c.estado IN ('finalizada','calificada')
               ORDER BY c.finalizada_en DESC""",
            (g.user_id,),
        )
        trabajos = cur.fetchall()
    return jsonify({
        "metodo_pago": perfil.get("metodo_pago"),
        "datos_pago":  perfil.get("datos_pago"),
        "trabajos_pagables": [dict(t) for t in trabajos],
    })
