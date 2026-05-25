from flask import Blueprint, g, jsonify, request
from auth_utils import require_auth
from db import get_connection

contrataciones_bp = Blueprint("contrataciones", __name__)

@contrataciones_bp.post("/<cont_id>/iniciar")
@require_auth("prestador")
def iniciar(cont_id):
    data = request.get_json(silent=True) or {}
    lat = data.get("lat")  # opcional
    lng = data.get("lng")  # opcional
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT estado, arrendador_id FROM contratacion WHERE id=%s AND prestador_id=%s",
            (cont_id, g.user_id),
        )
        cont = cur.fetchone()
        if not cont or cont["estado"] != "aceptada":
            return jsonify({"error": "No se puede iniciar"}), 409
        cur.execute(
            "UPDATE contratacion SET estado='en_progreso', iniciada_en=NOW() WHERE id=%s",
            (cont_id,),
        )
        loc_text = f" (lat:{lat}, lng:{lng})" if lat and lng else ""
        cur.execute(
            """INSERT INTO notificacion (contratacion_id, destinatario_id, mensaje)
               VALUES (%s, %s, %s)""",
            (cont_id, cont["arrendador_id"],
             f"El prestador comenzo la limpieza{loc_text}."),
        )
        conn.commit()
    return jsonify({"estado": "en_progreso", "lat": lat, "lng": lng})
