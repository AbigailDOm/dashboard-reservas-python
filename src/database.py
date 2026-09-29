import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "imo_reservas.db"


def inicializar_bd():
    """Crea las tablas necesarias para reservas y auditoría si no existen."""
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

    # 2. Tabla de Reservas (Histórico centralizado de reportes)
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


def guardar_reservas_en_bd(df_procesado: pd.DataFrame):
    """Inserta de forma masiva los registros limpios en la tabla reservas de SQLite."""
    conn = sqlite3.connect(DB_NAME)
    df_sql = pd.DataFrame({
        'fecha_realizacion': df_procesado['Fecha de realización'].dt.strftime('%Y-%m-%d %H:%M:%S'),
        'prestador': df_procesado['Prestador'],
        'servicio': df_procesado['Servicio'],
        'origen_resumen': df_procesado['Origen_Resumen'],
        'asistencia': df_procesado['Asistencia'],
        'dia_semana': df_procesado['Dia_Semana'],
        'turno': df_procesado['Turno']
    })
    df_sql.to_sql('reservas', conn, if_exists='append', index=False)
    conn.close()


def cargar_reservas_desde_bd() -> pd.DataFrame:
    """Carga todo el histórico de reservas desde SQLite y estandariza los nombres de columnas para el tablero."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM reservas", conn)
    conn.close()

    if not df.empty:
        # Mapeamos o normalizamos nombres por si vienen en minúsculas desde SQL
        renombres = {
            'fecha_realizacion': 'Fecha de realización',
            'prestador': 'Prestador',
            'servicio': 'Servicio',
            'origen_resumen': 'Origen_Resumen',
            'asistencia': 'Asistencia',
            'dia_semana': 'Dia_Semana',
            'turno': 'Turno'
        }
        df = df.rename(columns=renombres)

        # Si la columna Dia_Semana no existiera en viejos registros, la recalculamos por seguridad
        if 'Dia_Semana' not in df.columns and 'Fecha de realización' in df.columns:
            df['Fecha de realización'] = pd.to_datetime(df['Fecha de realización'])
            dias_map = {0: 'lunes', 1: 'martes', 2: 'miércoles', 3: 'jueves', 4: 'viernes', 5: 'sábado', 6: 'domingo'}
            df['Dia_Semana'] = df['Fecha de realización'].dt.weekday.map(dias_map)

        df['Fecha de realización'] = pd.to_datetime(df['Fecha de realización'])

    return df