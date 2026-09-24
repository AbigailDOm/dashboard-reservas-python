import pandas as pd


def cargar_y_convertir_excel(path_excel: str) -> pd.DataFrame:
    df = pd.read_excel(path_excel, sheet_name='Reservas')
    # Convertimos la columna a tipo datetime para poder manipular fechas y horas fácilmente
    df['Fecha de realización'] = pd.to_datetime(
        df['Fecha de realización'], format='%d/%m/%Y %H:%M', errors='coerce'
    )
    return df


def agregar_columnas_calculadas(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica las transformaciones requeridas para generar las nuevas columnas."""
    df = df.copy()

    # 1. Fecha en formato dd/mmm/aaaa
    df['Fecha_Formato'] = df['Fecha de realización'].dt.strftime('%d/%m/%Y %H:%M')

    # 2. Día separado en formato dd
    df['Dia_Numero'] = df['Fecha de realización'].dt.strftime('%d')

    # 3. Día de la semana en español
    dias_espanol = {
        'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
        'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado', 'Sunday': 'domingo'
    }
    df['Dia_Semana'] = df['Fecha de realización'].dt.day_name().map(dias_espanol)

    # 4. Hora de atención HH:MM
    df['Hora_Atencion'] = df['Fecha de realización'].dt.strftime('%H:%M')

    # 5. Hora corta (primeros dos dígitos como entero)
    df['Hora_Corta'] = df['Fecha de realización'].dt.hour

    # 6. Turno (Matutino / Vespertino)
    df['Turno'] = df['Hora_Corta'].apply(lambda hora: 'Matutino' if hora < 12 else 'Vespertino')

    # 7 y 8. Regla Exacta de Asistencia e Inasistencia
    # Definimos la lista exacta de estados que cuentan como ASISTENCIA
    estados_asistencia = ['En Espera']

    # Normalizamos el texto (elimina espacios y pone Mayúscula Inicial)
    estado_limpio = df['Estado'].astype(str).str.strip().str.title()

    # Si el estado está en la lista -> Asiste, de lo contrario -> No Asiste
    df['Asistencia'] = estado_limpio.apply(
        lambda estado: 'Asiste' if estado in [e.title() for e in estados_asistencia] else 'No Asiste'
    )

    df['Inasistencia'] = estado_limpio.apply(
        lambda estado: 'No Asiste' if estado in [e.title() for e in estados_asistencia] else 'Asiste'
    )

    # 9. Origen
    df['Origen_Resumen'] = df['Origen'].apply(
        lambda origen: 'Online' if str(origen).strip().lower() == 'online' else 'Manual'
    )

    return df