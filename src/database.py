import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "imo_reservas.db"


def inicializar_bd():
    """Crea las tablas necesarias para auditoría y asegura la estructura de reservas."""
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
    """Inserta de forma masiva los registros procesados creando o añadiendo a la tabla reservas en SQLite."""
    conn = sqlite3.connect(DB_NAME)

    df_sql = df_procesado.copy()
    if 'Fecha de realización' in df_sql.columns:
        df_sql['Fecha de realización'] = df_sql['Fecha de realización'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # 'append' si la tabla ya existe con todas las columnas, o 'replace' si es la primera carga limpia
    try:
        df_sql.to_sql('reservas', conn, if_exists='append', index=False)
    except Exception:
        # Si hay discrepancia de columnas previa, recreamos la tabla limpia con el nuevo esquema completo
        df_sql.to_sql('reservas', conn, if_exists='replace', index=False)

    conn.close()


def cargar_reservas_desde_bd() -> pd.DataFrame:
    """Carga todo el histórico de reservas desde SQLite y estandariza los nombres de columnas para el tablero."""
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql("SELECT * FROM reservas", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()

    if not df.empty:
        if 'Fecha de realización' in df.columns:
            df['Fecha de realización'] = pd.to_datetime(df['Fecha de realización'])
        elif 'fecha_realizacion' in df.columns:
            df['Fecha de realización'] = pd.to_datetime(df['fecha_realizacion'])

        if 'Dia_Semana' not in df.columns and 'Fecha de realización' in df.columns:
            dias_map = {0: 'lunes', 1: 'martes', 2: 'miércoles', 3: 'jueves', 4: 'viernes', 5: 'sábado', 6: 'domingo'}
            df['Dia_Semana'] = df['Fecha de realización'].dt.weekday.map(dias_map)

    return df