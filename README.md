# 🧹 CleanStay — Backend API + Frontend Arrendador

Servicio de conexión entre arrendadores de Airbnb y prestadores de servicios de limpieza.

## 📁 Estructura del proyecto

```
cleanstay/
├── server.js          ← API Express + rutas
├── index.html         ← Frontend del ARRENDADOR (React embebido)
├── package.json
├── .env.example       ← Copia esto como .env y llena tus datos
└── README.md
```

---

## ⚙️ Configuración inicial (todos los miembros del equipo)

### 1. Clonar el repo
```bash
git clone https://github.com/TU_USUARIO/cleanstay.git
cd cleanstay
```

### 2. Instalar dependencias
```bash
npm install
```

### 3. Crear el archivo `.env`
```bash
cp .env.example .env
```
Luego edita `.env` con las credenciales reales de la BD (el dueño de AWS las comparte por privado, **nunca en el repo**).

### 4. Arrancar el servidor
```bash
npm run dev     # desarrollo con hot-reload
npm start       # producción
```

El servidor corre en `http://localhost:3001`

---

## 🗄️ Base de datos — esquema completo

El esquema está en AWS RDS (PostgreSQL). Para ejecutarlo por primera vez:

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE rol_usuario AS ENUM ('arrendador', 'prestador');
CREATE TYPE estado_disponibilidad AS ENUM ('disponible', 'reservada');
CREATE TYPE estado_contratacion AS ENUM ('pendiente', 'aceptada', 'rechazada');

CREATE TABLE usuario (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre        VARCHAR(100) NOT NULL,
  apellido      VARCHAR(100) NOT NULL,
  email         VARCHAR(255) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  rol           rol_usuario NOT NULL,
  creado_en     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE disponibilidad (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prestador_id   UUID NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
  fecha          DATE NOT NULL,
  franja_horaria VARCHAR(50) NOT NULL,
  estado         estado_disponibilidad DEFAULT 'disponible',
  creado_en      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE contratacion (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  arrendador_id       UUID NOT NULL REFERENCES usuario(id),
  prestador_id        UUID NOT NULL REFERENCES usuario(id),
  disponibilidad_id   UUID NOT NULL REFERENCES disponibilidad(id),
  solicitado_en       TIMESTAMP DEFAULT NOW(),
  estado              estado_contratacion DEFAULT 'pendiente',
  respondido_en       TIMESTAMP
);

CREATE TABLE notificacion (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  contratacion_id  UUID NOT NULL REFERENCES contratacion(id) ON DELETE CASCADE,
  destinatario_id  UUID NOT NULL REFERENCES usuario(id),
  mensaje          TEXT NOT NULL,
  leida            BOOLEAN DEFAULT FALSE,
  creado_en        TIMESTAMP DEFAULT NOW()
);
```

---

## 📡 Endpoints de la API

### Autenticación
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/register` | Registrar usuario (arrendador o prestador) |
| POST | `/api/auth/login` | Login → devuelve JWT |

**Body register:**
```json
{
  "nombre": "Juan",
  "apellido": "Pérez",
  "email": "juan@email.com",
  "password": "secreto123",
  "rol": "arrendador"
}
```

**Body login:**
```json
{ "email": "juan@email.com", "password": "secreto123" }
```
**Response login:**
```json
{
  "token": "eyJ...",
  "user": { "id": "uuid", "nombre": "Juan", "rol": "arrendador", ... }
}
```

---

### Prestadores (requiere JWT de arrendador)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/prestadores` | Lista prestadores con disponibilidades |
| GET | `/api/prestadores?q=maria` | Filtra por nombre |
| GET | `/api/prestadores?franja=mañana` | Filtra por franja horaria |

**Cabecera requerida:**
```
Authorization: Bearer <token>
```

---

### Contrataciones (requiere JWT de arrendador)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/contrataciones` | Crear solicitud de limpieza |
| GET | `/api/contrataciones/mis-contrataciones` | Ver mis solicitudes |

**Body POST:**
```json
{
  "prestador_id": "uuid-del-prestador",
  "disponibilidad_id": "uuid-de-la-disponibilidad"
}
```

---

### Notificaciones (requiere JWT)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/notificaciones` | Ver notificaciones del usuario |
| GET | `/api/notificaciones/unread-count` | Cantidad no leídas |
| PATCH | `/api/notificaciones/:id/leer` | Marcar como leída |

---

### Dashboard
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/dashboard/stats` | Estadísticas del arrendador |

---

## 🤝 Partes del proyecto por equipo

| Módulo | Descripción | Endpoints necesarios |
|--------|-------------|----------------------|
| ✅ **Arrendador** (este repo) | Login, buscar prestadores, contratar | Todos los de arriba |
| 🔲 **Prestador** | Login, publicar disponibilidades, aceptar/rechazar | `POST /api/disponibilidades`, `PATCH /api/contrataciones/:id/responder` |
| 🔲 **Perfiles** | Ver perfil propio y ajeno, fotos | `GET/PUT /api/usuarios/:id/perfil` |
| 🔲 **Calificaciones** | Calificar después del servicio | `POST /api/calificaciones` |

### Endpoints que el equipo del PRESTADOR debe agregar a `server.js`:

```js
// POST /api/disponibilidades — prestador publica su disponibilidad
// Body: { fecha, franja_horaria }

// PATCH /api/contrataciones/:id/responder — aceptar o rechazar
// Body: { respuesta: 'aceptada' | 'rechazada' }
// Debe: actualizar estado, guardar respondido_en, crear notif para arrendador
```

---

## 🚀 Subir a GitHub (primera vez)

```bash
# Desde la carpeta del proyecto
git init
git add .
git commit -m "feat: backend API + frontend arrendador"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/cleanstay.git
git push -u origin main
```

**⚠️ MUY IMPORTANTE:** El archivo `.env` está en `.gitignore`. Nunca lo subas al repo. Comparte las credenciales de la BD por mensaje privado con tu equipo.

Agrega esto a tu `.gitignore`:
```
node_modules/
.env
```

---

## 🧪 Probar la API rápido (con curl)

```bash
# Registrar arrendador
curl -X POST http://localhost:3001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Juan","apellido":"Perez","email":"juan@test.com","password":"123456","rol":"arrendador"}'

# Login
curl -X POST http://localhost:3001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"juan@test.com","password":"123456"}'

# Ver prestadores (usa el token del login)
curl http://localhost:3001/api/prestadores \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

---

## 👥 Equipo

- Módulo arrendador: [tu nombre]
- Módulo prestador: [compañero 2]
- Módulo perfiles: [compañero 3]
