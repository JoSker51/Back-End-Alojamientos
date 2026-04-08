// ═══════════════════════════════════════════════════════════════
//  CleanStay — Backend API
//  Stack: Node.js + Express + PostgreSQL (AWS RDS)
//  Rutas que consume el frontend del arrendador
// ═══════════════════════════════════════════════════════════════

const express    = require('express');
const { Pool }   = require('pg');
const bcrypt     = require('bcryptjs');
const jwt        = require('jsonwebtoken');
const cors       = require('cors');
require('dotenv').config();

const app = express();
app.use(express.json());
app.use(cors({ origin: process.env.FRONTEND_URL || '*' }));

// ─── Conexión PostgreSQL (AWS RDS) ──────────────────────────────
const pool = new Pool({
  host:     process.env.DB_HOST,      // ej: mydb.xxxxxx.us-east-1.rds.amazonaws.com
  port:     parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME,      // nombre de tu base de datos
  user:     process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  ssl:      { rejectUnauthorized: false }, // requerido por AWS RDS
});

pool.connect()
  .then(() => console.log('✅  Conectado a PostgreSQL en AWS'))
  .catch(e  => console.error('❌  Error BD completo:', e));

// ─── Middleware de autenticación JWT ────────────────────────────
function auth(req, res, next) {
  const header = req.headers['authorization'];
  if (!header) return res.status(401).json({ message: 'No autorizado' });
  const token = header.replace('Bearer ', '');
  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET);
    next();
  } catch {
    return res.status(401).json({ message: 'Token inválido o expirado' });
  }
}

// Solo arrendadores pueden usar estas rutas
function soloArrendador(req, res, next) {
  if (req.user.rol !== 'arrendador') return res.status(403).json({ message: 'Solo arrendadores' });
  next();
}

// ═══════════════════════════════════════════════════════════════
//  AUTH
// ═══════════════════════════════════════════════════════════════

// POST /api/auth/register
app.post('/api/auth/register', async (req, res) => {
  const { nombre, apellido, email, password, rol } = req.body;
  if (!nombre || !apellido || !email || !password || !rol) {
    return res.status(400).json({ message: 'Faltan campos requeridos' });
  }
  if (!['arrendador', 'prestador'].includes(rol)) {
    return res.status(400).json({ message: 'Rol inválido' });
  }
  try {
    const existe = await pool.query('SELECT id FROM usuario WHERE email = $1', [email]);
    if (existe.rows.length > 0) return res.status(409).json({ message: 'Email ya registrado' });

    const hash = await bcrypt.hash(password, 12);
    const { rows } = await pool.query(
      `INSERT INTO usuario (nombre, apellido, email, password_hash, rol)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id, nombre, apellido, email, rol, creado_en`,
      [nombre, apellido, email, hash, rol]
    );
    res.status(201).json({ user: rows[0] });
  } catch (e) {
    console.error(e);
    res.status(500).json({ message: 'Error del servidor' });
  }
});

// POST /api/auth/login
app.post('/api/auth/login', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) return res.status(400).json({ message: 'Email y contraseña requeridos' });
  try {
    const { rows } = await pool.query(
      'SELECT id, nombre, apellido, email, password_hash, rol FROM usuario WHERE email = $1',
      [email]
    );
    if (rows.length === 0) return res.status(401).json({ message: 'Credenciales incorrectas' });
    const user = rows[0];
    const ok = await bcrypt.compare(password, user.password_hash);
    if (!ok) return res.status(401).json({ message: 'Credenciales incorrectas' });

    const token = jwt.sign(
      { id: user.id, email: user.email, rol: user.rol },
      process.env.JWT_SECRET,
      { expiresIn: '7d' }
    );
    const { password_hash, ...userSafe } = user;
    res.json({ token, user: userSafe });
  } catch (e) {
    console.error(e);
    res.status(500).json({ message: 'Error del servidor' });
  }
});

// ═══════════════════════════════════════════════════════════════
//  PRESTADORES — visibles para arrendadores
// ═══════════════════════════════════════════════════════════════

// GET /api/prestadores?q=nombre&franja=mañana
app.get('/api/prestadores', auth, soloArrendador, async (req, res) => {
  const { q, franja } = req.query;
  try {
    let query = `
      SELECT
        u.id, u.nombre, u.apellido, u.email,
        COALESCE(
          json_agg(
            json_build_object(
              'id',             d.id,
              'fecha',          d.fecha,
              'franja_horaria', d.franja_horaria,
              'estado',         d.estado
            ) ORDER BY d.fecha
          ) FILTER (WHERE d.id IS NOT NULL AND d.estado = 'disponible'),
          '[]'
        ) AS disponibilidades
      FROM usuario u
      LEFT JOIN disponibilidad d ON d.prestador_id = u.id AND d.estado = 'disponible'
      WHERE u.rol = 'prestador'
    `;
    const params = [];
    if (q) {
      params.push(`%${q}%`);
      query += ` AND (u.nombre ILIKE $${params.length} OR u.apellido ILIKE $${params.length})`;
    }
    if (franja) {
      params.push(franja);
      query += ` AND d.franja_horaria = $${params.length}`;
    }
    query += ' GROUP BY u.id ORDER BY u.nombre';

    const { rows } = await pool.query(query, params);
    res.json(rows);
  } catch (e) {
    console.error(e);
    res.status(500).json({ message: 'Error del servidor' });
  }
});

// ═══════════════════════════════════════════════════════════════
//  CONTRATACIONES
// ═══════════════════════════════════════════════════════════════

// POST /api/contrataciones  — arrendador crea una solicitud
app.post('/api/contrataciones', auth, soloArrendador, async (req, res) => {
  const { prestador_id, disponibilidad_id } = req.body;
  if (!prestador_id || !disponibilidad_id) {
    return res.status(400).json({ message: 'Faltan campos' });
  }
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // Verificar que la disponibilidad pertenezca al prestador y esté libre
    const disp = await client.query(
      `SELECT id, fecha, franja_horaria FROM disponibilidad
       WHERE id = $1 AND prestador_id = $2 AND estado = 'disponible'`,
      [disponibilidad_id, prestador_id]
    );
    if (disp.rows.length === 0) {
      await client.query('ROLLBACK');
      return res.status(409).json({ message: 'Disponibilidad no existe o ya fue reservada' });
    }

    // Crear la contratación
    const { rows: [contratacion] } = await client.query(
      `INSERT INTO contratacion (arrendador_id, prestador_id, disponibilidad_id)
       VALUES ($1, $2, $3)
       RETURNING id`,
      [req.user.id, prestador_id, disponibilidad_id]
    );

    // Marcar disponibilidad como reservada
    await client.query(
      `UPDATE disponibilidad SET estado = 'reservada' WHERE id = $1`,
      [disponibilidad_id]
    );

    // Obtener datos para la notificación
    const arrendador = await client.query(
      'SELECT nombre, apellido FROM usuario WHERE id = $1',
      [req.user.id]
    );
    const { nombre, apellido } = arrendador.rows[0];
    const { fecha, franja_horaria } = disp.rows[0];

    const mensaje = `${nombre} ${apellido} te ha solicitado limpiar el ${new Date(fecha+'T00:00:00').toLocaleDateString('es-CO', { day: 'numeric', month: 'long' })} (${franja_horaria})`;

    // Crear notificación para el prestador
    await client.query(
      `INSERT INTO notificacion (contratacion_id, destinatario_id, mensaje)
       VALUES ($1, $2, $3)`,
      [contratacion.id, prestador_id, mensaje]
    );

    await client.query('COMMIT');
    res.status(201).json({ id: contratacion.id, message: 'Solicitud enviada exitosamente' });
  } catch (e) {
    await client.query('ROLLBACK');
    console.error(e);
    res.status(500).json({ message: 'Error del servidor' });
  } finally {
    client.release();
  }
});

// GET /api/contrataciones/mis-contrataciones
app.get('/api/contrataciones/mis-contrataciones', auth, soloArrendador, async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT
         c.id, c.estado, c.solicitado_en, c.respondido_en,
         p.nombre AS prestador_nombre, p.apellido AS prestador_apellido,
         d.fecha, d.franja_horaria
       FROM contratacion c
       JOIN usuario p ON p.id = c.prestador_id
       JOIN disponibilidad d ON d.id = c.disponibilidad_id
       WHERE c.arrendador_id = $1
       ORDER BY c.solicitado_en DESC`,
      [req.user.id]
    );
    res.json(rows);
  } catch (e) {
    console.error(e);
    res.status(500).json({ message: 'Error del servidor' });
  }
});

// ═══════════════════════════════════════════════════════════════
//  NOTIFICACIONES (arrendador)
// ═══════════════════════════════════════════════════════════════

// GET /api/notificaciones
app.get('/api/notificaciones', auth, async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT id, mensaje, leida, creado_en
       FROM notificacion
       WHERE destinatario_id = $1
       ORDER BY creado_en DESC`,
      [req.user.id]
    );
    res.json(rows);
  } catch (e) {
    res.status(500).json({ message: 'Error del servidor' });
  }
});

// GET /api/notificaciones/unread-count
app.get('/api/notificaciones/unread-count', auth, async (req, res) => {
  try {
    const { rows } = await pool.query(
      'SELECT COUNT(*) AS count FROM notificacion WHERE destinatario_id = $1 AND leida = false',
      [req.user.id]
    );
    res.json({ count: parseInt(rows[0].count) });
  } catch (e) {
    res.status(500).json({ message: 'Error del servidor' });
  }
});

// PATCH /api/notificaciones/:id/leer
app.patch('/api/notificaciones/:id/leer', auth, async (req, res) => {
  try {
    await pool.query(
      'UPDATE notificacion SET leida = true WHERE id = $1 AND destinatario_id = $2',
      [req.params.id, req.user.id]
    );
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ message: 'Error del servidor' });
  }
});

// ═══════════════════════════════════════════════════════════════
//  DASHBOARD STATS
// ═══════════════════════════════════════════════════════════════

app.get('/api/dashboard/stats', auth, soloArrendador, async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT
         COUNT(*)                                         AS total,
         COUNT(*) FILTER (WHERE estado = 'aceptada')     AS aceptadas,
         COUNT(*) FILTER (WHERE estado = 'pendiente')    AS pendientes,
         COUNT(*) FILTER (WHERE estado = 'rechazada')    AS rechazadas
       FROM contratacion
       WHERE arrendador_id = $1`,
      [req.user.id]
    );
    const r = rows[0];
    res.json({
      total:      parseInt(r.total),
      aceptadas:  parseInt(r.aceptadas),
      pendientes: parseInt(r.pendientes),
      rechazadas: parseInt(r.rechazadas),
    });
  } catch (e) {
    res.status(500).json({ message: 'Error del servidor' });
  }
});

// ─── Start ───────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`🚀  API corriendo en http://localhost:${PORT}`));
