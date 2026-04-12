

import os
import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ── Conexión a AWS RDS ──────────────────────────────────────
# Crea un archivo .env en la raíz del proyecto con esto:
#
#   DB_HOST=tu-instancia.xxxx.us-east-1.rds.amazonaws.com
#   DB_PORT=5432
#   DB_NAME=postgres
#   DB_USER=tu_usuario
#   DB_PASSWORD=tu_contraseña
#
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        cursor_factory=psycopg2.extras.RealDictCursor
    )


router = APIRouter(prefix="/api", tags=["notificaciones"])


# ── Modelos ─────────────────────────────────────────────────
class RespuestaContratacion(BaseModel):
    decision: str  # "aceptada" o "rechazada"


# ── Helper: obtener usuario desde header ───────────────────
# Por ahora se pasa el user_id en el header X-User-Id.
# Cuando integren autenticación real (JWT), reemplazar esto.
def get_user_id(x_user_id: Optional[str] = None) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Header X-User-Id requerido")
    return x_user_id


# ── GET /api/notificaciones ─────────────────────────────────
# Devuelve todas las notificaciones del prestador autenticado.
@router.get("/notificaciones")
def listar_notificaciones(x_user_id: Optional[str] = Header(None)):
    user_id = get_user_id(x_user_id)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    notificacion_id,
                    mensaje,
                    leida,
                    creado_en,
                    contratacion_id,
                    estado_contratacion,
                    solicitado_en,
                    nombre_arrendador,
                    email_arrendador,
                    fecha_servicio,
                    franja_horaria
                FROM vista_notificaciones
                WHERE destinatario_id = %s
                ORDER BY creado_en DESC
            """, (user_id,))
            notificaciones = cur.fetchall()
        return {"notificaciones": [dict(n) for n in notificaciones]}
    finally:
        conn.close()


# ── PATCH /api/notificaciones/{id}/leer ────────────────────
# Marca una notificación como leída.
@router.patch("/notificaciones/{notificacion_id}/leer")
def marcar_leida(notificacion_id: str, x_user_id: Optional[str] = Header(None)):
    user_id = get_user_id(x_user_id)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE notificacion
                SET leida = TRUE
                WHERE id = %s AND destinatario_id = %s
            """, (notificacion_id, user_id))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Notificación no encontrada")
            conn.commit()
        return {"mensaje": "Notificación marcada como leída"}
    finally:
        conn.close()


# ── POST /api/contrataciones/{id}/responder ─────────────────
# El prestador acepta o rechaza la solicitud.
# Si acepta → marca la disponibilidad como 'reservada'.
# Si rechaza → la disponibilidad queda libre.
@router.post("/contrataciones/{contratacion_id}/responder")
def responder_contratacion(
    contratacion_id: str,
    body: RespuestaContratacion,
    x_user_id: Optional[str] = Header(None)
):
    user_id = get_user_id(x_user_id)

    if body.decision not in ("aceptada", "rechazada"):
        raise HTTPException(status_code=400, detail="decision debe ser 'aceptada' o 'rechazada'")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Verificar que la contratación existe, es para este prestador y está pendiente
            cur.execute("""
                SELECT id, disponibilidad_id, estado
                FROM contratacion
                WHERE id = %s AND prestador_id = %s
            """, (contratacion_id, user_id))
            contratacion = cur.fetchone()

            if not contratacion:
                raise HTTPException(status_code=404, detail="Contratación no encontrada")
            if contratacion["estado"] != "pendiente":
                raise HTTPException(
                    status_code=409,
                    detail=f"Esta contratación ya fue {contratacion['estado']}"
                )

            # Actualizar estado de la contratación
            cur.execute("""
                UPDATE contratacion
                SET estado = %s, respondido_en = NOW()
                WHERE id = %s
            """, (body.decision, contratacion_id))

            # Si acepta, bloquear la disponibilidad
            if body.decision == "aceptada":
                cur.execute("""
                    UPDATE disponibilidad
                    SET estado = 'reservada'
                    WHERE id = %s
                """, (contratacion["disponibilidad_id"],))

            # Marcar la notificación relacionada como leída automáticamente
            cur.execute("""
                UPDATE notificacion
                SET leida = TRUE
                WHERE contratacion_id = %s AND destinatario_id = %s
            """, (contratacion_id, user_id))

            conn.commit()

        return {
            "mensaje": f"Contratación {body.decision} correctamente",
            "contratacion_id": contratacion_id,
            "estado": body.decision
        }
    finally:
        conn.close()


# ── GET /api/contrataciones/mis-solicitudes ─────────────────
# Historial de solicitudes recibidas por el prestador.
@router.get("/contrataciones/mis-solicitudes")
def mis_solicitudes(x_user_id: Optional[str] = Header(None)):
    user_id = get_user_id(x_user_id)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    c.id,
                    c.estado,
                    c.solicitado_en,
                    c.respondido_en,
                    ua.nombre || ' ' || ua.apellido AS arrendador,
                    d.fecha,
                    d.franja_horaria
                FROM contratacion c
                JOIN usuario ua       ON ua.id = c.arrendador_id
                JOIN disponibilidad d ON d.id = c.disponibilidad_id
                WHERE c.prestador_id = %s
                ORDER BY c.solicitado_en DESC
            """, (user_id,))
            solicitudes = cur.fetchall()
        return {"solicitudes": [dict(s) for s in solicitudes]}
    finally:
        conn.close()
