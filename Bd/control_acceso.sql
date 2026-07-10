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