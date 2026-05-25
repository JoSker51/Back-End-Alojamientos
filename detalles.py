from flask import Blueprint, g, jsonify
from auth_utils import require_auth
from db import get_connection

contrataciones_bp = Blueprint("contrataciones", __name__)

@contrataciones_bp.get("/<cont_id>/archivos")
@require_auth()
def archivos(cont_id):
    with get_connection() as conn, conn.cursor() as cur:
        # Verificar que el usuario es parte de la contratacion
        cur.execute(
            """SELECT 1 FROM contratacion
               WHERE id=%s AND (arrendador_id=%s OR prestador_id=%s)""",
            (cont_id, g.user_id, g.user_id),
        )
        if not cur.fetchone():
            return jsonify({"error": "No autorizado"}), 404

        # Archivos del trabajo + foto_residencia del arrendador
        cur.execute(
            """(SELECT id, tipo, nombre_original, mime_type, tamano_bytes, creado_en
                FROM archivo WHERE contratacion_id = %s)
               UNION
               (SELECT a.id, a.tipo, a.nombre_original, a.mime_type, a.tamano_bytes, a.creado_en
                FROM archivo a
                JOIN contratacion c ON c.arrendador_id = a.usuario_id
                WHERE c.id = %s AND a.tipo = 'foto_residencia')
               ORDER BY creado_en ASC""",
            (cont_id, cont_id),
        )
        rows = cur.fetchall()
    return jsonify({"archivos": [dict(r) for r in rows]})
