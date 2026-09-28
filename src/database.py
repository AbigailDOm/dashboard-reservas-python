import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "imo_reservas.db"


def inicializar_bd():
    """Crea las tablas necesarias para reservas, auditoría y usuarios si no existen."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Tabla de Auditoría
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            nombre TEXT,
            accion TEXT,
            detalles TEXT,
            timestamp TEXT
        )
    ''')

    # 2. Tabla de Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY,
            nombre TEXT,
            password TEXT,
            rol TEXT
        )
    ''')

    # 3. Tabla de Reservas (Histórico centralizado de reportes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_realizacion TEXT,
            prestador TEXT,
            servicio TEXT,
            origen_resumen TEXT,
            asistencia TEXT,
            dia_semana TEXT,
            turno TEXT
        )
    ''')

    conn.commit()
    conn.close()


def registrar_actividad(username, nombre, accion, detalles=""):
    """Guarda cada movimiento o consulta que hace un usuario en la BD."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO auditoria (username, nombre, accion, detalles, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, nombre, accion, detalles, timestamp))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error al registrar auditoría: {e}")


def sincronizar_usuarios_desde_secrets(usuarios_secrets):
    """Sincroniza los usuarios iniciales desde st.secrets hacia SQLite si la tabla está vacía."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    count = cursor.fetchone()[0]

    if count == 0:
        for username, data in usuarios_secrets.items():
            rol = "admin" if "v.dominguez" in username or "direccion" in username else "usuario"
            cursor.execute('''
                INSERT OR IGNORE INTO usuarios (username, nombre, password, rol)
                VALUES (?, ?, ?, ?)
            ''', (username, data["name"], data["password"], rol))
        conn.commit()
    conn.close()


def obtener_usuarios_bd():
    """Obtiene los usuarios directamente desde SQLite para el autenticador."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT username, nombre, password FROM usuarios")
    rows = cursor.fetchall()
    conn.close()

    usernames_dict = {}
    for row in rows:
        usernames_dict[row[0]] = {
            "name": row[1],
            "password": row[2]
        }
    return {"usernames": usernames_dict}


def guardar_reservas_en_bd(df_procesado: pd.DataFrame):
    """Inserta de forma masiva los registros limpios en la tabla reservas de SQLite."""
    conn = sqlite3.connect(DB_NAME)
    # Seleccionamos y renombramos columnas para que coincidan con la tabla SQL
    df_sql = pd.DataFrame({
        'fecha_realizacion': df_procesado['Fecha de realización'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'prestador': df_procesado['Prestador'],
        'servicio': df_procesado['Servicio'],
        'origen_resumen': df_procesado['Origen_Resumen'],
        'asistencia': df_procesado['Asistencia'],
        'dia_semana': df_procesado['Dia_Semana'],
        'turno': df_procesado['Turno']
    })
    # 'append' agrega los nuevos registros sin borrar los anteriores (ideal para subir por lotes o meses)
    df_sql.to_sql('reservas', conn, if_exists='append', index=False)
    conn.close()


def cargar_reservas_desde_bd() -> pd.DataFrame:
    """Carga todo el histórico de reservas desde SQLite y lo convierte a DataFrame de pandas."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM reservas", conn)
    conn.close()

    if not df.empty:
        # Convertimos la columna de texto de vuelta a formato fecha de pandas
        df['Fecha de realización'] = pd.to_datetime(df['fecha_realizacion'])
    return df