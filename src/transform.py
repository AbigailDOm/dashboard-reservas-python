import pandas as pd
import streamlit as st

@st.cache_data(show_spinner=False)
def cargar_y_convertir_excel(path_excel) -> pd.DataFrame:
    df = pd.read_excel(path_excel, sheet_name='Reservas')
    df['Fecha de realización'] = pd.to_datetime(
        df['Fecha de realización'], format='%d/%m/%Y %H:%M', errors='coerce'
    )
    return df


def agregar_columnas_calculadas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica las transformaciones requeridas con lógica estricta de asistencia."""
    df = df.copy()

    # Fechas y Horarios
    df['Fecha_Formato'] = df['Fecha de realización'].dt.strftime('%d/%m/%Y %H:%M')
    df['Dia_Numero'] = df['Fecha de realización'].dt.strftime('%d')

    # Mes en texto en español y número para ordenar
    meses_espanol = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    df['Mes_Num'] = df['Fecha de realización'].dt.month
    df['Mes_Texto'] = df['Mes_Num'].map(meses_espanol)

    dias_espanol = {
        'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
        'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado', 'Sunday': 'domingo'
    }
    df['Dia_Semana'] = df['Fecha de realización'].dt.day_name().map(dias_espanol)
    df['Hora_Atencion'] = df['Fecha de realización'].dt.strftime('%H:%M')
    df['Hora_Corta'] = df['Fecha de realización'].dt.hour
    df['Turno'] = df['Hora_Corta'].apply(lambda hora: 'Matutino' if hora < 12 else 'Vespertino')

    # -------------------------------------------------------------------------
    # REGLA BÁSICA Y ÚNICA DE NEGOCIO:
    # ÚNICAMENTE el texto "En Espera" cuenta como Asistencia.
    # Cualquier otro valor (Reservado, Cancelado, Atendido, etc.) es Inasistencia.
    # -------------------------------------------------------------------------
    estado_limpio = df['Estado'].astype(str).str.strip().str.lower()

    # Creamos una columna principal con el texto para los gráficos
    df['Asistencia'] = estado_limpio.apply(lambda e: 'Asiste' if e == 'en espera' else 'No Asiste')

    # Creamos la columna opuesta para evitar el espejo ambiguo
    df['Inasistencia'] = df['Asistencia'].apply(lambda a: 'Inasistencia' if a == 'No Asiste' else 'Asistencia')

    # Canal / Origen
    df['Origen_Resumen'] = df['Origen'].apply(
        lambda origen: 'Online' if str(origen).strip().lower() == 'online' else 'Manual'
    )

    return df