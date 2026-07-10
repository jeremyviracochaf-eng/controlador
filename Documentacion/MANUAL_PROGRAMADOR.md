# Manual del Programador

## Sistema de Control de Acceso RFID

Este documento describe la estructura tecnica del sistema de control de acceso RFID desarrollado con Flask, MySQL y comunicacion con hardware programado desde Arduino IDE. El objetivo del manual es facilitar el mantenimiento, instalacion, pruebas y futuras mejoras del proyecto.

## 1. Descripcion general

El sistema permite administrar usuarios, registrar tarjetas RFID, validar accesos, abrir una puerta desde la interfaz web y guardar auditoria de acciones administrativas. La aplicacion web funciona como servidor central y expone endpoints HTTP que pueden ser consumidos por un ESP32, ESP8266 u otro microcontrolador programado en Arduino IDE.

Componentes principales:

- Backend: aplicacion Flask ubicada en `Backend/app.py`.
- Frontend: plantillas HTML Jinja ubicadas en `Frontend/templates`.
- Estilos y scripts: archivos estaticos en `Frontend/static`.
- Base de datos: MySQL administrada desde MySQL Workbench.
- Hardware: lector RFID y cerradura/relay controlados desde Arduino IDE.

## 2. Estructura del proyecto

```text
controlador/
|-- Backend/
|   |-- app.py
|-- Frontend/
|   |-- static/
|   |   |-- script.js
|   |   |-- styles.css
|   |-- templates/
|       |-- auditoria.html
|       |-- editar_usuario.html
|       |-- historial.html
|       |-- index.html
|       |-- login.html
|       |-- metricas.html
|       |-- nuevo_usuario.html
|       |-- registrar_tarjeta.html
|       |-- usuarios.html
|-- requirements.txt
|-- Bd/
|   |-- control_acceso.sql
|-- Documentacion/
    |-- MANUAL_PROGRAMADOR.md
```

## 3. Tecnologias utilizadas

- Python 3.x
- Flask
- Flask-SocketIO
- MySQL Server
- MySQL Workbench
- mysql-connector-python
- python-dotenv
- HTML, CSS y JavaScript
- Chart.js mediante CDN
- Font Awesome mediante CDN
- Socket.IO cliente mediante CDN
- Arduino IDE para el firmware del microcontrolador

## 4. Dependencias Python

El archivo `requirements.txt` recomendado para este proyecto es:

```txt
Flask==2.3.3
Flask-SocketIO==5.6.1
mysql-connector-python==9.7.0
python-dotenv==1.2.1
Werkzeug==3.1.6
simple-websocket==1.1.0
```

Instalacion:

```bash
pip install -r requirements.txt
```

## 5. Configuracion del entorno

El backend carga variables de entorno con `python-dotenv`. Se debe crear un archivo `.env` en la raiz del proyecto o en el directorio desde donde se ejecuta la aplicacion.

Ejemplo:

```env
SECRET_KEY=clave_secreta_para_sesiones
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=tu_password_mysql
DB_DATABASE=nombre_base_datos
```

Variables usadas por `Backend/app.py`:

- `SECRET_KEY`: clave para cifrar la sesion Flask.
- `DB_HOST`: servidor MySQL.
- `DB_USER`: usuario MySQL.
- `DB_PASSWORD`: contrasena MySQL.
- `DB_DATABASE`: nombre de la base de datos.

## 6. Ejecucion del sistema

Desde la raiz del proyecto:

```bash
python Backend/app.py
```

La aplicacion se ejecuta en:

```text
http://localhost:5000
```

El servidor queda disponible tambien en la red local porque se usa:

```python
socketio.run(app, host="0.0.0.0", port=5000, debug=True)
```

Para conectar el microcontrolador, usar la IP local del equipo servidor, por ejemplo:

```text
http://192.168.1.50:5000
```

## 7. Base de datos MySQL

El codigo utiliza cuatro tablas principales:

- `administradores`
- `usuarios`
- `accesos`
- `auditoria`

El script de base de datos del proyecto se encuentra en:

```text
Bd/control_acceso.sql
```

La base definida en el script se llama:

```sql
control_acceso
```

El archivo crea las tablas necesarias para administradores, usuarios, accesos y auditoria.

### Tabla `administradores`

Uso: autenticar administradores.

Estructura del script:

```sql
CREATE TABLE administradores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);
```

Notas:

- El login consulta `SELECT * FROM administradores WHERE BINARY usuario = %s`.
- La contrasena se valida con `check_password_hash(admin[2], password)`.
- Por eso el campo `password` debe guardar un hash generado con Werkzeug, no texto plano.

### Tabla `usuarios`

Uso: almacenar personas autorizadas o pendientes de tarjeta RFID.

Estructura del script:

```sql
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    uid_rfid VARCHAR(50) NOT NULL UNIQUE,
    rol VARCHAR(50) NOT NULL,
    estado TINYINT(1) NOT NULL DEFAULT 1
);
```

Estados usados por el sistema:

- `0`: inactivo o pendiente de tarjeta.
- `1`: activo.
- `2`: eliminado logicamente.

Nota de compatibilidad con el backend:

- En `Backend/app.py`, al crear un usuario nuevo se permite guardar `uid_rfid` como `NULL` hasta registrar la tarjeta.
- Por eso, para que el flujo de "crear usuario y luego registrar tarjeta" funcione correctamente, conviene permitir `NULL` en `uid_rfid`.
- Version recomendada para el proyecto actual:

```sql
uid_rfid VARCHAR(50) NULL UNIQUE
```

### Tabla `accesos`

Uso: historial de accesos permitidos, denegados y aperturas remotas.

Estructura del script:

```sql
CREATE TABLE accesos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estado_acceso VARCHAR(20) NOT NULL,
    uid_rfid VARCHAR(50) NOT NULL,

    CONSTRAINT fk_usuario
        FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);
```

Valores usados en `estado_acceso`:

- `Permitido`
- `Denegado`
- `Remoto`

Nota de compatibilidad con el backend:

- El backend registra aperturas remotas con `usuario_id = NULL` y `uid_rfid = 'WEB'`.
- Tambien puede registrar accesos denegados de tarjetas no registradas con `usuario_id = NULL`.
- Por eso, para que no falle la insercion de accesos remotos o denegados, conviene permitir `NULL` en `usuario_id`.
- Version recomendada para el proyecto actual:

```sql
usuario_id INT NULL
```

Tambien se recomienda que la llave foranea use `ON DELETE SET NULL` si se desea conservar el historial cuando se elimine un usuario fisicamente. En este proyecto se usa eliminacion logica con `estado = 2`, por lo que no es obligatorio borrar usuarios de la tabla.

### Tabla `auditoria`

Uso: registrar acciones realizadas por administradores.

Estructura del script:

```sql
CREATE TABLE auditoria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_admin VARCHAR(50) NOT NULL,
    accion VARCHAR(100) NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Ajuste SQL recomendado para compatibilidad

Si la base ya fue creada desde `Bd/control_acceso.sql`, ejecutar en MySQL Workbench:

```sql
USE control_acceso;

ALTER TABLE usuarios
MODIFY uid_rfid VARCHAR(50) NULL UNIQUE;

ALTER TABLE accesos
DROP FOREIGN KEY fk_usuario;

ALTER TABLE accesos
MODIFY usuario_id INT NULL;

ALTER TABLE accesos
ADD CONSTRAINT fk_usuario
FOREIGN KEY (usuario_id)
REFERENCES usuarios(id)
ON UPDATE CASCADE
ON DELETE SET NULL;
```

Con este ajuste se mantiene el historial de accesos y se permite registrar usuarios antes de vincular una tarjeta RFID.

## 8. Crear administrador inicial

Las contrasenas deben guardarse con hash. Ejemplo para generar hash:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123'))"
```

Luego insertar en MySQL Workbench:

```sql
INSERT INTO administradores(usuario, password)
VALUES ('admin', 'HASH_GENERADO_AQUI');
```

## 9. Backend Flask

Archivo principal:

```text
Backend/app.py
```

Responsabilidades:

- Configurar Flask y Socket.IO.
- Conectar con MySQL.
- Controlar login y logout.
- Renderizar pantallas administrativas.
- Registrar usuarios y tarjetas.
- Validar UID RFID enviados por el hardware.
- Guardar historial de accesos.
- Emitir eventos en tiempo real al frontend.
- Recibir y publicar estado de puerta.

Variables globales importantes:

```python
orden_puerta = {"accion": None}
ultima_orden_enviada = {"accion": None}
estado_puerta_hardware = "Bloqueada"
ultimo_uid = ""
ultimo_tiempo_uid = 0
```

Estas variables guardan el estado temporal usado entre la web y el hardware. Si el servidor se reinicia, estos valores vuelven a su estado inicial.

## 10. Rutas web administrativas

| Ruta | Metodo | Descripcion |
|---|---|---|
| `/` | GET | Muestra login o redirige al dashboard si hay sesion |
| `/login` | POST | Valida credenciales del administrador |
| `/logout` | GET | Cierra sesion |
| `/dashboard` | GET | Panel principal con contadores y ultimo acceso |
| `/usuarios` | GET | Lista usuarios no eliminados |
| `/nuevo_usuario` | GET | Formulario de nuevo usuario |
| `/guardar_usuario` | POST | Guarda usuario y redirige a registrar tarjeta |
| `/editar_usuario/<id>` | GET | Formulario para editar usuario |
| `/actualizar_usuario` | POST | Actualiza datos de usuario |
| `/cambiar_estado/<id>` | GET | Activa o desactiva usuario |
| `/eliminar_usuario/<id>` | GET | Eliminacion logica del usuario |
| `/historial` | GET | Historial de accesos |
| `/registrar_tarjeta` | GET | Pantalla para vincular tarjeta RFID |
| `/actualizar_rfid_usuario` | POST | Asigna UID a un usuario |
| `/auditoria` | GET | Lista acciones administrativas |
| `/metricas` | GET | Reportes graficos |
| `/abrir_puerta` | GET/POST | Orden de apertura remota |
| `/cerrar_puerta` | POST | Orden de cierre remoto |

## 11. Endpoints para Arduino / hardware

Estos endpoints son los mas importantes para el firmware en Arduino IDE.

### Validar tarjeta RFID

```http
POST /validar
Content-Type: application/json

{
  "uid": "UID_DE_LA_TARJETA"
}
```

Respuesta permitida:

```json
{
  "estado": "permitido",
  "usuario": "Nombre del usuario"
}
```

Respuesta denegada:

```json
{
  "estado": "denegado"
}
```

Uso esperado en Arduino:

- Leer UID desde el modulo RFID.
- Enviar UID a `/validar`.
- Si la respuesta es `permitido`, activar relay o cerradura.
- Si la respuesta es `denegado`, no abrir y opcionalmente activar alerta.

### Capturar UID para registro

```http
POST /capturar_uid
Content-Type: application/json

{
  "uid": "UID_DE_LA_TARJETA"
}
```

Respuesta:

```json
{
  "ok": true
}
```

Si se repite el mismo UID en menos de 3 segundos:

```json
{
  "ok": true,
  "duplicate": true
}
```

Uso esperado:

- Durante el registro de tarjeta, el microcontrolador envia el UID detectado.
- La web recibe el evento `rfid_detectado` por Socket.IO y llena el campo UID.

### Obtener ultimo UID

```http
GET /obtener_uid
```

Respuesta:

```json
{
  "uid": "UID_DE_LA_TARJETA"
}
```

### Limpiar UID temporal

```http
GET /limpiar_uid
```

Respuesta:

```json
{
  "ok": true
}
```

### Consultar orden de puerta

```http
GET /estado_puerta
```

Respuesta sin orden:

```json
{
  "accion": "ninguna"
}
```

Respuesta con apertura:

```json
{
  "accion": "abrir"
}
```

Uso esperado:

- El microcontrolador consulta periodicamente `/estado_puerta`.
- Si recibe `abrir`, activa el mecanismo de apertura.
- Luego el servidor consume la orden y vuelve a `ninguna`.

### Reportar estado fisico de puerta

```http
POST /actualizar_estado_puerta
Content-Type: application/json

{
  "estado": "Bloqueada"
}
```

o:

```json
{
  "estado": "Desbloqueada"
}
```

Respuesta:

```json
{
  "ok": true
}
```

Uso esperado:

- El hardware informa si la puerta esta bloqueada o desbloqueada.
- El dashboard recibe el cambio por Socket.IO con el evento `cambio_puerta`.

## 12. Eventos Socket.IO

El servidor emite eventos para actualizar la interfaz en tiempo real.

| Evento | Emisor | Receptor | Descripcion |
|---|---|---|---|
| `rfid_detectado` | Backend | Frontend | Notifica UID capturado |
| `validacion` | Backend | Frontend | Informa si un acceso fue autorizado |
| `puerta` | Backend | Frontend | Informa orden de apertura/cierre |
| `cambio_puerta` | Backend | Frontend | Actualiza estado fisico de la puerta |

## 13. Flujo de registro de usuario y tarjeta

1. El administrador inicia sesion.
2. Entra a `Usuarios`.
3. Crea un nuevo usuario desde `/nuevo_usuario`.
4. El backend guarda nombre y rol en `usuarios`.
5. El sistema redirige a `/registrar_tarjeta?usuario_id=ID`.
6. El lector RFID envia el UID por `/capturar_uid`.
7. La pantalla de registro recibe el UID por Socket.IO.
8. El administrador confirma la vinculacion.
9. El backend actualiza `usuarios.uid_rfid` y cambia `estado` a `1`.
10. Se registra la accion en `auditoria`.

## 14. Flujo de acceso fisico RFID

1. El usuario acerca la tarjeta al lector RFID.
2. El microcontrolador lee el UID.
3. El microcontrolador envia `POST /validar`.
4. El backend busca un usuario activo con ese UID.
5. Si existe, registra acceso `Permitido`.
6. Si no existe, registra acceso `Denegado`.
7. El backend emite evento `validacion`.
8. El microcontrolador abre o niega el acceso segun la respuesta.

## 15. Flujo de apertura remota

1. El administrador pulsa abrir puerta desde la web.
2. Flask ejecuta `/abrir_puerta`.
3. Se asigna `orden_puerta = {"accion": "abrir"}`.
4. Se registra auditoria.
5. Se inserta un acceso con `uid_rfid = 'WEB'` y `estado_acceso = 'Remoto'`.
6. El microcontrolador consulta `/estado_puerta`.
7. Si recibe `abrir`, activa la cerradura o relay.
8. La orden queda consumida y vuelve a `ninguna`.

## 16. Frontend

Las pantallas usan plantillas Jinja:

- `login.html`: inicio de sesion.
- `index.html`: dashboard.
- `usuarios.html`: listado de usuarios.
- `nuevo_usuario.html`: creacion de usuarios.
- `editar_usuario.html`: edicion de usuarios.
- `registrar_tarjeta.html`: vinculacion RFID.
- `historial.html`: registros de acceso.
- `auditoria.html`: acciones administrativas.
- `metricas.html`: graficos y estadisticas.

Archivos estaticos:

- `styles.css`: estilos globales.
- `script.js`: funciones compartidas de interfaz.

CDN usados:

- Font Awesome para iconos.
- Chart.js para graficos.
- Socket.IO cliente para tiempo real.

## 17. Consideraciones para Arduino IDE

El sistema usa un ESP32 programado desde Arduino IDE. El sketch proporcionado integra WiFi, peticiones HTTP, lector RFID MFRC522 y control de relay para la cerradura.

### Librerias usadas en Arduino

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>
```

Dependencias:

- `WiFi.h`: conexion del ESP32 a la red WiFi.
- `HTTPClient.h`: consumo de endpoints Flask.
- `SPI.h`: comunicacion SPI con el lector RFID.
- `MFRC522.h`: manejo del modulo RFID RC522.

### Pines configurados

```cpp
#define SS_PIN 21
#define RST_PIN 22
#define RELAY_PIN 4
```

Conexion SPI inicializada:

```cpp
SPI.begin(18, 19, 23, 21);
```

Distribucion usada:

| Componente | Pin ESP32 |
|---|---|
| RFID SS/SDA | GPIO 21 |
| RFID RST | GPIO 22 |
| SPI SCK | GPIO 18 |
| SPI MISO | GPIO 19 |
| SPI MOSI | GPIO 23 |
| Relay | GPIO 4 |

### Configuracion WiFi

El sketch tiene configurada la red:

```cpp
const char* ssid = "Prueba";
const char* password = "12345678";
```

Para otro entorno, cambiar `ssid` y `password` por los datos reales de la red.

### URLs del servidor Flask

El sketch apunta a la IP:

```text
10.59.41.48:5000
```

Endpoints usados:

```cpp
const char* validarURL = "http://10.59.41.48:5000/validar";
const char* estadoURL  = "http://10.59.41.48:5000/estado_puerta";
const char* capturaURL = "http://10.59.41.48:5000/capturar_uid";
const char* actualizarEstadoURL = "http://10.59.41.48:5000/actualizar_estado_puerta";
```

Si cambia la IP del computador donde corre Flask, se deben actualizar estas cuatro rutas.

### Funciones principales del sketch

| Funcion | Responsabilidad |
|---|---|
| `conectarWiFi()` | Conecta el ESP32 a la red WiFi |
| `httpPOST(url, json)` | Envia datos JSON al servidor Flask |
| `httpGET(url)` | Consulta rutas GET del servidor Flask |
| `abrirPuerta()` | Activa el relay, informa estado desbloqueado, espera 3 segundos y vuelve a bloquear |
| `leerRFID(uidOut)` | Lee la tarjeta RFID y devuelve el UID en mayusculas |
| `loop()` | Coordina lectura RFID, validacion, captura y polling de apertura remota |

### Formato del UID

El UID se arma byte por byte en hexadecimal, separado por espacios y convertido a mayusculas:

```cpp
uid += String(rfid.uid.uidByte[i], HEX);
uid.toUpperCase();
```

Ejemplo de UID enviado:

```text
04 A1 B2 C3
```

El mismo formato debe quedar guardado en `usuarios.uid_rfid` para que la validacion coincida.

### Flujo del sketch Arduino

1. El ESP32 inicia puerto serial a `115200`.
2. Configura `RELAY_PIN` en estado seguro `HIGH`.
3. Inicializa SPI y el lector MFRC522.
4. Se conecta a la red WiFi.
5. En cada ciclo del `loop()` intenta leer una tarjeta RFID.
6. Si detecta una tarjeta nueva:
   - Envia el UID a `/capturar_uid`.
   - Envia el UID a `/validar`.
   - Si la respuesta contiene `permitido`, ejecuta `abrirPuerta()`.
7. Cada segundo consulta `/estado_puerta`.
8. Si recibe una orden con texto `abrir`, ejecuta `abrirPuerta()`.
9. Al abrir la puerta:
   - Activa relay con `LOW`.
   - Reporta `Desbloqueada`.
   - Espera 3 segundos.
   - Desactiva relay con `HIGH`.
   - Reporta `Bloqueada`.

### Control anti-repeticion

El sketch usa estas variables:

```cpp
bool enviado = false;
bool processing = false;
```

Esto evita enviar multiples validaciones mientras la misma tarjeta permanece sobre el lector. Cuando la tarjeta se retira, `enviado` vuelve a `false` y el sistema queda listo para otra lectura.

### Relay y estado seguro

El relay se maneja asi:

```cpp
digitalWrite(RELAY_PIN, HIGH); // Estado inicial seguro
digitalWrite(RELAY_PIN, LOW);  // Activa apertura
digitalWrite(RELAY_PIN, HIGH); // Bloquea nuevamente
```

Esto indica que el modulo relay usado es activo en bajo. Si se cambia por un relay activo en alto, se debe invertir la logica.

### Requisitos minimos del codigo Arduino

El codigo Arduino debe tener como minimo:

- Conexion WiFi al mismo segmento de red que el servidor Flask.
- Lectura del UID del modulo RFID.
- Envio HTTP POST a `/validar`.
- Envio HTTP POST a `/capturar_uid` durante registro.
- Consulta periodica GET a `/estado_puerta`.
- Envio HTTP POST a `/actualizar_estado_puerta`.
- Control de relay, cerradura o servo segun la respuesta del servidor.

Ejemplo generico de URLs usando IP local:

```text
http://192.168.1.50:5000/validar
http://192.168.1.50:5000/capturar_uid
http://192.168.1.50:5000/estado_puerta
http://192.168.1.50:5000/actualizar_estado_puerta
```

En el sketch actual la IP configurada es `10.59.41.48`.

### Recomendaciones para el firmware

- Mantener el ESP32 y el servidor Flask en la misma red.
- Verificar la IP del servidor antes de cargar el sketch.
- Usar monitor serial a `115200` para diagnosticar lecturas y respuestas HTTP.
- Confirmar si el relay es activo en bajo o activo en alto.
- Evitar reducir demasiado el polling de `/estado_puerta`; actualmente consulta cada 1000 ms.
- Si la red cambia con frecuencia, considerar guardar IP, SSID y password en constantes faciles de modificar.

## 18. Pruebas recomendadas

### Pruebas web

- Login con usuario correcto.
- Login con usuario incorrecto.
- Crear usuario.
- Editar usuario.
- Activar/desactivar usuario.
- Eliminar usuario logicamente.
- Registrar tarjeta.
- Abrir puerta desde dashboard.
- Revisar historial.
- Revisar auditoria.
- Revisar metricas.

### Pruebas hardware

- Enviar UID registrado y activo: debe responder `permitido`.
- Enviar UID no registrado: debe responder `denegado`.
- Enviar UID de usuario inactivo: debe responder `denegado`.
- Probar apertura remota desde la web.
- Probar reporte de estado `Bloqueada` y `Desbloqueada`.

### Pruebas con curl

```bash
curl -X POST http://localhost:5000/validar ^
  -H "Content-Type: application/json" ^
  -d "{\"uid\":\"ABC123\"}"
```

```bash
curl -X POST http://localhost:5000/capturar_uid ^
  -H "Content-Type: application/json" ^
  -d "{\"uid\":\"ABC123\"}"
```

```bash
curl http://localhost:5000/estado_puerta
```

## 19. Recomendaciones de mantenimiento

- No guardar contrasenas en texto plano.
- Mantener el archivo `.env` fuera de entregas publicas.
- Respaldar la base MySQL desde Workbench antes de cambios importantes.
- Cerrar cursores despues de consultas para evitar consumo innecesario.
- Evitar que el microcontrolador haga demasiadas peticiones por segundo.
- Revisar que la IP configurada en Arduino coincida con la IP del servidor.
- Desactivar `debug=True` en produccion.
- Mantener nombres exactos de estados: `Permitido`, `Denegado`, `Remoto`.

## 20. Observaciones tecnicas del codigo actual

Durante la revision se encontraron puntos menores que pueden mejorarse:

- En algunas rutas se crean cursores que no se cierran explicitamente.
- En `capturar_uid` aparece `ultimo_tiempo_uid = telemetry = ahora`; `telemetry` no se usa.
- El proyecto ya incluye el script `Bd/control_acceso.sql`; revisar la nota de compatibilidad porque el backend necesita permitir `NULL` en algunos campos.
- El codigo Arduino proporcionado esta documentado en la seccion de Arduino IDE; si se guarda como archivo `.ino`, conviene agregarlo a una carpeta propia del proyecto.
- Algunas cadenas muestran caracteres con codificacion incorrecta en comentarios o textos antiguos. Conviene guardar archivos como UTF-8.

## 21. Archivos importantes para modificar

- Cambios de rutas o API: `Backend/app.py`.
- Cambios visuales generales: `Frontend/static/styles.css`.
- Cambios de comportamiento frontend: `Frontend/static/script.js`.
- Cambios de pantallas: `Frontend/templates/*.html`.
- Cambios de dependencias: `requirements.txt`.
- Cambios de base de datos: MySQL Workbench o script `.sql`.
- Cambios de hardware: sketch en Arduino IDE.

## 22. Glosario

- RFID: tecnologia de identificacion por radiofrecuencia.
- UID: identificador unico leido desde la tarjeta RFID.
- Backend: servidor que procesa reglas de negocio y base de datos.
- Frontend: interfaz web del administrador.
- Socket.IO: canal de comunicacion en tiempo real entre servidor y navegador.
- Endpoint: ruta HTTP consumida por navegador o hardware.
- Auditoria: registro de acciones administrativas.
- Eliminacion logica: marcar un registro como eliminado sin borrarlo fisicamente.
