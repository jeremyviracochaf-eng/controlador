import os
import time
from datetime import date, timedelta
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    session,
    flash
)
from flask_socketio import SocketIO, emit
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# ==============================================================================
# CONFIGURACIÓN DE LA APLICACIÓN Y BASE DE DATOS
# ==============================================================================

app = Flask(
    __name__,
    template_folder="../Frontend/templates",
    static_folder="../Frontend/static"
)

socketio = SocketIO(app, cors_allowed_origins="*")

# Clave secreta protegida para cifrado de sesiones administrativas
app.secret_key = os.getenv("SECRET_KEY")

# Conexión segura a MySQL usando variables de entorno locales
conexion = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_DATABASE"),

)

# --- ARQUITECTURA DE ESTADO GLOBAL CORREGIDA ---
# 1. 🔵 Orden (COMMAND)
orden_puerta = {"accion": None}
ultima_orden_enviada = {"accion": None}

# 2. 🟢 Estado físico (FEEDBACK hardware)
estado_puerta_hardware = "Bloqueada"  # Monitoreo de estado ("Bloqueada"/"Desbloqueada")

# Variables para control de debounce anti-duplicados RFID
ultimo_uid = ""
ultimo_tiempo_uid = 0


# ==============================================================================
# VISTAS PÚBLICAS / ACCESO
# ==============================================================================

@app.route("/")
def login_page():
    """Muestra la pantalla inicial de inicio de sesión."""
    # Si ya está logueado, lo mandamos directo al dashboard
    if "usuario" in session:
        return redirect("/dashboard")
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    """Procesa las credenciales del administrador para iniciar sesión de forma estricta."""
    usuario_input = request.form["usuario"].strip()
    password = request.form["password"]

    cursor = conexion.cursor()
    
    
    cursor.execute(
        """
        SELECT *
        FROM administradores
        WHERE BINARY usuario = %s
        """,
        (usuario_input,)
    )
    admin = cursor.fetchone()


    if admin and check_password_hash(admin[2], password):
        session["usuario"] = admin[1]

        cursor.execute(
            """
            INSERT INTO auditoria(usuario_admin, accion)
            VALUES(%s,%s)
            """,
            (admin[1], "Inició sesión")
        )
        conexion.commit()
        cursor.close()
        return redirect("/dashboard")


    cursor.close()
    flash("Usuario o contraseña incorrectos", "danger")
    return redirect("/")


@app.route("/logout")
def logout():
    """Cierra la sesión del administrador y registra la auditoría."""
    if "usuario" in session:
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO auditoria(usuario_admin, accion)
            VALUES(%s, %s)
            """,
            (session["usuario"], "Cerró sesión")
        )
        conexion.commit()
        cursor.close()

    session.pop("usuario", None)
    return redirect("/")


# ==============================================================================
# PANEL PRINCIPAL (DASHBOARD)
# ==============================================================================

@app.route("/dashboard")
def dashboard():
    """Muestra estadísticas generales del sistema (Solo administradores)."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()

    # Usuarios activos
    cursor.execute(
        """
       SELECT COUNT(*)
       FROM usuarios
        WHERE estado = 1
        """
    )
    usuarios_activos = cursor.fetchone()[0]

# Usuarios eliminados
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM usuarios
        WHERE estado = 2
        """
    )
    usuarios_eliminados = cursor.fetchone()[0]

    # Contadores de accesos permitidos
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM accesos
        WHERE estado_acceso='Permitido'
        """
    )
    permitidos = cursor.fetchone()[0]

    # Contadores de accesos denegados
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM accesos
        WHERE estado_acceso='Denegado'
        """
    )
    denegados = cursor.fetchone()[0]

    # CAMBIO AQUÍ: Obtenemos el último evento con su nombre ya resuelto por SQL
    cursor.execute(
        """
        SELECT 
            accesos.fecha_hora, 
            accesos.estado_acceso,
            CASE 
                WHEN accesos.uid_rfid = 'WEB' THEN 'Administrador'
                ELSE IFNULL(
                    usuarios.nombre, 
                    IFNULL((SELECT nombre FROM usuarios WHERE uid_rfid = accesos.uid_rfid LIMIT 1), 'Tarjeta No Registrada')
                )
            END AS nombre_persona
        FROM accesos
        LEFT JOIN usuarios ON accesos.usuario_id = usuarios.id
        ORDER BY accesos.id DESC
        LIMIT 1
        """
    )
    ultimo_acceso = cursor.fetchone()
    cursor.close()

    return render_template(
    "index.html",
    usuarios_activos=usuarios_activos,
    usuarios_eliminados=usuarios_eliminados,
    permitidos=permitidos,
    denegados=denegados,
    ultimo_acceso=ultimo_acceso
)


# ==============================================================================
# GESTIÓN DE USUARIOS (RUTAS ADMINISTRATIVAS)
# ==============================================================================

@app.route("/usuarios")
def usuarios():
    """Lista todos los usuarios registrados que no hayan sido eliminados."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()
    
    # CAMBIO AQUÍ: Filtramos para ignorar a los usuarios con estado = 2 (Eliminados)
    cursor.execute("SELECT * FROM usuarios WHERE estado != 2")
    datos = cursor.fetchall()
    cursor.close()  # Cerramos el cursor de forma limpia

    return render_template("usuarios.html", usuarios=datos)


@app.route("/nuevo_usuario")
def nuevo_usuario():
    """Muestra el formulario para registrar un nuevo usuario."""
    if "usuario" not in session:
        return redirect("/")
        
    return render_template("nuevo_usuario.html")


@app.route("/guardar_usuario", methods=["POST"])
def guardar_usuario():
    """Procesa el formulario e inserta el nuevo usuario en la base de datos."""
    if "usuario" not in session:
        return redirect("/")

    nombre = request.form["nombre"]
    uid = request.form.get("uid") or None
    rol = request.form["rol"]

    cursor = conexion.cursor()
    cursor.execute(
        """
        INSERT INTO usuarios(nombre, uid_rfid, rol)
        VALUES(%s,%s,%s)
        """,
        (nombre, uid, rol)
    )
    
    nuevo_usuario_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO auditoria(usuario_admin, accion)
        VALUES(%s,%s)
        """,
        (session["usuario"], f"Registró usuario {nombre}")
    )
    conexion.commit()

    flash(
    "Usuario registrado correctamente. Ahora registre la tarjeta RFID.",
    "success"
    )
    
    return redirect(f"/registrar_tarjeta?usuario_id={nuevo_usuario_id}")


@app.route("/editar_usuario/<int:id>")
def editar_usuario(id):
    """Muestra el formulario con los datos cargados de un usuario específico."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id=%s", (id,))
    usuario = cursor.fetchone()

    return render_template("editar_usuario.html", usuario=usuario)


@app.route("/actualizar_usuario", methods=["POST"])
def actualizar_usuario():
    """Guarda las modificaciones hechas a un usuario existente controlando duplicados de RFID."""
    if "usuario" not in session:
        return redirect("/")

    id_usuario = request.form["id"]
    nombre = request.form["nombre"]
    uid = request.form["uid"].strip() if request.form["uid"] else None
    rol = request.form["rol"]
    estado = int(request.form["estado"]) 

    # Si se limpia el UID, se fuerza el estado a 0 (Inactivo / Pendiente RFID)
    if not uid or uid == "" or uid == "—":
        uid = None
        estado = 0
        
    cursor = conexion.cursor()

    # 1. SI SE INGRESÓ UN UID, VERIFICAR QUE NO ESTÉ ASIGNADO A OTRO USUARIO
    if uid:
        cursor.execute(
            "SELECT id, nombre FROM usuarios WHERE uid_rfid = %s AND id != %s", 
            (uid, id_usuario)
        )
        tarjeta_duplicada = cursor.fetchone()
        
        if tarjeta_duplicada:
            # Si el UID ya lo tiene otra persona, mandamos advertencia limpia y recargamos la edición
            flash(f"La tarjeta RFID ya está asignada al usuario: {tarjeta_duplicada[1]} (ID: {tarjeta_duplicada[0]}).", "warning")
            cursor.close()
            return redirect("/usuarios")

    # 2. SI PASA LA VALIDACIÓN, PROCESAMOS EL UPDATE DE FORMA SEGURA
    try:
        cursor.execute(
            """
            UPDATE usuarios
            SET nombre=%s, uid_rfid=%s, rol=%s, estado=%s
            WHERE id=%s
            """, 
            (nombre, uid, rol, estado, id_usuario)
        ) 

        cursor.execute(
            """
            INSERT INTO auditoria(usuario_admin, accion)
            VALUES(%s,%s)
            """,
            (session["usuario"], f"Editó usuario {nombre} (Estado: {'Activo' if estado == 1 else 'Inactivo/Pendiente'})")
        )
        conexion.commit()
        flash("Usuario actualizado correctamente", "success")
        
    except mysql.connector.Error as err:
        conexion.rollback()
        flash(f"Error inesperado en la base de datos: {err}", "danger")
    finally:
        cursor.close()
        
    return redirect("/usuarios")


@app.route("/cambiar_estado/<int:id>")
def cambiar_estado(id):
    """Alterna el estado si tiene un UID, de lo contrario lo impide."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()
    
    # Verificar primero si el usuario cuenta con un UID asignado
    cursor.execute("SELECT uid_rfid FROM usuarios WHERE id = %s", (id,))
    res = cursor.fetchone()
    
    if not res or not res[0] or res[0].strip() == "":
        flash("No se puede activar un usuario que no tiene UID asignado.", "warning")
        return redirect("/usuarios")

    cursor.execute(
        """
        UPDATE usuarios
        SET estado = NOT estado
        WHERE id = %s
        """, 
        (id,)
    )
    
    cursor.execute(
        """
        INSERT INTO auditoria(usuario_admin, accion)
        VALUES(%s,%s)
        """,
        (session["usuario"], f"Cambió estado del usuario ID {id}")
    )
    conexion.commit()
    return redirect("/usuarios")

@app.route("/eliminar_usuario/<int:id>")
def eliminar_usuario(id):
    if "usuario" not in session:
        return redirect("/")
        
    cursor = conexion.cursor()
    try:
        # 1. OBTENER EL NOMBRE DEL USUARIO ANTES DE ELIMINARLO
        cursor.execute("SELECT nombre FROM usuarios WHERE id = %s", (id,))
        resultado = cursor.fetchone()
        
        # Si por alguna razón el usuario no existe, evitamos que falle
        nombre_usuario = resultado[0] if resultado else "Usuario Desconocido"
        
        # 2. MARCAR COMO ELIMINADO (estado = 2) Y LIBERAR LA TARJETA
        cursor.execute(
            """
            UPDATE usuarios 
            SET estado = 2, uid_rfid = NULL 
            WHERE id = %s
            """, 
            (id,)
        )
        
        # 3. GUARDAR EN AUDITORÍA CON EL NOMBRE REAL
        mensaje_auditoria = f"Eliminó al usuario: {nombre_usuario} (ID: {id})"
        cursor.execute(
            """
            INSERT INTO auditoria(usuario_admin, accion) 
            VALUES(%s, %s)
            """,
            (session["usuario"], mensaje_auditoria)
        )
        
        conexion.commit()
        flash(f"Usuario {nombre_usuario} eliminado de la lista correctamente.", "success")
    except mysql.connector.Error as err:
        conexion.rollback()
        flash(f"No se pudo ocultar al usuario: {err}", "danger")
    finally:
        cursor.close()
        
    return redirect("/usuarios")

# ==============================================================================
# MONITOREO E HISTORIALES
# ==============================================================================

@app.route("/historial")
def historial():
    """Muestra el registro cronológico de entradas permitidas y denegadas mapeando accesos web."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()
    try:
        # CONSULTA LIMPIA Y SEGURA:
        # 1. Si uid_rfid es 'WEB', vacio o NULL -> Muestra "Administrador".
        # 2. Si no es web, se apoya 100% en el LEFT JOIN por ID (El nombre nunca cambiará en el futuro).
        # 3. Si el usuario_id es NULL (ej. escaneo inicial de tarjeta nueva) -> Muestra "Tarjeta No Registrada".
        cursor.execute(
            """
            SELECT
                accesos.id,
                accesos.fecha_hora,
                accesos.uid_rfid,
                CASE 
                    WHEN accesos.uid_rfid = 'WEB' OR accesos.uid_rfid IS NULL OR accesos.uid_rfid = '' THEN 'Administrador'
                    ELSE IFNULL(usuarios.nombre, 'Tarjeta No Registrada')
                END AS nombre,
                accesos.estado_acceso
            FROM accesos
            LEFT JOIN usuarios ON accesos.usuario_id = usuarios.id
            ORDER BY accesos.id DESC
            """
        )
        datos = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error en consulta de historial: {err}")
        cursor.execute(
            """
            SELECT accesos.id, accesos.fecha_hora, accesos.uid_rfid, usuarios.nombre, accesos.estado_acceso
            FROM accesos LEFT JOIN usuarios ON accesos.usuario_id = usuarios.id ORDER BY accesos.id DESC
            """
        )
        datos = cursor.fetchall()
    finally:
        cursor.close()

    return render_template("historial.html", accesos=datos)

@app.route("/registrar_tarjeta")
def vista_registrar_tarjeta():
    if "usuario" not in session:
        return redirect("/")
        
    # Capturamos el usuario_id si viene desde la redirección de "guardar_usuario"
    # Convertimos a entero si existe para que coincida con el tipo de dato en Jinja (usuario[0])
    usuario_id_url = request.args.get("usuario_id")
    usuario_seleccionado = int(usuario_id_url) if usuario_id_url else None

    cursor = conexion.cursor()
    # Traemos todos los usuarios activos o pendientes para llenar el select
    cursor.execute("SELECT id, nombre FROM usuarios WHERE estado != 2 ORDER BY nombre ASC")
    datos_usuarios = cursor.fetchall()
    cursor.close()

    return render_template(
        "registrar_tarjeta.html", 
        usuarios=datos_usuarios, 
        usuario_seleccionado=usuario_seleccionado
    )

@app.route("/actualizar_rfid_usuario", methods=["POST"])
def actualizar_rfid_usuario():
    """Actualiza el UID RFID de un usuario evitando que el sistema colapse por duplicados."""
    if "usuario" not in session:
        return redirect("/")

    # 1. CAPTURA SEGURA DE DATOS DESDE EL FORMULARIO
    # Extraemos el ID del usuario y el UID enviado por el lector
    usuario_id = request.form.get("id")  # Asegúrate de que tu formulario HTML envíe el id del usuario elegido
    uid_raw = request.form.get("uid_rfid") or request.form.get("uid")  # Soporta ambos nombres por si acaso

    # Evitamos el error de 'NoneType' aplicando .strip() solo si existe contenido
    nuevo_uid = uid_raw.strip() if uid_raw else ""

    # Validación rápida por si envían el campo completamente vacío o con guiones
    if not nuevo_uid or nuevo_uid == "—" or nuevo_uid == "":
        flash("Error: El código de tarjeta no es válido o está vacío.", "registro_warning")
        return redirect("/registrar_tarjeta")

    estados_labels = ["Permitido", "Denegado", "Remoto"]
    estados_valores = [0, 0, 0]
    horas_labels = [f"{hora:02d}:00" for hora in range(24)]
    horas_valores = [0] * 24
    top_labels, top_valores = [], []
    fechas_30_dias = [date.today() - timedelta(days=desplazamiento) for desplazamiento in range(29, -1, -1)]
    dias_labels = [fecha.strftime("%d %b") for fecha in fechas_30_dias]
    dias_valores = [0] * 30

    cursor = conexion.cursor()

    try:
        # 2. VALIDACIÓN CRÍTICA: Verificar si la tarjeta ya la tiene OTRO usuario
        cursor.execute(
            """
            SELECT id, nombre 
            FROM usuarios 
            WHERE uid_rfid = %s AND id != %s
            """,
            (nuevo_uid, usuario_id)
        )
        usuario_existente = cursor.fetchone()

        if usuario_existente:
            # Si ya existe en otro id, enviamos la advertencia limpia y volvemos a la pestaña de registro
            flash(f"Advertencia: El UID ya está registrado a nombre de {usuario_existente[1]} (ID: {usuario_existente[0]}).", "registro_warning")
            return redirect("/registrar_tarjeta")

        # 3. PROCESO DE ACTUALIZACIÓN SEGURO (Cambiamos el UID y ponemos al usuario como Activo '1')
        cursor.execute(
            """
            UPDATE usuarios 
            SET uid_rfid = %s, estado = 1 
            WHERE id = %s
            """,
            (nuevo_uid, usuario_id)
        )
        
        # Guardamos la acción en la auditoría
        cursor.execute(
            """
            INSERT INTO auditoria(usuario_admin, accion)
            VALUES(%s, %s)
            """,
            (session["usuario"], f"Vinculó tarjeta RFID {nuevo_uid} al usuario ID {usuario_id}")
        )
        
        conexion.commit()
        flash("Tarjeta RFID vinculada correctamente al usuario.", "success")
        return redirect("/usuarios")  # Se queda en la misma pestaña mostrando el éxito limpio

    except mysql.connector.Error as err:
        conexion.rollback()
        flash(f"Ocurrió un error interno en la base de datos: {err}", "danger")
        return redirect("/registrar_tarjeta")
        
    finally:
        cursor.close()

@app.route("/limpiar_uid")
def limpiar_uid():
    """Limpia el buffer del último UID almacenado en memoria."""
    global ultimo_uid
    ultimo_uid = ""
    return jsonify({"ok": True})


@app.route("/auditoria")
def auditoria():
    """Muestra las acciones del sistema realizadas por los administradores."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM auditoria ORDER BY fecha DESC")
    registros = cursor.fetchall()

    return render_template("auditoria.html", registros=registros)


# ==============================================================================
# REPORTES GRÁFICOS Y ESTADÍSTICAS
# ==============================================================================

@app.route("/metricas")
def metricas_page():
    """Genera las métricas basadas en el diagrama real y renderiza los gráficos."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()

    try:
        # 1. Datos para gráfico de Rosca (Distribución de estados de acceso)
        cursor.execute(
            """
            SELECT estado_acceso, COUNT(*) 
            FROM accesos 
            GROUP BY estado_acceso
            """
        )
        datos_estados = cursor.fetchall()
        # Si el estado viene vacío o nulo, lo nombramos como 'Remoto / Otro'
        estados_labels = [row[0] if row[0] else "Remoto" for row in datos_estados]
        estados_valores = [row[1] for row in datos_estados]

        # 2. Datos para flujo por horas (Hoy por hora - ACTUALIZADO)
        cursor.execute(
            """
            SELECT HOUR(fecha_hora) AS hora, COUNT(*)
            FROM accesos
            WHERE DATE(fecha_hora) = CURDATE()
            GROUP BY HOUR(fecha_hora)
            ORDER BY hora ASC
            """
        )
        datos_horas = cursor.fetchall()
        horas_labels = [f"{row[0]}:00" for row in datos_horas]
        horas_valores = [row[1] for row in datos_horas]

        # 3. Top 5 usuarios con más accesos válidos
        cursor.execute(
            """
            SELECT usuarios.nombre, COUNT(accesos.id) as total
            FROM accesos
            INNER JOIN usuarios ON accesos.usuario_id = usuarios.id
            WHERE accesos.usuario_id IS NOT NULL
            GROUP BY usuarios.id, usuarios.nombre
            ORDER BY total DESC
            LIMIT 5
            """
        )
        datos_top = cursor.fetchall()
        top_labels = [row[0] for row in datos_top]
        top_valores = [row[1] for row in datos_top]

        # 4. Datos para los últimos 30 días (NUEVO)
        cursor.execute(
            """
            SELECT DATE(fecha_hora) AS dia, COUNT(*)
            FROM accesos
            WHERE fecha_hora >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(fecha_hora)
            ORDER BY dia ASC
            """
        )
        datos_dias = cursor.fetchall()
        dias_labels = [str(row[0]) for row in datos_dias]
        dias_valores = [row[1] for row in datos_dias]

    except mysql.connector.Error as err:
        print(f"❌ Error crítico en las consultas de métricas: {err}")
        # Inicializadores vacíos de respaldo para evitar que la página caiga en error 500
        estados_labels, estados_valores = [], []
        horas_labels, horas_valores = [], []
        top_labels, top_valores = [], []
        dias_labels, dias_valores = [], []

    return render_template(
        "metricas.html",
        estados_labels=estados_labels,
        estados_valores=estados_valores,
        horas_labels=horas_labels,
        horas_valores=horas_valores,
        top_labels=top_labels,
        top_valores=top_valores,
        dias_labels=dias_labels,
        dias_valores=dias_valores
    )
# ==============================================================================
# CONTROL DE PUERTA DESDE FRONTEND (WEB INTERFACE) - ARQUITECTURA PRO
# ==============================================================================

@app.route("/abrir_puerta", methods=["GET", "POST"])
def abrir_puerta_web():
    """Envía la orden de apertura manual desde la interfaz Web cambiando el comando global."""
    global orden_puerta
    
    if "usuario" not in session:
        if request.method == "POST":
            return jsonify({"error": "No autorizado"}), 401
        return redirect("/")

    # Definir el comando estructurado
    orden_puerta = {"accion": "abrir"}

    # Notificar a la web por Sockets en tiempo real
    socketio.emit("puerta", orden_puerta)

    cursor = conexion.cursor()
    cursor.execute(
        """
        INSERT INTO auditoria(usuario_admin, accion)
        VALUES(%s,%s)
        """,
        (session["usuario"], "Apertura remota de puerta")
    )

    cursor.execute(
        """
        INSERT INTO accesos(usuario_id, uid_rfid, estado_acceso)
        VALUES(%s,%s,%s)
        """,
        (None, "WEB", "Remoto")
    )
    conexion.commit()

    if request.method == "POST":
        return jsonify({"ok": True})
        
    flash("Orden de apertura enviada correctamente", "success")
    return redirect("/dashboard")


@app.route('/cerrar_puerta', methods=['POST'])
def cerrar_puerta():
    """Permite enviar una orden explícita de bloqueo al canal socket y al hardware."""
    global orden_puerta
    if "usuario" not in session:
        return jsonify({"error": "No autorizado"}), 401

    orden_puerta = {"accion": "cerrar"}
    socketio.emit("puerta", orden_puerta)
    return jsonify({"ok": True})


# ==============================================================================
# API ENDPOINTS (PROCESOS INTERNOS / HARDWARE ESP32)
# ==============================================================================

@app.route("/estado_puerta", methods=["GET"])
def verificar_orden_apertura():
    """Endpoint de polling consultado por el ESP32 con limpieza automática y protección anti-loop."""
    global orden_puerta, ultima_orden_enviada

    # Si no hay ninguna orden nueva programada, le decimos que no haga nada
    if orden_puerta["accion"] is None:
        return jsonify({"accion": "ninguna"})

    # Si hay una orden de abrir
    if orden_puerta["accion"] == "abrir":
        respuesta = orden_puerta
        
        # 🔥 EL FIX: Consumimos la orden en ambas variables para dejar el sistema limpio
        orden_puerta = {"accion": None}  
        ultima_orden_enviada = {"accion": None} # Al limpiar esto, la siguiente pulsación web será totalmente nueva
        
        return jsonify(respuesta)

    return jsonify({"accion": "ninguna"})


@app.route("/obtener_estado_puerta")
def obtener_estado_puerta():
    """Retorna el estado de seguridad actual del cerrojo (Bloqueada/Desbloqueada)."""
    global estado_puerta_hardware
    return jsonify({"estado": estado_puerta_hardware})


@app.route("/validar", methods=["POST"])
def validar():
    """API para que la lectora física verifique accesos de credenciales RFID."""
    datos = request.get_json()
    uid = datos.get("uid")

    cursor = conexion.cursor()
    
    # 1. Intentamos buscar un usuario activo con esa tarjeta
    cursor.execute(
        "SELECT id, nombre FROM usuarios WHERE uid_rfid=%s AND estado=1",
        (uid,)
    )
    usuario = cursor.fetchone()

    autorizado = False

    if usuario:
        usuario_id = usuario[0]
        autorizado = True
        cursor.execute(
            """
            INSERT INTO accesos(usuario_id, uid_rfid, estado_acceso)
            VALUES (%s,%s,%s)
            """,
            (usuario_id, uid, "Permitido")
        )
        conexion.commit()
        
        # 👉 emitir validación al frontend en tiempo real
        socketio.emit("validacion", {"uid": uid, "autorizado": autorizado, "usuario": usuario[1]})
        
        return jsonify({
            "estado": "permitido",
            "usuario": usuario[1]
        })
    else:
        # 2. CASO DENEGADO: Antes de poner NULL, buscamos si la tarjeta le pertenecía a alguien 
        # (Incluso usuarios inactivos o eliminados para conservar su historial original)
        cursor.execute(
            "SELECT id, nombre FROM usuarios WHERE uid_rfid=%s LIMIT 1",
            (uid,)
        )
        usuario_dueno = cursor.fetchone()
        
        # Si tenía dueño (ej. Maria Chris antes de borrarle el UID), guardamos su ID. 
        # Si es nueva (ej. Jessica registrándola), guardará None (Tarjeta No Registrada).
        usuario_id_guardar = usuario_dueno[0] if usuario_dueno else None
        nombre_pantalla = usuario_dueno[1] if usuario_dueno else "Tarjeta No Registrada"

        cursor.execute(
            """
            INSERT INTO accesos(usuario_id, uid_rfid, estado_acceso)
            VALUES (%s,%s,%s)
            """,
            (usuario_id_guardar, uid, "Denegado")
        )
        conexion.commit()
        
        # 👉 emitir validación denegada al frontend en tiempo real enviando el nombre si existe
        socketio.emit("validacion", {"uid": uid, "autorizado": autorizado, "usuario": nombre_pantalla})
        
        return jsonify({"estado": "denegado"})


@app.route("/capturar_uid", methods=["POST"])
def capturar_uid():
    """API que recibe lecturas brutas del sensor con Debounce Anti-Duplicados."""
    global ultimo_uid, ultimo_tiempo_uid

    datos = request.get_json()
    uid = datos.get("uid", "")

    ahora = time.time()

    # 🔥 Debounce anti duplicados (Evita capturas fantasmas en ráfaga dentro de 3 segundos)
    if uid == ultimo_uid and (ahora - ultimo_tiempo_uid) < 3:
        return jsonify({"ok": True, "duplicate": True})

    ultimo_uid = uid
    ultimo_tiempo_uid = telemetry = ahora

    print("UID recibido:", uid)

    # 👉 Emitir a frontend en tiempo real vía WebSockets
    socketio.emit("rfid_detectado", {"uid": uid})

    return jsonify({"ok": True})


@app.route("/actualizar_estado_puerta", methods=["POST"])
def actualizar_estado_puerta():
    """Recibe la retroalimentación física (FEEDBACK) de la puerta desde el hardware."""
    global estado_puerta_hardware
    datos = request.get_json()
    estado_puerta_hardware = datos.get("estado")
    
    # EMITIR EVENTO EN TIEMPO REAL: Envía el estado ("Desbloqueada"/"Bloqueada") al navegador
    socketio.emit('cambio_puerta', {'estado': estado_puerta_hardware})
    
    return jsonify({"ok": True})


@app.route("/obtener_uid")
def obtener_uid():
    """API utilizada por la interfaz del panel para capturar el UID en el registro."""
    global ultimo_uid
    return jsonify({"uid": ultimo_uid})


# ==============================================================================
# SOCKET CONNECT
# ==============================================================================

@socketio.on('connect')  # ✅ Corregido para usar la instancia de SocketIO
def connect():
    print("Cliente conectado a Socket.IO")

# ==============================================================================
# INICIO DE LA APLICACIÓN
# ==============================================================================

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
