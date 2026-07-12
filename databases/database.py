"""
database.py — Gestión de la base de datos de placas robadas.
Usa SQLite (incluido en Python, sin instalación extra).
"""
import sqlite3
import difflib
import os
import sys
from datetime import datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "secure_placas.db"))


def obtener_conexion():
    """Retorna una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    return conn


def inicializar_db():
    """Crea las tablas si no existen e inserta datos de ejemplo."""
    conn = obtener_conexion()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS placas_robadas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            placa           TEXT NOT NULL UNIQUE,
            modelo          TEXT,
            color           TEXT,
            propietario     TEXT,
            fecha_reporte   TEXT,
            descripcion     TEXT,
            activo          INTEGER DEFAULT 1,
            fecha_creacion  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_alertas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            placa           TEXT NOT NULL,
            placa_detectada TEXT,
            similitud       REAL,
            ruta_foto_vehiculo TEXT,
            ruta_foto_placa    TEXT,
            fecha_alerta    TEXT DEFAULT CURRENT_TIMESTAMP,
            usuario_id      INTEGER DEFAULT 0
        )
    """)

    # Intentar agregar la columna usuario_id si la tabla historial_alertas ya existía sin ella
    try:
        cursor.execute("ALTER TABLE historial_alertas ADD COLUMN usuario_id INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre           TEXT NOT NULL,
            telegram_chat_id TEXT NOT NULL UNIQUE,
            activo           INTEGER DEFAULT 1,
            fecha_registro   TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cuentas_usuario (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            email            TEXT NOT NULL UNIQUE,
            password_hash    TEXT NOT NULL,
            token            TEXT,
            rtsp_url         TEXT,
            telegram_chat_id TEXT,
            telegram_token   TEXT,
            gemini_api_key   TEXT,
            created_at       TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Datos de ejemplo para pruebas
    ejemplos = [
        ("XYZ1234", "Toyota Corolla", "Blanco",  "Carlos Mendoza",   "2025-01-10", "Robado en estacionamiento"),
        ("ABC5678", "Honda Civic",    "Rojo",     "María Rodríguez",  "2025-02-20", "Robo a mano armada"),
        ("REPORTE12","Nissan Sentra", "Negro",    "Juan García",      "2025-03-05", "Reporte por desaparición"),
    ]

    for placa, modelo, color, propietario, fecha, desc in ejemplos:
        cursor.execute("""
            INSERT OR IGNORE INTO placas_robadas (placa, modelo, color, propietario, fecha_reporte, descripcion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (placa, modelo, color, propietario, fecha, desc))

    conn.commit()
    conn.close()
    print(f"[DB] Base de datos inicializada en: {DB_PATH}")


class DatabasePlacas:
    """Interfaz principal para consultar y gestionar placas robadas."""

    def __init__(self):
        inicializar_db()

    def consultar_placa(self, texto_detectado: str, umbral_similitud: float = 0.80):
        """
        Busca si una placa detectada coincide con alguna placa robada.
        Usa búsqueda exacta primero y luego búsqueda difusa.

        Returns:
            (es_robado: bool, info: dict | None)
            info contiene: placa, modelo, color, propietario, fecha_reporte, descripcion, similitud
        """
        conn = obtener_conexion()
        cursor = conn.cursor()

        # 1. Búsqueda exacta
        cursor.execute(
            "SELECT * FROM placas_robadas WHERE placa = ? AND activo = 1",
            (texto_detectado,)
        )
        fila = cursor.fetchone()

        if fila:
            conn.close()
            return True, {**dict(fila), "similitud": 1.0}

        # 2. Búsqueda difusa sobre todas las placas activas
        cursor.execute("SELECT * FROM placas_robadas WHERE activo = 1")
        todas = cursor.fetchall()
        conn.close()

        mejor_coincidencia = None
        mejor_similitud = 0.0

        for fila in todas:
            placa_bd = fila["placa"]
            similitud = difflib.SequenceMatcher(None, texto_detectado, placa_bd).ratio()
            if similitud > mejor_similitud:
                mejor_similitud = similitud
                mejor_coincidencia = fila

        if mejor_similitud >= umbral_similitud and mejor_coincidencia:
            return True, {**dict(mejor_coincidencia), "similitud": mejor_similitud}

        # 3. Búsqueda externa en la API de REPUVE (si está habilitada)
        try:
            import sys
            import os
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "iAs")))
            from repuve_api import consultar_repuve
            
            res_repuve = consultar_repuve(texto_detectado)
            if res_repuve and res_repuve.get("es_robado"):
                return True, {
                    "placa": res_repuve["placa"],
                    "modelo": res_repuve["modelo"],
                    "color": res_repuve["color"],
                    "propietario": res_repuve["propietario"],
                    "fecha_reporte": res_repuve["fecha_reporte"],
                    "descripcion": f"REPUVE: {res_repuve['detalles_repuve']}",
                    "similitud": 1.0
                }
        except Exception as e:
            print(f"[DB] Error al consultar REPUVE: {e}")

        return False, None

    def registrar_alerta(self, placa_bd: str, placa_detectada: str, similitud: float,
                         ruta_vehiculo: str = None, ruta_placa: str = None, usuario_id: int = 0):
        """Registra una alerta detectada en el historial."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO historial_alertas (placa, placa_detectada, similitud, ruta_foto_vehiculo, ruta_foto_placa, usuario_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (placa_bd, placa_detectada, similitud, ruta_vehiculo, ruta_placa, usuario_id))
        conn.commit()
        conn.close()

    def agregar_placa(self, placa: str, modelo: str = "", color: str = "",
                      propietario: str = "", fecha_reporte: str = None, descripcion: str = ""):
        """Agrega una nueva placa robada a la base de datos."""
        if fecha_reporte is None:
            fecha_reporte = datetime.now().strftime("%Y-%m-%d")

        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO placas_robadas (placa, modelo, color, propietario, fecha_reporte, descripcion)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (placa.upper().strip(), modelo, color, propietario, fecha_reporte, descripcion))
            conn.commit()
            print(f"✅ [DB] Placa '{placa.upper()}' agregada correctamente.")
            return True
        except sqlite3.IntegrityError:
            print(f"⚠️ [DB] La placa '{placa.upper()}' ya existe en la base de datos.")
            return False
        finally:
            conn.close()

    def eliminar_placa(self, placa: str):
        """Desactiva una placa (marca como no activa, no borra el registro)."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE placas_robadas SET activo = 0 WHERE placa = ?",
            (placa.upper().strip(),)
        )
        afectadas = cursor.rowcount
        conn.commit()
        conn.close()
        if afectadas > 0:
            print(f"✅ [DB] Placa '{placa.upper()}' desactivada (vehículo recuperado).")
        else:
            print(f"❌ [DB] No se encontró la placa '{placa.upper()}'.")
        return afectadas > 0

    def listar_placas(self, solo_activas: bool = True):
        """Retorna la lista de placas en la base de datos."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        if solo_activas:
            cursor.execute("SELECT * FROM placas_robadas WHERE activo = 1 ORDER BY fecha_reporte DESC")
        else:
            cursor.execute("SELECT * FROM placas_robadas ORDER BY fecha_reporte DESC")
        filas = cursor.fetchall()
        conn.close()
        return [dict(f) for f in filas]

    def listar_historial(self, limite: int = 20, usuario_id: int = 0):
        """Retorna el historial de alertas más recientes de un usuario (o todas si usuario_id es 0)."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        if usuario_id > 0:
            cursor.execute(
                "SELECT * FROM historial_alertas WHERE usuario_id = ? ORDER BY fecha_alerta DESC LIMIT ?", (usuario_id, limite)
            )
        else:
            cursor.execute(
                "SELECT * FROM historial_alertas ORDER BY fecha_alerta DESC LIMIT ?", (limite,)
            )
        filas = cursor.fetchall()
        conn.close()
        return [dict(f) for f in filas]

    # --- Métodos para gestión de usuarios de Telegram ---

    def agregar_usuario(self, nombre: str, telegram_chat_id: str):
        """Agrega un nuevo usuario a la base de datos para recibir alertas."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO usuarios (nombre, telegram_chat_id, activo)
                VALUES (?, ?, 1)
            """, (nombre.strip(), str(telegram_chat_id).strip()))
            conn.commit()
            print(f"✅ [DB] Usuario '{nombre}' con Chat ID '{telegram_chat_id}' agregado/activado.")
            return True
        except Exception as e:
            print(f"❌ [DB] Error al agregar usuario: {e}")
            return False
        finally:
            conn.close()

    def eliminar_usuario(self, telegram_chat_id: str):
        """Desactiva a un usuario."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET activo = 0 WHERE telegram_chat_id = ?",
            (str(telegram_chat_id).strip(),)
        )
        afectadas = cursor.rowcount
        conn.commit()
        conn.close()
        if afectadas > 0:
            print(f"✅ [DB] Usuario con Chat ID '{telegram_chat_id}' desactivado.")
        else:
            print(f"❌ [DB] No se encontró el Chat ID '{telegram_chat_id}'.")
        return afectadas > 0

    def listar_usuarios(self, solo_activos: bool = True):
        """Lista los usuarios registrados."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        if solo_activos:
            cursor.execute("SELECT * FROM usuarios WHERE activo = 1 ORDER BY fecha_registro DESC")
        else:
            cursor.execute("SELECT * FROM usuarios ORDER BY fecha_registro DESC")
        filas = cursor.fetchall()
        conn.close()
        return [dict(f) for f in filas]

    def obtener_chat_ids_activos(self):
        """Retorna una lista simple con todos los chat_id activos de Telegram."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT telegram_chat_id FROM usuarios WHERE activo = 1")
            filas = cursor.fetchall()
            return [f["telegram_chat_id"] for f in filas]
        except Exception:
            return []
        finally:
            conn.close()

    # --- Gestión de Cuentas de Usuario SaaS ---

    def crear_cuenta(self, email: str, password_hash: str) -> bool:
        """Crea una nueva cuenta de usuario en el sistema."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO cuentas_usuario (email, password_hash)
                VALUES (?, ?)
            """, (email.lower().strip(), password_hash))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def obtener_cuenta_por_email(self, email: str):
        """Retorna los datos de una cuenta por su email."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cuentas_usuario WHERE email = ?", (email.lower().strip(),))
        fila = cursor.fetchone()
        conn.close()
        return dict(fila) if fila else None

    def obtener_cuenta_por_token(self, token: str):
        """Retorna los datos de una cuenta buscando por su token activo."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cuentas_usuario WHERE token = ?", (token,))
        fila = cursor.fetchone()
        conn.close()
        return dict(fila) if fila else None

    def actualizar_token_cuenta(self, usuario_id: int, token: str):
        """Actualiza el token JWT/sesión de un usuario."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("UPDATE cuentas_usuario SET token = ? WHERE id = ?", (token, usuario_id))
        conn.commit()
        conn.close()

    def actualizar_config_cuenta(self, usuario_id: int, rtsp_url: str, telegram_chat_id: str, telegram_token: str, gemini_api_key: str):
        """Actualiza la configuración de cámara e integraciones de una cuenta."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE cuentas_usuario
            SET rtsp_url = ?, telegram_chat_id = ?, telegram_token = ?, gemini_api_key = ?
            WHERE id = ?
        """, (rtsp_url, telegram_chat_id, telegram_token, gemini_api_key, usuario_id))
        conn.commit()
        conn.close()

    def obtener_todas_las_cuentas_con_camara(self):
        """Retorna todas las cuentas de usuario que tienen una cámara configurada."""
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cuentas_usuario WHERE rtsp_url IS NOT NULL AND rtsp_url != ''")
        filas = cursor.fetchall()
        conn.close()
        return [dict(f) for f in filas]
