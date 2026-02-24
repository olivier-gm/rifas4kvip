from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from crud import (
    get_data0, get_data02, obtener_datos_historial,
    obtener_comprador_por_cedula2,
    get_enunciado2,  get_porcentaje2,
    get_premio2, obtener_comprador_por_cedula,
    get_tickets, get_tickets2, get_porcentaje, tickets_disponibles,
    reintegrar_tickets, reintegrar_tickets2, get_data, get_data2,
    actualizar_partida, obtener_datos_partida, get_enunciado, get_premio,
    insertar_comprador, insertar_comprador2, get_estatus, get_estatus2,
    get_precio, get_precio2, vendidos, vendidos2, get_minima, get_minima2,
    get_dolar, get_dolar2, get_zelle, get_zelle2
)
import os
from werkzeug.utils import secure_filename
from functools import wraps
import sqlite3
from datetime import datetime
import random
import string
import time
import json
import shutil
from pathlib import Path
from flask import current_app
from io import BytesIO

try:
    from PIL import Image, UnidentifiedImageError
except Exception:
    Image = None
    UnidentifiedImageError = Exception


def generar_sufijo_aleatorio(length=6):
    # Genera un sufijo aleatorio de letras y números
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choices(caracteres, k=length))

# Decorador para proteger las rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):  # Verifica si el usuario está autenticado
            return redirect(url_for('admin_index'))  # Redirige al login si no está autenticado
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
UPLOAD_FOLDER = 'static/comprobantes'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'supersecretkey'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def compress_and_save(file_storage, dest_path, max_width=1200, quality=70):
    """
    Read a Werkzeug FileStorage, compress/resize using Pillow if available,
    and write to dest_path as JPEG. If Pillow is not available or fails, falls back
    to saving the original bytes.
    """
    try:
        file_bytes = file_storage.read()
        if Image is not None:
            img = Image.open(BytesIO(file_bytes))
            img = img.convert('RGB')
            if img.width > max_width:
                new_height = int(max_width * img.height / img.width)
                img = img.resize((max_width, new_height), Image.LANCZOS)
            # Ensure parent dir exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            img.save(dest_path, format='JPEG', quality=quality, optimize=True)
            return True
        else:
            # Pillow not available - write original bytes
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, 'wb') as f:
                f.write(file_bytes)
            return True
    except Exception:
        try:
            # fallback: try to save using file_storage.save
            file_storage.stream.seek(0)
        except Exception:
            pass
        try:
            file_storage.save(dest_path)
            return True
        except Exception:
            return False

@app.route('/', methods=["GET"])
def index():
    flags = obtener_datos_historial()  # solo lee en GET
    return render_template(
        'index.html', solicitudes = get_data2(), solicitudes2  = get_data02(),
        enunciado=get_enunciado(), enunciado2=get_enunciado2(),
        premio=get_premio(), premio2=get_premio2(),
        porcentaje=get_porcentaje(True), porcentaje2=get_porcentaje2(True),
        disponibilidad=get_porcentaje(False), disponibilidad2=get_porcentaje2(False),
        mostrar_rifa2=bool(flags['mostrar_rifa2']),
        mostrar_rifa3=bool(flags['mostrar_rifa3'])
    )
@app.route("/compra", methods=["POST", "GET"])
def pago():
    estatus = get_estatus()
    if estatus == "Venta finalizada":
        return redirect(url_for('index'))  # redirigir a un panel de administración
    # Si no es POST, solo se muestran los datos vacíos
    return render_template("comprar.html", cant_min=get_minima(),
                            precio=int(get_precio()),
                            zelle=get_zelle(), precio_dolares=get_dolar(), porcentaje=get_porcentaje(True), disponibilidad = get_porcentaje(False))


@app.route("/2/compra", methods=["POST", "GET"])
def pago2():
    """
    Versión duplicada para la rifa2: usa funciones con sufijo _2 y plantillas terminadas en '2'.
    """
    estatus = get_estatus2()
    if estatus == "Venta finalizada":
        return redirect(url_for('index'))
    return render_template("comprar2.html", cant_min=get_minima2(),
                            precio=int(get_precio2()) if get_precio2() is not None else 0,
                            zelle=get_zelle2(), precio_dolares=get_dolar2(), porcentaje=get_porcentaje2(True), disponibilidad = get_porcentaje2(False))

@app.route("/verify", methods=["POST", "GET"])
def verificar():
    return render_template("verificar.html")

@app.route("/verify2", methods=["POST", "GET"])
def verificar2():
    return render_template("verificar2.html")


@app.route("/registrar_compra", methods=["POST", "GET"])
def registrar():
    if request.method == "POST":

        # Recuperar los datos del formulario
        nombre = request.form["nombre"]
        cedula = request.form["cedula"]
        nmr_te = request.form["telefono"]
        nmr_r = request.files["referencia"]
        if not nmr_te or nmr_te.strip() == "":
            return jsonify({"success": False, "message": "Por favor, completa el número de teléfono."}), 400

        # Validar y guardar el archivo de referencia si es necesario
        if nmr_r and allowed_file(nmr_r.filename):
            filename = secure_filename(nmr_r.filename)
            # Agregar un sufijo aleatorio al nombre del archivo
            nombre_archivo, extension = os.path.splitext(filename)
            sufijo = generar_sufijo_aleatorio()
            filename = f"{nombre_archivo}_{sufijo}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # Compress and save as JPEG
            success = compress_and_save(nmr_r, filepath, max_width=1200, quality=70)
            referencia_ruta = os.path.join('/static/comprobantes', filename).replace("\\", "/") if success else None
            fecha = get_enunciado()

        # Recuperar los datos de la compra (los valores pasados en los campos ocultos)
        cant_tickets = request.form.get("quantity", "")
        digitos = request.form.get("digitos", "")
        # validar digitos: deben ser exactamente 4 dígitos numéricos
        if not digitos or not digitos.isdigit() or len(digitos) != 4:
            return jsonify({"success": False, "message": "Los 4 dígitos deben ser numéricos."}), 400
        if int(cant_tickets) == 0:
            return redirect(url_for('index'))
        tickets_seleccionados = get_tickets(cant_tickets)
        total_price = request.form.get("total_price", 0)
        total_price_2 = request.form.get("total_price_2", 0)


        link = f'/{cedula}'

        # Insertar los datos en la base de datos
        insertar_comprador(
            nombre, cedula, nmr_te, filename, tickets_seleccionados,
            f"{total_price}bs",
            fecha, referencia_ruta, link, tickets_seleccionados, digitos
        )

        return render_template('confirmacion.html')

    return redirect(url_for('index'))


@app.route("/2/registrar_compra", methods=["POST", "GET"])
def registrar2():
    if request.method == "POST":

        # Recuperar los datos del formulario
        nombre = request.form["nombre"]
        cedula = request.form["cedula"]
        nmr_te = request.form["telefono"]
        nmr_r = request.files["referencia"]
        if not nmr_te or nmr_te.strip() == "":
            return jsonify({"success": False, "message": "Por favor, completa el número de teléfono."}), 400

        # Validar y guardar el archivo de referencia si es necesario
        if nmr_r and allowed_file(nmr_r.filename):
            filename = secure_filename(nmr_r.filename)
            # Agregar un sufijo aleatorio al nombre del archivo
            nombre_archivo, extension = os.path.splitext(filename)
            sufijo = generar_sufijo_aleatorio()
            filename = f"{nombre_archivo}_{sufijo}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            success = compress_and_save(nmr_r, filepath, max_width=1200, quality=70)
            referencia_ruta = os.path.join('/static/comprobantes', filename).replace("\\", "/") if success else None
            fecha = get_enunciado2()

        # Recuperar los datos de la compra (los valores pasados en los campos ocultos)
        cant_tickets = request.form.get("quantity", "")
        digitos = request.form.get("digitos", "")
        # validar digitos: deben ser exactamente 4 dígitos numéricos
        if not digitos or not digitos.isdigit() or len(digitos) != 4:
            return jsonify({"success": False, "message": "Los 4 dígitos deben ser numéricos."}), 400
        if int(cant_tickets) == 0:
            return redirect(url_for('index'))
        tickets_seleccionados = get_tickets2(cant_tickets)
        total_price = request.form.get("total_price", 0)
        total_price_2 = request.form.get("total_price_2", 0)


        link = f'/{cedula}'

        # Insertar los datos en la base de datos (rifa2)
        insertar_comprador2(
            nombre, cedula, nmr_te, filename, tickets_seleccionados,
            f"{total_price}bs",
            fecha, referencia_ruta, link, tickets_seleccionados, digitos
        )

        return render_template('confirmacion2.html')

    return redirect(url_for('index'))

@app.route("/admin/dashboard/partida/reiniciar" , methods = ["POST"])
@login_required  # Ruta protegida por login
def reiniciar():

    conn = sqlite3.connect('rifa.db')
    cursor = conn.cursor()

    cursor.execute("""DELETE FROM tickets_disponibles WHERE 1 = 1""")
    conn.commit()

    cursor.execute("""DELETE FROM requeridos WHERE 1 = 1""")
    conn.commit()

    cursor.executemany("""
    INSERT OR IGNORE INTO tickets_disponibles (carton_disponible) VALUES (?);
    """, [(i,) for i in range(1, 10001)])
    conn.commit()

    conn.close()

        # Eliminar todos los archivos en /static/comprobantes/
    # folder_path = 'static/comprobantes/'
    # for filename in os.listdir(folder_path):
    #     file_path = os.path.join(folder_path, filename)
    #     if os.path.isfile(file_path):  # Verificar si es un archivo
    #         os.remove(file_path)

    # Redirigir al panel de administración
    return redirect(url_for('admin_dashboard_partida'))

@app.route("/2/admin/dashboard/partida/reiniciar" , methods = ["POST"])
@login_required  # Ruta protegida por login
def reiniciar2():
    conn = sqlite3.connect('rifa2.db')
    cursor = conn.cursor()

    cursor.execute("""DELETE FROM tickets_disponibles WHERE 1 = 1""")
    conn.commit()

    cursor.execute("""DELETE FROM requeridos WHERE 1 = 1""")
    conn.commit()

    cursor.executemany("""
    INSERT OR IGNORE INTO tickets_disponibles (carton_disponible) VALUES (?);
    """, [(i,) for i in range(1, 10001)])
    conn.commit()

    conn.close()

    # Opcional: eliminar comprobantes si lo deseas (mantengo comentado como en reiniciar)
    # folder_path = 'static/comprobantes/'
    # for filename in os.listdir(folder_path):
    #     file_path = os.path.join(folder_path, filename)
    #     if os.path.isfile(file_path):
    #         os.remove(file_path)

    # Redirigir al panel de administración de rifa2
    return redirect(url_for('admin_dashboard_partida2'))



@app.route('/<cedula>')
def view_data(cedula):
    """
    Renderiza una plantilla HTML con el nombre y los tickets asociados a la cédula.
    """
    # Obtener datos del comprador desde la base de datos (implementar lógica en tu función)
    comprador = obtener_comprador_por_cedula(cedula)  # Ejemplo de función
    if not comprador:
        return redirect(url_for('verificar'))

    nombre = comprador["nombre"]
    tickets = comprador["tickets"]

    # Renderizar la plantilla con los datos
    return render_template('descargar_tickets.html', nombre=nombre, tickets=tickets)

@app.route('/2/<cedula>')
def view_data2(cedula):
    """
    Renderiza una plantilla HTML con el nombre y los tickets asociados a la cédula.
    """
    # Obtener datos del comprador desde la base de datos (implementar lógica en tu función)
    comprador = obtener_comprador_por_cedula2(cedula)  # Ejemplo de función
    if not comprador:
        return redirect(url_for('verificar2'))
        digitos = request.form.get("digitos", "")
        # validar digitos: deben ser exactamente 4 dígitos numéricos
        if not digitos or not digitos.isdigit() or len(digitos) != 4:
            return jsonify({"success": False, "message": "Los 4 dígitos deben ser numéricos."}), 400

    nombre = comprador["nombre"]
    tickets = comprador["tickets"]

    # Renderizar la plantilla con los datos
    return render_template('descargar_tickets2.html', nombre=nombre, tickets=tickets)

@app.route('/comprobar_tickets')
def comprobar_tickets():
    tickets = request.args.get('orden', '')
    tickets_lista = tickets.split(',')

    # Puedes devolver una vista donde se muestran las imágenes de los cartones
    return render_template('comprobar_tickets.html', tickets=tickets_lista)


@app.route('/comprobar_tickets2')
def comprobar_tickets2():
    tickets = request.args.get('orden', '')
    tickets_lista = tickets.split(',')

    # Versión duplicada que usa plantilla con sufijo 2
    return render_template('comprobar_tickets2.html', tickets=tickets_lista)

@app.route("/admin", methods=["GET", "POST"])
def admin_index():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "admin123":
            session['logged_in'] = True  # Establece que el usuario está autenticado
            return redirect(url_for('admin_dashboard'))  # redirigir a un panel de administración
        else:
            error_message = "Usuario o contraseña incorrectos"
            return render_template("login.html", error_message=error_message)

    return render_template("login.html")


@app.route("/2/admin", methods=["GET", "POST"])
def admin_index2():
    # Duplicado del login para rifa2 (usa plantilla con sufijo 2)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "admin123":
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard2'))
        else:
            error_message = "Usuario o contraseña incorrectos"
            return render_template("login2.html", error_message=error_message)

    return render_template("login2.html")

@app.route("/admin/dashboard")
@login_required  # Ruta protegida por login

def admin_dashboard():
    return render_template("panel_admin.html")


@app.route("/2/admin/dashboard")
@login_required
def admin_dashboard2():
    return render_template("panel_admin2.html")


@app.route("/admin/dashboard/partida" , methods = ["POST" , "GET"])
@login_required  # Ruta protegida por login

def admin_dashboard_partida():
    datos = obtener_datos_partida()

    if request.method == "POST":
        scnd_price = request.form.get("scnd_price")
        with sqlite3.connect("rifa.db") as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS scnd_price
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                precio INTEGER)''')
            conn.commit()
            cursor.execute('''SELECT precio FROM scnd_price LIMIT 1;''')
            if not scnd_price:
                scnd_price = cursor.fetchone()
            cursor.execute('''UPDATE scnd_price SET precio = ?''', (scnd_price,))
            conn.commit()

        UPLOAD_FOLDER_PARTIDA = "static/img"

        if "imagen" in request.files:
            file = request.files["imagen"]
            if file and allowed_file(file.filename):
                print("Archivo recibido correctamente.")  # Verifica si entra aquí
                os.makedirs(UPLOAD_FOLDER_PARTIDA, exist_ok=True)
                filename = secure_filename("partida.jpg")
                filepath = os.path.join(UPLOAD_FOLDER_PARTIDA, filename)
                file.save(filepath)
                print(f"Imagen guardada en: {filepath}")  # Verifica la ruta guardada
            else:
                print("Archivo no permitido.")
        else:
            print("No se recibió ningún archivo.")

        action = request.form.get("action")  #"reiniciar" o "detener"
        fecha_enunciado = request.form.get("fechaEnunciado")
        recompensa = request.form.get("recompensa")
        precio_carton = request.form.get("precioTicket", 0)
        print(precio_carton)
        tipo_ticket = request.form.get("tipoTicket")
        precio_dolares = request.form.get("precioTicket$", 0)
        zelle = request.form.get("zelle")
        actualizar_partida(fecha_enunciado, recompensa, precio_carton, tipo_ticket, action, precio_dolares, zelle)
        return redirect(url_for('admin_dashboard_partida'))  #redirigir a un panel de administración
    return render_template("admin_partida.html", datos=datos)


@app.route("/2/admin/dashboard/partida", methods=["POST", "GET"])
@login_required
def admin_dashboard_partida2():
    # Vista de partida para rifa2. Acepta GET y POST para actualizar valores en rifa2.db.
    datos = {
        'estatus': get_estatus2(),
        'venta': get_enunciado2(),
        'recompensa': get_premio2(),
        'precio_de_ticket': get_precio2(),
        'minima_ticket_regalo': get_minima2(),
        'precio_dolar': get_dolar2(),
        'zelle': get_zelle2(),
    }

    if request.method == 'POST':
        scnd_price = request.form.get('scnd_price')
        # Persistir scnd_price en rifa2.db
        with sqlite3.connect("rifa2.db") as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS scnd_price
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                precio INTEGER)''')
            conn.commit()
            cursor.execute('''SELECT precio FROM scnd_price LIMIT 1;''')
            if not scnd_price:
                scnd_price = cursor.fetchone()
            cursor.execute('''UPDATE scnd_price SET precio = ?''', (scnd_price,))
            conn.commit()

        UPLOAD_FOLDER_PARTIDA = "static/img"

        if "imagen" in request.files:
            file = request.files["imagen"]
            if file and allowed_file(file.filename):
                os.makedirs(UPLOAD_FOLDER_PARTIDA, exist_ok=True)
                # guardar con nombre distinto para rifa2
                filename = secure_filename("partida2.jpg")
                filepath = os.path.join(UPLOAD_FOLDER_PARTIDA, filename)
                file.save(filepath)
            else:
                # archivo no permitido o no enviado - continuar sin fallo
                pass

        # Campos del formulario
        action = request.form.get('action')
        fecha_enunciado = request.form.get('fechaEnunciado')
        recompensa = request.form.get('recompensa')
        precio_carton = request.form.get('precioTicket', 0)
        tipo_ticket = request.form.get('tipoTicket')
        precio_dolares = request.form.get('precioTicket$', 0)
        zelle = request.form.get('zelle')

        # Asegurar que exista la fila en venta; si no, crearla
        with sqlite3.connect('rifa2.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='venta';")
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS venta (
                        id INTEGER PRIMARY KEY,
                        venta TEXT,
                        hora_de_partida TEXT,
                        precio_de_ticket REAL,
                        estatus TEXT,
                        mensaje TEXT,
                        recompensa TEXT,
                        minima_ticket_regalo TEXT,
                        precio_dolar REAL,
                        zelle TEXT
                    );
                ''')
                conn.commit()

            cursor.execute("SELECT COUNT(*) FROM venta;")
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute("INSERT INTO venta (id, venta, hora_de_partida, precio_de_ticket, estatus, mensaje) VALUES (1, ?, ?, ?, ?, ?);", ("", "", 0.0, "Venta finalizada", ""))
                conn.commit()

            # Construir update dinámico
            fields = []
            values = []
            if fecha_enunciado:
                fields.append("venta = ?"); values.append(fecha_enunciado)
            if recompensa:
                fields.append("recompensa = ?"); values.append(recompensa)
            if precio_carton is not None and precio_carton != '':
                try:
                    # tratar como número si es posible
                    precio_val = float(precio_carton)
                    fields.append("precio_de_ticket = ?"); values.append(precio_val)
                except Exception:
                    fields.append("precio_de_ticket = ?"); values.append(precio_carton)
            if precio_dolares is not None and precio_dolares != '':
                fields.append("precio_dolar = ?"); values.append(precio_dolares)
            if zelle is not None:
                fields.append("zelle = ?"); values.append(zelle)
            if tipo_ticket:
                fields.append("minima_ticket_regalo = ?"); values.append(tipo_ticket)
            if action:
                fields.append("estatus = ?"); values.append(action)

            if fields:
                update_query = f"UPDATE venta SET {', '.join(fields)} WHERE id = 1;"
                cursor.execute(update_query, values)
                conn.commit()

        return redirect(url_for('admin_dashboard_partida2'))

    # GET: renderizar vista
    return render_template("admin_partida2.html", datos=datos)


@app.route("/admin/dashboard/historial" , methods = ["POST" , "GET"])
@login_required  # Ruta protegida por login

def admin_dashboard_historial():
    datos = obtener_datos_historial()
    return render_template("admin_historial.html", datos=datos)


@app.route("/2/admin/dashboard/historial", methods=["POST", "GET"])
@login_required
def admin_dashboard_historial2():
    datos = obtener_datos_historial()
    return render_template("admin_historial2.html", datos=datos)



@app.route("/admin/dashboard/solicitudes")
@login_required  # Ruta protegida por login
def admin_dashboard_solicitudes():
    solicitudes = get_data()  # Recupera los datos de la tabla
    return render_template("admin_solicitudes.html", solicitudes=solicitudes, json=json)


@app.route("/2/admin/dashboard/solicitudes")
@login_required
def admin_dashboard_solicitudes2():
    # Para rifa2 usamos get_data0 (duplicada que apunta a rifa2.db)
    solicitudes = get_data0()
    return render_template("admin_solicitudes2.html", solicitudes=solicitudes, json=json)

@app.route("/admin/dashboard/solicitudes/top")
@login_required  # Ruta protegida por login
def top():
    solicitudes = get_data2()
    return render_template("top.html", solicitudes = solicitudes)


@app.route("/2/admin/dashboard/solicitudes/top")
@login_required
def top2():
    solicitudes = get_data02()
    return render_template("top2.html", solicitudes=solicitudes)

@app.route("/admin/dashboard/solicitudes/invalidate/", methods=["POST"])
def invalidate():
    data = request.get_json()
    solicitud_id = data.get("id")

    # Conectar a la base de datos
    conn = sqlite3.connect('rifa.db')
    cursor = conn.cursor()

    try:
        # Obtener los cartones asociados a la solicitud
        cursor.execute("""SELECT tickets_vendidos FROM requeridos WHERE id = ?""", (solicitud_id,))
        cartones_solicitados = cursor.fetchone()

        if not cartones_solicitados:
            return jsonify({"success": False, "message": "Solicitud no encontrada"}), 404

        # Extraer los cartones vendidos como texto
        cartones_texto = cartones_solicitados[0]  # Obtener el primer resultado
        if isinstance(cartones_texto, str):
            cartones = [int(carton.strip()) for carton in cartones_texto.strip('[]').split(',') if carton.strip().isdigit()]
        else:
            cartones = [int(cartones_texto)]


        # Reintegrar los cartones a la tabla de disponibles
        reintegrar_tickets(cartones)

        # Actualizar el estado de la solicitud como invalidada
        cursor.execute("""UPDATE requeridos SET estatus = "invalidado" WHERE id = ?""", (solicitud_id,))
        conn.commit()
        cursor.execute("""DELETE FROM requeridos WHERE id = ?""", (solicitud_id,))
        conn.commit()

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        conn.close()

    return redirect(url_for('prueba'))


@app.route("/2/admin/dashboard/solicitudes/invalidate/", methods=["POST"])
def invalidate2():
    data = request.get_json()
    solicitud_id = data.get("id")

    # Conectar a la base de datos rifa2
    conn = sqlite3.connect('rifa2.db')
    cursor = conn.cursor()

    try:
        cursor.execute("""SELECT tickets_vendidos FROM requeridos WHERE id = ?""", (solicitud_id,))
        cartones_solicitados = cursor.fetchone()

        if not cartones_solicitados:
            return jsonify({"success": False, "message": "Solicitud no encontrada"}), 404

        cartones_texto = cartones_solicitados[0]
        if isinstance(cartones_texto, str):
            cartones = [int(carton.strip()) for carton in cartones_texto.strip('[]').split(',') if carton.strip().isdigit()]
        else:
            cartones = [int(cartones_texto)]

        reintegrar_tickets2(cartones)

        cursor.execute("""UPDATE requeridos SET estatus = "invalidado" WHERE id = ?""", (solicitud_id,))
        conn.commit()
        cursor.execute("""DELETE FROM requeridos WHERE id = ?""", (solicitud_id,))
        conn.commit()

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        conn.close()

    return redirect(url_for('prueba2'))


@app.route("/admin/dashboard/solicitudes/invalidate/prueba", methods=["GET", "POST"])
def prueba():
    time.sleep(1)
    return redirect(url_for('admin_dashboard_solicitudes'))


@app.route("/2/admin/dashboard/solicitudes/invalidate/prueba", methods=["GET", "POST"])
def prueba2():
    time.sleep(1)
    return redirect(url_for('admin_dashboard_solicitudes2'))

@app.route("/admin/dashboard/solicitudes/message/", methods=["POST"])
def message():
    data = request.get_json()
    solicitud_id = data.get("id")

    # Conectar a la base de datos
    conn = sqlite3.connect('rifa.db')
    cursor = conn.cursor()

    # Verificar si la solicitud existe
    cursor.execute("""UPDATE requeridos SET estatus = "enviado" WHERE id = ?""", (solicitud_id,))
    conn.commit()

    # Extraer los cartones vendidos como texto
    cursor.execute("""SELECT tickets_vendidos FROM requeridos WHERE id = ?""", (solicitud_id,))
    cartones_vendidos = cursor.fetchone()[0]  # Obtener el primer resultado
    conn.close()

    # Limpieza y conversión del string a lista de enteros
    if isinstance(cartones_vendidos, str):
        # Eliminar caracteres no deseados y dividir el string
        cartones = [int(carton.strip()) for carton in cartones_vendidos.strip('[]').split(',') if carton.strip().isdigit()]
    else:
        # Si no es un string, manejarlo como un único valor
        cartones = [int(cartones_vendidos)]


    # Llamar a la función para insertar los cartones
    vendidos(cartones)

    return redirect(url_for('admin_dashboard_solicitudes'))  # redirigir a un panel de administración


@app.route("/2/admin/dashboard/solicitudes/message/", methods=["POST"])
def message2():
    data = request.get_json()
    solicitud_id = data.get("id")

    # Conectar a la base de datos rifa2
    conn = sqlite3.connect('rifa2.db')
    cursor = conn.cursor()

    cursor.execute("""UPDATE requeridos SET estatus = "enviado" WHERE id = ?""", (solicitud_id,))
    conn.commit()

    cursor.execute("""SELECT tickets_vendidos FROM requeridos WHERE id = ?""", (solicitud_id,))
    cartones_vendidos = cursor.fetchone()[0]
    conn.close()

    if isinstance(cartones_vendidos, str):
        cartones = [int(carton.strip()) for carton in cartones_vendidos.strip('[]').split(',') if carton.strip().isdigit()]
    else:
        cartones = [int(cartones_vendidos)]

    vendidos2(cartones)

    return redirect(url_for('admin_dashboard_solicitudes2'))

import re

@app.route("/admin/dashboard/vendidos")
@login_required  # Ruta protegida por login
def mostrar_cartones():
    with sqlite3.connect("rifa.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tickets_vendidos FROM requeridos;")
        cartones_tuplas = cursor.fetchall()
        conn.commit()
        cursor.execute("""
            SELECT monto
            FROM requeridos
            WHERE id IN (
                SELECT MIN(id)
                FROM requeridos
                GROUP BY tickets_vendidos
            );
        """)
        montos = cursor.fetchall()

        # Procesar los montos
        total_bs = 0
        total_dolar = 0

        for monto in montos:
            if monto and monto[0]:
                # Expresión regular para separar los montos antes de 'bs' y entre '/' y '$'
                match_bs = re.search(r'([\d.]+)bs', monto[0])
                match_dolar = re.search(r'/([\d.]+)\$', monto[0])

                if match_bs:
                    total_bs += float(match_bs.group(1))
                if match_dolar:
                    total_dolar += float(match_dolar.group(1))

        montos_totales = f"{total_bs}bs/{total_dolar}$"

        # Usar un conjunto para evitar duplicados
        cartones_set = set()
        for carton in cartones_tuplas:
            if carton[0]:  # Evitar errores con valores vacíos o nulos
                numeros = eval(carton[0]) if isinstance(carton[0], str) else carton[0]
                if isinstance(numeros, list):
                    cartones_set.update(numeros)
                else:
                    cartones_set.add(numeros)

        # Convertir el conjunto a lista para pasar a la plantilla
        tickets = list(cartones_set)

        return render_template("disponibles_no.html", tickets=tickets, montos_totales=montos_totales)


@app.route("/2/admin/dashboard/vendidos")
@login_required
def mostrar_cartones2():
    with sqlite3.connect("rifa2.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tickets_vendidos FROM requeridos;")
        cartones_tuplas = cursor.fetchall()
        conn.commit()
        cursor.execute("""
            SELECT monto
            FROM requeridos
            WHERE id IN (
                SELECT MIN(id)
                FROM requeridos
                GROUP BY tickets_vendidos
            );
        """)
        montos = cursor.fetchall()

        total_bs = 0
        total_dolar = 0

        for monto in montos:
            if monto and monto[0]:
                match_bs = re.search(r'([\d.]+)bs', monto[0])
                match_dolar = re.search(r'/([\d.]+)\$', monto[0])

                if match_bs:
                    total_bs += float(match_bs.group(1))
                if match_dolar:
                    total_dolar += float(match_dolar.group(1))

        montos_totales = f"{total_bs}bs/{total_dolar}$"

        cartones_set = set()
        for carton in cartones_tuplas:
            if carton[0]:
                numeros = eval(carton[0]) if isinstance(carton[0], str) else carton[0]
                if isinstance(numeros, list):
                    cartones_set.update(numeros)
                else:
                    cartones_set.add(numeros)

        tickets = list(cartones_set)

        return render_template("disponibles_no2.html", tickets=tickets, montos_totales=montos_totales)



if __name__ == '__main__':
    app.run(debug=True)
