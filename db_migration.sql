-- ============================================================
-- MIGRACIÓN: Historia de usuario - Aceptar/Rechazar solicitudes
-- Ejecutar en DBeaver sobre la BD existente en AWS RDS
-- ============================================================

-- Asegurarse de que los ENUMs base existen (si ya los creaste, omite estas líneas)
DO $$ BEGIN
  CREATE TYPE estado_contratacion AS ENUM ('pendiente', 'aceptada', 'rechazada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE estado_disponibilidad AS ENUM ('disponible', 'reservada');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Índices para mejorar rendimiento en las consultas de notificaciones
CREATE INDEX IF NOT EXISTS idx_notificacion_destinatario
  ON notificacion(destinatario_id);

CREATE INDEX IF NOT EXISTS idx_notificacion_leida
  ON notificacion(destinatario_id, leida);

CREATE INDEX IF NOT EXISTS idx_contratacion_prestador
  ON contratacion(prestador_id, estado);

CREATE INDEX IF NOT EXISTS idx_contratacion_arrendador
  ON contratacion(arrendador_id);

-- Vista útil para que el frontend cargue notificaciones con detalle
CREATE OR REPLACE VIEW vista_notificaciones AS
SELECT
  n.id                  AS notificacion_id,
  n.mensaje,
  n.leida,
  n.creado_en,
  n.destinatario_id,
  c.id                  AS contratacion_id,
  c.estado              AS estado_contratacion,
  c.solicitado_en,
  ua.nombre || ' ' || ua.apellido AS nombre_arrendador,
  ua.email              AS email_arrendador,
  d.fecha               AS fecha_servicio,
  d.franja_horaria
FROM notificacion n
JOIN contratacion c   ON c.id = n.contratacion_id
JOIN usuario ua       ON ua.id = c.arrendador_id
JOIN disponibilidad d ON d.id = c.disponibilidad_id;
