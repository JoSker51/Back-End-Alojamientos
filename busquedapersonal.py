# Backend: simplemente devuelve TODOS los prestadores. La busqueda se hace en cliente.
from flask import Blueprint, jsonify
from auth_utils import require_auth
from db import get_connection

prestadores_bp = Blueprint("prestadores", __name__)

@prestadores_bp.get("")
@require_auth("arrendador")
def listar():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, nombre, apellido, email, telefono FROM usuario WHERE rol='prestador' ORDER BY nombre"
        )
        return jsonify({"prestadores": [dict(p) for p in cur.fetchall()]})
