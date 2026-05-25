from flask import Flask, request, render_template
import os

app = Flask(__name__, template_folder='TEMPLATES')

empleados = []

UPLOAD_FOLDER = 'archivos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET'])
def index():
    return render_template('registrar_empleado.html')

@app.route('/registro', methods=['GET', 'POST'])
def registrar():
    if request.method == 'GET':
        return render_template('registrar_empleado.html')

    # Datos personales
    nombre              = request.form['nombre']
    tipo_identificacion = request.form['tipo_identificacion']
    numero_identificacion = request.form['numero_identificacion']
    fecha_nacimiento    = request.form['fecha_nacimiento']
    edad                = request.form['edad']
    genero              = request.form['genero']

    # Contacto
    telefono   = request.form['telefono']
    correo     = request.form['correo']
    direccion  = request.form['direccion']
    ciudad     = request.form['ciudad']

    # Cuenta de pago
    medio_pago         = request.form['medio_pago']
    banco              = request.form.get('banco', '')
    numero_cuenta      = request.form.get('numero_cuenta', '')
    titular_cuenta     = request.form.get('titular_cuenta', '')
    numero_billetera   = request.form.get('numero_billetera', '')
    descripcion_pago   = request.form.get('descripcion_pago', '')

    # Hoja de vida
    archivo = request.files['archivo']

    if archivo and archivo.filename.endswith('.txt'):
        ruta = os.path.join(UPLOAD_FOLDER, archivo.filename)
        archivo.save(ruta)
    else:
        return render_template('registrar_empleado.html',
                               error="Solo se permiten archivos en formato .txt para la hoja de vida.")

    empleado = {
        "nombre": nombre,
        "tipo_identificacion": tipo_identificacion,
        "numero_identificacion": numero_identificacion,
        "fecha_nacimiento": fecha_nacimiento,
        "edad": edad,
        "genero": genero,
        "telefono": telefono,
        "correo": correo,
        "direccion": direccion,
        "ciudad": ciudad,
        "medio_pago": medio_pago,
        "banco": banco,
        "numero_cuenta": numero_cuenta,
        "titular_cuenta": titular_cuenta,
        "numero_billetera": numero_billetera,
        "descripcion_pago": descripcion_pago,
        "hoja_de_vida": ruta
    }

    empleados.append(empleado)

    return render_template('registrar_empleado.html',
                           mensaje=f"Empleado '{nombre}' registrado exitosamente.")

if __name__ == '__main__':
    app.run(debug=True)
