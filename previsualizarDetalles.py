# El backend devuelve los archivos del trabajo + las fotos de la residencia del arrendador.
# Ya disponible desde el momento en que la contratacion existe (estado=pendiente).
from flask import Blueprint, g, jsonify
from auth_utils import require_auth
from db import get_connection

contrataciones_bp = Blueprint("contrataciones", __name__)

@contrataciones_bp.get("/<cont_id>/archivos")
@require_auth()
def archivos_pre_aceptar(cont_id):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT 1 FROM contratacion
               WHERE id=%s AND (arrendador_id=%s OR prestador_id=%s)""",
            (cont_id, g.user_id, g.user_id),
        )
        if not cur.fetchone():
            return jsonify({"error": "No autorizado"}), 404
        cur.execute(
            """SELECT a.id, a.tipo, a.nombre_original, a.mime_type, a.tamano_bytes, a.creado_en
               FROM archivo a
               JOIN contratacion c ON c.arrendador_id = a.usuario_id
               WHERE c.id = %s AND a.tipo = 'foto_residencia'
               ORDER BY a.creado_en""",
            (cont_id,),
        )
        return jsonify({"archivos": [dict(r) for r in cur.fetchall()]})
