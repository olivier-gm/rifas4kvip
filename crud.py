import sqlite3
import json
import time
from flask import request

DB_NAME = "rifa.db"
DB_NAME2 = "rifa2.db"

def execute_query(query, params=(), fetch=False, fetchone=False, db=DB_NAME):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(query, params)
    if fetch:
        data = cursor.fetchone() if fetchone else cursor.fetchall()
    else:
        conn.commit()
        data = None
    conn.close()
    return data

def obtener_datos_partida():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT estatus, venta, recompensa, precio_de_ticket, precio_dolar, zelle, minima_ticket_regalo FROM venta WHERE id = 1")
    resultado = cursor.fetchone()
    conn.commit()
    conn.close()
    return resultado if resultado else None

def actualizar_partida(fecha_enunciado=None, recompensa=None, precio_carton=None, tipo_ticket=None, action=None, precio_dolares=None, zelle=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM venta;")
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("""
            INSERT INTO venta (venta, recompensa, precio_de_ticket, minima_ticket_regalo, estatus)
            VALUES (?, ?, ?, ?, ?);
        """, ("", "", 0.0, "", "Venta finalizada"))
        conn.commit()

    fields = []
    values = []
    if fecha_enunciado:
        fields.append("venta = ?"); values.append(fecha_enunciado)
    if recompensa:
        fields.append("recompensa = ?"); values.append(recompensa)
    if precio_carton is not None:
        fields.append("precio_de_ticket = ?"); values.append(precio_carton)
    if precio_dolares is not None:
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
    conn.close()

def venta(C=None, read=None, U=None, D=None):
    if C:
        query = """
        INSERT OR REPLACE INTO venta (id, venta, hora_de_partida, precio_de_ticket, estatus, mensaje)
        VALUES (1, ?, ?, ?, ?, ?);
        """
        execute_query(query, C)
    elif read:
        query = "SELECT * FROM venta WHERE id = 1;"
        return execute_query(query, fetch=True)
    elif U:
        query = """
        UPDATE venta
        SET venta = ?, hora_de_partida = ?, precio_de_ticket = ?, estatus = ?, mensaje = ?
        WHERE id = 1;
        """
        execute_query(query, U)
    elif D:
        query = "DELETE FROM venta WHERE id = 1;"
        execute_query(query)

def tickets_disponibles(C=None, read=None, U=None, D=None):
    if C:
        query = "SELECT carton FROM tickets_usados;"
        return execute_query(query, fetch=True)
    elif read:
        if read == "*":
            query = "SELECT carton_disponible FROM tickets_disponibles;"
            return execute_query(query, fetch=True)
        else:
            query = "SELECT * FROM tickets_disponibles WHERE carton_disponible = ?;"
            return execute_query(query, (read,), fetch=True)

def tickets_usados(C=None, read=None, U=None, D=None):
    if C:
        query = "INSERT OR IGNORE INTO tickets_usados (carton, usuario) VALUES (?, ?);"
        execute_query(query, C)
    elif read:
        if read == "*":
            query = "SELECT carton FROM tickets_usados;"
            return execute_query(query, fetch=True)
        else:
            query = "SELECT * FROM tickets_usados WHERE carton = ?;"
            return execute_query(query, (read,), fetch=True)
    elif U:
        query = "UPDATE tickets_usados SET usuario = ? WHERE carton = ?;"
        execute_query(query, U)
    elif D:
        query = "DELETE FROM tickets_usados WHERE carton = ?;"
        execute_query(query, (D,))

def requeridos(C=None, read=None, U=None, D=None, table="requeridos"):
    if C:
        query = f"""
        INSERT INTO {table}
        (nombre_apellidos, cedula, telefono, referencia, tickets_vendidos, monto, fecha, link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        execute_query(query, C)
    elif read:
        query = f"SELECT * FROM {table} WHERE cedula = ?;"
        return execute_query(query, (read,), fetch=True)
    elif U:
        query = f"""
        UPDATE {table}
        SET nombre_apellidos = ?, telefono = ?, referencia = ?,
            tickets_vendidos = ?, monto = ?, fecha = ?
        WHERE cedula = ?;
        """
        execute_query(query, U)
    elif D:
        query = f"DELETE FROM {table} WHERE cedula = ?;"
        execute_query(query, (D,))

def usuarios_aceptados(C=None, read=None, U=None, D=None):
    requeridos(C, read, U, D, table="usuarios_aceptados")

def get_data2():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            MIN(id) AS id,
            nombre_apellidos,
            cedula,
            telefono,
            referencia,
            GROUP_CONCAT(tickets_vendidos) AS cartones,
            SUM(monto) AS monto,
            fecha,
            estatus,
            MIN(digitos) AS digitos,
            link,
            SUM(
                (SELECT LENGTH(REPLACE(REPLACE(tickets_vendidos, '[', ''), ']', '')) - LENGTH(REPLACE(REPLACE(tickets_vendidos, ',', ''), '[', '')) + 2)
            ) AS length
        FROM requeridos
        GROUP BY cedula
    """)
    rows = cursor.fetchall()
    conn.close()
    solicitudes = []
    for row in rows:
        solicitud = {
            "id": row[0], "nombre": row[1], "cedula": row[2], "telefono": row[3],
            "referencia": row[4], "cartones": row[5], "monto": row[6],
            "fecha": row[7], "estatus": row[8], "digitos": row[9], "link": row[10], "length": row[11],
        }
        solicitudes.append(solicitud)
    return solicitudes

def get_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            MIN(id) AS id,
            nombre_apellidos,
            cedula,
            telefono,
            referencia,
            tickets_vendidos,
            monto,
            fecha,
            estatus,
            digitos,
            link,
            SUM(
                (SELECT LENGTH(REPLACE(REPLACE(tickets_vendidos, '[', ''), ']', '')) - LENGTH(REPLACE(REPLACE(tickets_vendidos, ',', ''), '[', '')) + 2)
            ) AS length
        FROM requeridos
        GROUP BY id
    """)
    rows = cursor.fetchall()
    conn.close()
    solicitudes = []
    for row in rows:
        # Some databases may have the new 'digitos' column at the end; access safely
        dig = None
        try:
            dig = row[10]
        except Exception:
            dig = None
        solicitud = {
            "id": row[0], "nombre": row[1], "cedula": row[2], "telefono": row[3],
            "referencia": row[4], "cartones": row[5], "monto": row[6],
            "fecha": row[7], "estatus": row[8], "digitos": row[9], "link": row[10], "length": row[11],
        }
        solicitudes.append(solicitud)
    return solicitudes

def get_data02():
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            MIN(id) AS id,
            nombre_apellidos,
            cedula,
            telefono,
            referencia,
            GROUP_CONCAT(tickets_vendidos) AS cartones,
            SUM(monto) AS monto,
            fecha,
            estatus,
            MIN(digitos) AS digitos,
            link,
            SUM(
                (SELECT LENGTH(REPLACE(REPLACE(tickets_vendidos, '[', ''), ']', '')) - LENGTH(REPLACE(REPLACE(tickets_vendidos, ',', ''), '[', '')) + 2)
            ) AS length
        FROM requeridos
        GROUP BY cedula
    """)
    rows = cursor.fetchall()
    conn.close()
    solicitudes = []
    for row in rows:
        solicitud = {
            "id": row[0], "nombre": row[1], "cedula": row[2], "telefono": row[3],
            "referencia": row[4], "cartones": row[5], "monto": row[6],
            "fecha": row[7], "estatus": row[8], "digitos": row[9], "link": row[10], "length": row[11],
        }
        solicitudes.append(solicitud)
    return solicitudes

def get_data0():
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            MIN(id) AS id,
            nombre_apellidos,
            cedula,
            telefono,
            referencia,
            tickets_vendidos,
            monto,
            fecha,
            estatus,
            digitos,
            link,
            SUM(
                (SELECT LENGTH(REPLACE(REPLACE(tickets_vendidos, '[', ''), ']', '')) - LENGTH(REPLACE(REPLACE(tickets_vendidos, ',', ''), '[', '')) + 2)
            ) AS length
        FROM requeridos
        GROUP BY id
    """)
    rows = cursor.fetchall()
    conn.close()
    solicitudes = []
    for row in rows:
        # Some databases may have the new 'digitos' column at the end; access safely
        dig = None
        try:
            dig = row[10]
        except Exception:
            dig = None
        solicitud = {
            "id": row[0], "nombre": row[1], "cedula": row[2], "telefono": row[3],
            "referencia": row[4], "cartones": row[5], "monto": row[6],
            "fecha": row[7], "estatus": row[8], "digitos": row[9], "link": row[10], "length": row[11],
        }
        solicitudes.append(solicitud)
    return solicitudes

# --------- funciones para rifa (DB default) ----------
def get_enunciado():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT estatus FROM venta WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    estatus = row[0]
    if estatus == "Venta en curso":
        data = execute_query("SELECT venta FROM venta LIMIT 1", fetch=True, fetchone=True)
        return data[0] if data else None
    return "No disponible"

def get_premio():
    data = execute_query("SELECT recompensa FROM venta LIMIT 1", fetch=True, fetchone=True)
    return data[0] if data else None

def get_porcentaje(flag):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(carton_disponible) FROM tickets_disponibles")
    cantidad = cursor.fetchone()[0]
    conn.close()
    if flag is False:
        return cantidad
    total = 10000
    return round((cantidad / total) * 100, 2)

def get_precio():
    data = execute_query("SELECT precio_de_ticket FROM venta LIMIT 1", fetch=True, fetchone=True)
    return data[0] if data else None

def get_estatus():
    data = execute_query("SELECT estatus FROM venta WHERE id = 1", fetch=True, fetchone=True)
    return data[0] if data else None

def get_minima():
    data = execute_query("SELECT minima_ticket_regalo FROM venta WHERE id = 1", fetch=True, fetchone=True)
    return data[0] if data else None

def get_dolar():
    data = execute_query("SELECT precio_dolar FROM venta WHERE id = 1", fetch=True, fetchone=True)
    return data[0] if data else None

def get_zelle():
    data = execute_query("SELECT zelle FROM venta WHERE id = 1", fetch=True, fetchone=True)
    return data[0] if data else None

def insertar_comprador(nombre_apellido, cedula, telefono, referencia, tickets_vendidos, monto, fecha, referencia_ruta, link, tickets_vendidos_str, digitos=None, max_retries=3, delay=2):
    tickets_vendidos = [int(carton) for carton in tickets_vendidos_str] if isinstance(tickets_vendidos_str, (list, tuple)) else [int(x.strip()) for x in ','.join(map(str, tickets_vendidos_str)).split(',') if x.strip()]
    tickets_vendidos_text = json.dumps(tickets_vendidos)
    attempt = 0
    while attempt < max_retries:
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            conn.execute("BEGIN TRANSACTION;")
            placeholders = ','.join(['?'] * len(tickets_vendidos))
            query = f"SELECT carton_disponible FROM tickets_disponibles WHERE carton_disponible IN ({placeholders})"
            cursor.execute(query, tickets_vendidos)
            tickets_disponibles = [row[0] for row in cursor.fetchall()]
            if len(tickets_disponibles) != len(tickets_vendidos):
                conn.execute("ROLLBACK;")
                conn.close()
                attempt += 1
                time.sleep(delay)
                continue
            cursor.execute(f"DELETE FROM tickets_disponibles WHERE carton_disponible IN ({placeholders});", tickets_vendidos)
            cursor.execute("""
                INSERT INTO requeridos (
                    nombre_apellidos, cedula, telefono, referencia,
                    tickets_vendidos, monto, fecha, link, digitos
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (nombre_apellido, cedula, telefono, referencia, tickets_vendidos_text, monto, fecha, link, digitos))
            conn.commit()
            conn.close()
            break
        except sqlite3.OperationalError:
            try:
                conn.execute("ROLLBACK;")
            except Exception:
                pass
            conn.close()
            attempt += 1
            time.sleep(delay)

def obtener_comprador_por_cedula(cedula):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT nombre_apellidos, tickets_vendidos FROM requeridos WHERE cedula = ?', (cedula,))
        resultados = cursor.fetchall()
    if not resultados:
        return None
    nombre_apellidos = resultados[0][0]
    tickets_vendidos = []
    for _, tickets_str in resultados:
        try:
            tickets = json.loads(tickets_str) if isinstance(tickets_str, str) else list(tickets_str)
            tickets_vendidos.extend(int(t) for t in tickets)
        except Exception:
            continue
    return {"nombre": nombre_apellidos, "tickets": tickets_vendidos}

def get_tickets(cant_tickets):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets_disponibles")
        total_columns = cursor.fetchone()[0]
        if int(cant_tickets) > int(total_columns):
            cant_tickets = total_columns
        query = f"SELECT carton_disponible FROM tickets_disponibles ORDER BY RANDOM() ASC LIMIT {int(cant_tickets)}"
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return [row[0] for row in results]
    except sqlite3.Error:
        return []

def reintegrar_tickets(cartones):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cartones_tuplas = [(carton,) for carton in cartones]
    try:
        cursor.executemany("INSERT OR IGNORE INTO tickets_disponibles (carton_disponible) VALUES (?);", cartones_tuplas)
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def vendidos(cartones):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cartones_tuplas = [(carton,) for carton in cartones]
    try:
        cursor.executemany("INSERT INTO tickets_usados (carton) VALUES (?);", cartones_tuplas)
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

# --------- funciones duplicadas para rifa2 (DB_NAME2) ----------
def get_enunciado2():
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cursor.execute("SELECT estatus FROM venta WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    estatus = row[0]
    if estatus == "Venta en curso":
        conn = sqlite3.connect(DB_NAME2)
        cursor = conn.cursor()
        cursor.execute("SELECT venta FROM venta LIMIT 1")
        data = cursor.fetchone()
        conn.close()
        return data[0] if data else None
    return "No disponible"

def get_premio2():
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cursor.execute("SELECT recompensa FROM venta LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_porcentaje2(flag):
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(carton_disponible) FROM tickets_disponibles")
    cantidad = cursor.fetchone()[0]
    conn.close()
    if flag is False:
        return cantidad
    total = 10000
    return round((cantidad / total) * 100, 2)

def get_precio2():
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cursor.execute("SELECT precio_de_ticket FROM venta WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_estatus2():
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cursor.execute("SELECT estatus FROM venta WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_minima2():
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cursor.execute("SELECT minima_ticket_regalo FROM venta WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_dolar2():
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cursor.execute("SELECT precio_dolar FROM venta WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_zelle2():
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cursor.execute("SELECT zelle FROM venta WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def insertar_comprador2(nombre_apellido, cedula, telefono, referencia, tickets_vendidos, monto, fecha, referencia_ruta, link, tickets_vendidos_str, digitos=None, max_retries=3, delay=2):
    tickets_vendidos = [int(carton) for carton in tickets_vendidos_str] if isinstance(tickets_vendidos_str, (list, tuple)) else [int(x.strip()) for x in ','.join(map(str, tickets_vendidos_str)).split(',') if x.strip()]
    tickets_vendidos_text = json.dumps(tickets_vendidos)
    attempt = 0
    while attempt < max_retries:
        try:
            conn = sqlite3.connect(DB_NAME2)
            cursor = conn.cursor()
            conn.execute("BEGIN TRANSACTION;")
            placeholders = ','.join(['?'] * len(tickets_vendidos))
            query = f"SELECT carton_disponible FROM tickets_disponibles WHERE carton_disponible IN ({placeholders})"
            cursor.execute(query, tickets_vendidos)
            tickets_disponibles = [row[0] for row in cursor.fetchall()]
            if len(tickets_disponibles) != len(tickets_vendidos):
                conn.execute("ROLLBACK;")
                conn.close()
                attempt += 1
                time.sleep(delay)
                continue
            cursor.execute(f"DELETE FROM tickets_disponibles WHERE carton_disponible IN ({placeholders});", tickets_vendidos)
            cursor.execute("""
                INSERT INTO requeridos (
                    nombre_apellidos, cedula, telefono, referencia,
                    tickets_vendidos, monto, fecha, link, digitos
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (nombre_apellido, cedula, telefono, referencia, tickets_vendidos_text, monto, fecha, link, digitos))
            conn.commit()
            conn.close()
            break
        except sqlite3.OperationalError:
            try:
                conn.execute("ROLLBACK;")
            except Exception:
                pass
            conn.close()
            attempt += 1
            time.sleep(delay)

def obtener_comprador_por_cedula2(cedula):
    with sqlite3.connect(DB_NAME2) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT nombre_apellidos, tickets_vendidos FROM requeridos WHERE cedula = ?', (cedula,))
        resultados = cursor.fetchall()
    if not resultados:
        return None
    nombre_apellidos = resultados[0][0]
    tickets_vendidos = []
    for _, tickets_str in resultados:
        try:
            tickets = json.loads(tickets_str) if isinstance(tickets_str, str) else list(tickets_str)
            tickets_vendidos.extend(int(t) for t in tickets)
        except Exception:
            continue
    return {"nombre": nombre_apellidos, "tickets": tickets_vendidos}

def get_tickets2(cant_tickets):
    try:
        conn = sqlite3.connect(DB_NAME2)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets_disponibles")
        total_columns = cursor.fetchone()[0]
        if int(cant_tickets) > int(total_columns):
            cant_tickets = total_columns
        query = f"SELECT carton_disponible FROM tickets_disponibles ORDER BY RANDOM() ASC LIMIT {int(cant_tickets)}"
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return [row[0] for row in results]
    except sqlite3.Error:
        return []

def reintegrar_tickets2(cartones):
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cartones_tuplas = [(carton,) for carton in cartones]
    try:
        cursor.executemany("INSERT OR IGNORE INTO tickets_disponibles (carton_disponible) VALUES (?);", cartones_tuplas)
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def vendidos2(cartones):
    conn = sqlite3.connect(DB_NAME2)
    cursor = conn.cursor()
    cartones_tuplas = [(carton,) for carton in cartones]
    try:
        cursor.executemany("INSERT INTO tickets_usados (carton) VALUES (?);", cartones_tuplas)
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

# --------- flags persistence ----------
def obtener_datos_historial():
    conn = sqlite3.connect('config.db')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS feature_flags (
          key TEXT PRIMARY KEY,
          value INTEGER NOT NULL
        )
    """)
    defaults = [('mostrar_rifa2', 1), ('mostrar_rifa3', 0)]
    c.executemany("INSERT OR IGNORE INTO feature_flags (key,value) VALUES (?,?)", defaults)
    if request.method == 'POST':
        r2 = 1 if request.form.get('rifa2') == 'on' else 0
        r3 = 1 if request.form.get('rifa3') == 'on' else 0
        c.execute("UPDATE feature_flags SET value=? WHERE key='mostrar_rifa2'", (r2,))
        c.execute("UPDATE feature_flags SET value=? WHERE key='mostrar_rifa3'", (r3,))
        conn.commit()
    c.execute("SELECT key, value FROM feature_flags WHERE key IN ('mostrar_rifa2','mostrar_rifa3')")
    rows = dict(c.fetchall())
    conn.close()
    return {
        'mostrar_rifa2': int(rows.get('mostrar_rifa2', 1)),
        'mostrar_rifa3': int(rows.get('mostrar_rifa3', 0)),
    }
