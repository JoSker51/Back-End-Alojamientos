# Esquema (db_migration.sql)
"""
DO $$ BEGIN
  CREATE TYPE estado_contratacion AS ENUM (
    'pendiente', 'aceptada', 'rechazada',
    'en_progreso', 'finalizada', 'calificada'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE contratacion (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  arrendador_id   UUID NOT NULL REFERENCES usuario(id),
  prestador_id    UUID NOT NULL REFERENCES usuario(id),
  estado          estado_contratacion DEFAULT 'pendiente',
  solicitado_en   TIMESTAMP DEFAULT NOW(),
  respondido_en   TIMESTAMP,
  iniciada_en     TIMESTAMP,
  finalizada_en   TIMESTAMP
);
"""

# Verificacion de transicion valida en cada endpoint:
def cambiar_estado(cur, cont_id, estado_actual, estado_nuevo):
    transiciones_validas = {
        "pendiente": {"aceptada", "rechazada"},
        "aceptada":  {"en_progreso"},
        "en_progreso": {"finalizada"},
        "finalizada":  {"calificada"},
    }
    if estado_nuevo not in transiciones_validas.get(estado_actual, set()):
        raise ValueError(f"No se puede pasar de {estado_actual} a {estado_nuevo}")
    cur.execute("UPDATE contratacion SET estado=%s WHERE id=%s",
                (estado_nuevo, cont_id))
