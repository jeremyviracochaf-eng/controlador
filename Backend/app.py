from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    session,
    flash
)
import mysql.connector

from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

load_dotenv()
# CONFIGURACIÓN DE LA APLICACIÓN Y BD


app = Flask(
    __name__,
    template_folder="../Frontend/templates",
    static_folder="../Frontend"
)

abrir_puerta = False

app.secret_key = os.getenv("SECRET_KEY")

conexion = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_DATABASE")
)

ultimo_uid = ""

estado_puerta = "Bloqueada"



# VISTAS PÚBLICAS / ACCESO


@app.route("/")
def login_page():
    """Muestra la pantalla inicial de inicio de sesión."""
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    """Procesa las credenciales del administrador para iniciar sesión."""
    usuario = request.form["usuario"]
    password = request.form["password"]

    cursor = conexion.cursor()
    cursor.execute(
    """
    SELECT *
    FROM administradores
    WHERE usuario=%s
    """,
    (usuario,)
    )

    admin = cursor.fetchone()

    if admin and check_password_hash(admin[2], password):
        session["usuario"] = usuario

        cursor.execute("""
            INSERT INTO auditoria(usuario_admin, accion)
            VALUES(%s,%s)
        """,
        (
            usuario,
            "Inició sesión"
        ))
        
        conexion.commit()
        return redirect("/dashboard")

    return "Usuario o contraseña incorrectos"


@app.route("/logout")
def logout():

    if "usuario" in session:

        cursor = conexion.cursor()

        cursor.execute("""
        INSERT INTO auditoria(usuario_admin, accion)
        VALUES(%s,%s)
        """,
        (
            session["usuario"],
            "Cerró sesión"
        ))

        conexion.commit()

    session.pop("usuario", None)

    return redirect("/")



# PANEL PRINCIPAL (DASHBOARD)


@app.route("/dashboard")
def dashboard():
    """Muestra estadísticas generales del sistema (Solo administradores)."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()

    # Total usuarios
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cursor.fetchone()[0]

    # Accesos permitidos
    cursor.execute("""
        SELECT COUNT(*)
        FROM accesos
        WHERE estado_acceso='Permitido'
    """)
    permitidos = cursor.fetchone()[0]

    # Accesos denegados
    cursor.execute("""
        SELECT COUNT(*)
        FROM accesos
        WHERE estado_acceso='Denegado'
    """)
    denegados = cursor.fetchone()[0]

    cursor.execute("""
    SELECT fecha_hora, estado_acceso
    FROM accesos
    ORDER BY fecha_hora DESC
    LIMIT 1
    """)

    ultimo_acceso = cursor.fetchone()

    # Renderizado con todas las variables requeridas por index.html
    return render_template(
    "index.html",
    total_usuarios=total_usuarios,
    permitidos=permitidos,
    denegados=denegados,
    ultimo_acceso=ultimo_acceso
    )

# GESTIÓN DE USUARIOS (RUTAS ADMINISTRATIVAS)


@app.route("/usuarios")
def usuarios():
    """Lista todos los usuarios registrados."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM usuarios")
    datos = cursor.fetchall()

    return render_template(
        "usuarios.html",
        usuarios=datos
    )


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
    uid = request.form["uid"]
    rol = request.form["rol"]

    cursor = conexion.cursor()
    cursor.execute(
        """
        INSERT INTO usuarios(nombre, uid_rfid, rol)
        VALUES(%s,%s,%s)
        """,
        (nombre, uid, rol)
    )
    cursor.execute(
        """
        INSERT INTO auditoria(usuario_admin, accion)
        VALUES(%s,%s)
        """,
        (
            session["usuario"],
            f"Registró usuario {nombre}"
        )
    )
    conexion.commit()
    return redirect("/usuarios")


@app.route("/editar_usuario/<int:id>")
def editar_usuario(id):
    """Muestra el formulario con los datos cargados de un usuario específico."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()
    cursor.execute(
        "SELECT * FROM usuarios WHERE id=%s",
        (id,)
    )
    usuario = cursor.fetchone()

    return render_template(
        "editar_usuario.html",
        usuario=usuario
    )


@app.route("/actualizar_usuario", methods=["POST"])
def actualizar_usuario():
    """Guarda las modificaciones hechas a un usuario existente."""
    if "usuario" not in session:
        return redirect("/")

    id_usuario = request.form["id"]
    nombre = request.form["nombre"]
    uid = request.form["uid"]
    rol = request.form["rol"]

    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE usuarios
        SET nombre=%s,
            uid_rfid=%s,
            rol=%s
        WHERE id=%s
    """, (nombre, uid, rol, id_usuario)) 

    cursor.execute(
        """
        INSERT INTO auditoria(usuario_admin, accion)
        VALUES(%s,%s)
        """,
        (
            session["usuario"],
            f"Editó usuario {nombre}"
        )
    )
    
    conexion.commit()
    return redirect("/usuarios")


@app.route("/cambiar_estado/<int:id>")
def cambiar_estado(id):
    """Alterna el estado (Activo/Inactivo) de un usuario."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE usuarios
        SET estado = NOT estado
        WHERE id = %s
    """, (id,))
    
    cursor.execute("""
        INSERT INTO auditoria(usuario_admin, accion)
        VALUES(%s,%s)
    """,
    (
        session["usuario"],
        f"Cambió estado del usuario ID {id}"
    ))
    
    conexion.commit()
    return redirect("/usuarios")


# Monitoreo E Historiales

@app.route("/historial")
def historial():
    """Muestra el registro cronológico de entradas permitidas y denegadas."""
    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()
    cursor.execute("""
        SELECT
            accesos.id,
            accesos.fecha_hora,
            accesos.uid_rfid,
            usuarios.nombre,
            accesos.estado_acceso
        FROM accesos
        LEFT JOIN usuarios
        ON accesos.usuario_id = usuarios.id
        ORDER BY accesos.fecha_hora DESC
    """)
    datos = cursor.fetchall()

    return render_template(
        "historial.html",
        accesos=datos
    )

@app.route("/registrar_tarjeta")
def registrar_tarjeta():

    if "usuario" not in session:
        return redirect("/")

    return render_template("registrar_tarjeta.html")

@app.route("/limpiar_uid")
def limpiar_uid():

    global ultimo_uid

    ultimo_uid = ""

    return jsonify({"ok": True})

@app.route("/auditoria")
def auditoria():

    if "usuario" not in session:
        return redirect("/")

    cursor = conexion.cursor()

    cursor.execute("""
        SELECT *
        FROM auditoria
        ORDER BY fecha DESC
    """)

    registros = cursor.fetchall()

    return render_template(
        "auditoria.html",
        registros=registros
    )

@app.route("/abrir_puerta")
def abrir_puerta_web():

    global abrir_puerta

    if "usuario" not in session:
        return redirect("/")

    abrir_puerta = True

    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO auditoria(usuario_admin, accion)
        VALUES(%s,%s)
    """,
    (
        session["usuario"],
        "Apertura remota de puerta"
    ))

    cursor.execute("""
        INSERT INTO accesos(
            usuario_id,
            uid_rfid,
            estado_acceso
        )
        VALUES(%s,%s,%s)
    """,
    (
        None,
        "WEB",
        "Remoto"
    ))

    conexion.commit()

    flash(
        "Orden de apertura enviada correctamente",
        "success"
    )

    return redirect("/dashboard")

@app.route("/estado_puerta")
def estado_puerta():

    global abrir_puerta

    if abrir_puerta:

        abrir_puerta = False

        return jsonify({
            "accion": "abrir"
        })

    return jsonify({
        "accion": "ninguna"
    })

@app.route("/obtener_estado_puerta")
def obtener_estado_puerta():

    return jsonify({
        "estado": estado_puerta
    })


# API ENDPOINTS (PROCESOS INTERNOS / HARDWARE)

@app.route("/validar", methods=["POST"])
def validar():
    """API para que la lectora física verifique accesos (Pública/Hardware)."""
    datos = request.get_json()
    uid = datos.get("uid")

    cursor = conexion.cursor()
    cursor.execute(
        "SELECT id, nombre FROM usuarios WHERE uid_rfid=%s AND estado=1",
        (uid,)
    )
    usuario = cursor.fetchone()

    if usuario:
        usuario_id = usuario[0]
        cursor.execute(
            """
            INSERT INTO accesos(usuario_id, uid_rfid, estado_acceso)
            VALUES (%s,%s,%s)
            """,
            (usuario_id, uid, "Permitido")
        )
        conexion.commit()
        return jsonify({
            "estado": "permitido",
            "usuario": usuario[1]
        })
    else:
        cursor.execute(
            """
            INSERT INTO accesos(usuario_id, uid_rfid, estado_acceso)
            VALUES (%s,%s,%s)
            """,
            (None, uid, "Denegado")
        )
        conexion.commit()
        return jsonify({
            "estado": "denegado"
        })


@app.route("/capturar_uid", methods=["POST"])
def capturar_uid():
    """API que recibe las lecturas del sensor RFID en tiempo real."""
    global ultimo_uid
    datos = request.get_json()
    ultimo_uid = datos.get("uid")
    return jsonify({
        "mensaje": "UID recibido"
    })

@app.route("/actualizar_estado_puerta", methods=["POST"])
def actualizar_estado_puerta():

    global estado_puerta

    datos = request.get_json()

    estado_puerta = datos.get("estado")

    return jsonify({
        "ok": True
    })


@app.route("/obtener_uid")
def obtener_uid():
    """API utilizada por la interfaz para autocompletar tarjetas nuevas."""
    return jsonify({
        "uid": ultimo_uid
    })


# Inicio de la aplicación

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)