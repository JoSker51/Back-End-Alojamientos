from flask import Blueprint, g, jsonify, request
from auth_utils import require_auth
from db import get_connection

contrataciones_bp = Blueprint("contrataciones", __name__)
notificaciones_bp = Blueprint("notificaciones", __name__)


@contrataciones_bp.post("/<cont_id>/responder")
@require_auth("prestador")
def responder(cont_id):
    decision = (request.get_json().get("decision") or "").lower()
    if decision not in ("aceptada", "rechazada"):
        return jsonify({"error": "decision invalida"}), 400
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT c.estado, c.arrendador_id, d.fecha, d.franja_horaria
               FROM contratacion c JOIN disponibilidad d ON d.id=c.disponibilidad_id
               WHERE c.id=%s AND c.prestador_id=%s""",
            (cont_id, g.user_id),
        )
        cont = cur.fetchone()
        cur.execute("UPDATE contratacion SET estado=%s, respondido_en=NOW() WHERE id=%s",
                    (decision, cont_id))
        cur.execute("SELECT nombre, apellido FROM usuario WHERE id=%s", (g.user_id,))
        prest = cur.fetchone()
        verbo = "acepto" if decision == "aceptada" else "rechazo"
        # Notifica al arrendador del veredicto
        cur.execute(
            """INSERT INTO notificacion (contratacion_id, destinatario_id, mensaje)
               VALUES (%s, %s, %s)""",
            (cont_id, cont["arrendador_id"],
             f"{prest['nombre']} {prest['apellido']} {verbo} tu solicitud "
             f"para el {cont['fecha'].isoformat()} ({cont['franja_horaria']}).")
        )
        conn.commit()
    return jsonify({"estado": decision})


@notificaciones_bp.get("")
@require_auth()
def listar():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id, mensaje, leida, creado_en FROM notificacion
               WHERE destinatario_id = %s ORDER BY creado_en DESC""",
            (g.user_id,),
        )
        return jsonify({"notificaciones": [dict(r) for r in cur.fetchall()]})
