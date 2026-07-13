-- ==========================================
-- Base de datos: Sistema de Control de Acceso
-- ==========================================

CREATE DATABASE IF NOT EXISTS control_acceso;
USE control_acceso;

-- ==========================================
-- Tabla: administradores
-- ==========================================

CREATE TABLE administradores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- ==========================================
-- Tabla: usuarios
-- ==========================================

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    uid_rfid VARCHAR(50) NOT NULL UNIQUE,
    rol VARCHAR(50) NOT NULL,
    estado TINYINT(1) NOT NULL DEFAULT 1
);

-- ==========================================
-- Tabla: accesos
-- ==========================================

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

-- ==========================================
-- Tabla: auditoria
-- ==========================================

CREATE TABLE auditoria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_admin VARCHAR(50) NOT NULL,
    accion VARCHAR(100) NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO administradores (usuario, password) 
VALUES ('admin', 'scrypt:32768:8:1$pSkP7KU5vZp0eYqK$8a32bb889e072942a555df1cb53b7e9ae1d43b081d576592d05eabcc39d25ded587c52cd6e8e065411aa303301f7ac34366cd45fab386ba91eac7874ed830906');