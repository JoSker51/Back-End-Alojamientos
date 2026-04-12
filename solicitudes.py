from flask import Blueprint, request, jsonify
import uuid

solicitudes_bp = Blueprint('solicitudes', __name__)

# Simulación de base de datos
solicitudes = []

# Crear solicitud
@solicitudes_bp.route('/solicitudes', methods=['POST'])
def crear_solicitud():
    data = request.get_json()

    # Validación básica
    campos_requeridos = ['usuario_id', 'servicio', 'ciudad', 'duracion']
    for campo in campos_requeridos:
        if campo not in data:
            return jsonify({"error": f"Falta el campo: {campo}"}), 400

    solicitud = {
        "id": str(uuid.uuid4()),
        "usuario_id": data.get('usuario_id'),
        "servicio": data.get('servicio'),
        "ciudad": data.get('ciudad'),
        "duracion": data.get('duracion'),
        "detalles": data.get('detalles', ""),
        "estado": "pendiente",
        "aplicantes": []
    }

    solicitudes.append(solicitud)

    return jsonify({
        "mensaje": "Solicitud creada correctamente",
        "data": solicitud
    }), 201


# Obtener solicitudes (filtradas por ciudad)
@solicitudes_bp.route('/solicitudes', methods=['GET'])
def obtener_solicitudes():
    ciudad = request.args.get('ciudad')

    if ciudad:
        filtradas = [s for s in solicitudes if s['ciudad'].lower() == ciudad.lower()]
        return jsonify(filtradas)

    return jsonify(solicitudes)


# Obtener una solicitud por ID
@solicitudes_bp.route('/solicitudes/<id>', methods=['GET'])
def obtener_solicitud_por_id(id):
    for s in solicitudes:
        if s['id'] == id:
            return jsonify(s)

    return jsonify({"error": "Solicitud no encontrada"}), 404