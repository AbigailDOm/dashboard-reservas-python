import pandas as pd


def _preparar_columnas_numericas(df: pd.DataFrame) -> pd.DataFrame:
    """Lee directamente la columna 'Asistencia' que ya sabemos que está bien en reservas_procesadas."""
    df_copia = df.copy()
    # 1 si dice exactamente 'Asiste', 0 para cualquier otra cosa
    df_copia['Asiste_Num'] = (df_copia['Asistencia'] == 'Asiste').astype(int)
    # 1 si dice exactamente 'No Asiste', 0 para cualquier otra cosa
    df_copia['NoAsiste_Num'] = (df_copia['Asistencia'] == 'No Asiste').astype(int)
    return df_copia


def generar_reporte_prestadores(df: pd.DataFrame) -> pd.DataFrame:
    """Resume citas, asistencias, inasistencias y sus porcentajes agrupados por Prestador."""
    df = _preparar_columnas_numericas(df)
    reporte = df.groupby('Prestador').agg(
        Total_Citas=('Estado', 'count'),
        Atendidos=('Asiste_Num', 'sum'),
        Inasistencias=('NoAsiste_Num', 'sum')
    ).reset_index()

    reporte['% Asistencia'] = (reporte['Atendidos'] / reporte['Total_Citas'] * 100).round(2)
    reporte['% Inasistencia'] = (reporte['Inasistencias'] / reporte['Total_Citas'] * 100).round(2)

    return reporte.sort_values(by='Total_Citas', ascending=False)


def generar_reporte_servicios(df: pd.DataFrame) -> pd.DataFrame:
    """Resume la demanda, asistencia e inasistencia con porcentajes por Servicio."""
    df = _preparar_columnas_numericas(df)
    reporte = df.groupby('Servicio').agg(
        Total_Reservas=('Estado', 'count'),
        Atendidos=('Asiste_Num', 'sum'),
        Inasistencias=('NoAsiste_Num', 'sum')
    ).reset_index()

    reporte['% Asistencia'] = (reporte['Atendidos'] / reporte['Total_Reservas'] * 100).round(2)
    reporte['% Inasistencia'] = (reporte['Inasistencias'] / reporte['Total_Reservas'] * 100).round(2)

    return reporte.sort_values(by='Total_Reservas', ascending=False)


def generar_reporte_origen(df: pd.DataFrame) -> pd.DataFrame:
    """Resume el comportamiento por canal de Origen (Online vs Manual)."""
    df = _preparar_columnas_numericas(df)
    reporte = df.groupby('Origen_Resumen').agg(
        Total_Reservas=('Estado', 'count'),
        Atendidos=('Asiste_Num', 'sum'),
        Inasistencias=('NoAsiste_Num', 'sum')
    ).reset_index()

    reporte['% del Total Reservas'] = (reporte['Total_Reservas'] / reporte['Total_Reservas'].sum() * 100).round(2)
    reporte['% Asistencia'] = (reporte['Atendidos'] / reporte['Total_Reservas'] * 100).round(2)
    reporte['% Inasistencia'] = (reporte['Inasistencias'] / reporte['Total_Reservas'] * 100).round(2)

    return reporte


def generar_reporte_prestador_servicio(df: pd.DataFrame) -> pd.DataFrame:
    """Desglosa los servicios atendidos por cada prestador."""
    df = _preparar_columnas_numericas(df)
    reporte = df.groupby(['Prestador', 'Servicio']).agg(
        Total_Citas=('Estado', 'count'),
        Atendidos=('Asiste_Num', 'sum'),
        Inasistencias=('NoAsiste_Num', 'sum')
    ).reset_index()

    reporte['% Asistencia'] = (reporte['Atendidos'] / reporte['Total_Citas'] * 100).round(2)
    reporte['% Inasistencia'] = (reporte['Inasistencias'] / reporte['Total_Citas'] * 100).round(2)

    return reporte.sort_values(by=['Prestador', 'Total_Citas'], ascending=[True, False])


def generar_reporte_origen_servicio(df: pd.DataFrame) -> pd.DataFrame:
    """Desglosa los servicios demandados según el origen de la reserva (Online vs Manual)."""
    df = _preparar_columnas_numericas(df)
    reporte = df.groupby(['Origen_Resumen', 'Servicio']).agg(
        Total_Reservas=('Estado', 'count'),
        Atendidos=('Asiste_Num', 'sum'),
        Inasistencias=('NoAsiste_Num', 'sum')
    ).reset_index()

    reporte['% Asistencia'] = (reporte['Atendidos'] / reporte['Total_Reservas'] * 100).round(2)
    reporte['% Inasistencia'] = (reporte['Inasistencias'] / reporte['Total_Reservas'] * 100).round(2)

    return reporte.sort_values(by=['Origen_Resumen', 'Total_Reservas'], ascending=[True, False])


def generar_reporte_por_hora_cerrada(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa las reservas en bloques de horas cerradas (ej. 08:00, 09:00)."""
    df_temp = _preparar_columnas_numericas(df)
    df_temp['Hora_Bloque'] = df_temp['Hora_Corta'].apply(lambda h: f"{int(h):02d}:00" if pd.notnull(h) else "N/A")

    reporte = df_temp.groupby('Hora_Bloque').agg(
        Total_Citas=('Estado', 'count'),
        Atendidos=('Asiste_Num', 'sum'),
        Inasistencias=('NoAsiste_Num', 'sum')
    ).reset_index()

    reporte['% Asistencia'] = (reporte['Atendidos'] / reporte['Total_Citas'] * 100).round(2)
    reporte['% Inasistencia'] = (reporte['Inasistencias'] / reporte['Total_Citas'] * 100).round(2)

    return reporte.sort_values(by='Hora_Bloque')


def generar_reporte_dia_semana(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa asistencias e inasistencias por día de la semana (lunes a domingo)."""
    df = _preparar_columnas_numericas(df)
    reporte = df.groupby('Dia_Semana').agg(
        Total_Citas=('Estado', 'count'),
        Atendidos=('Asiste_Num', 'sum'),
        Inasistencias=('NoAsiste_Num', 'sum')
    ).reset_index()

    reporte['% Asistencia'] = (reporte['Atendidos'] / reporte['Total_Citas'] * 100).round(2)
    reporte['% Inasistencia'] = (reporte['Inasistencias'] / reporte['Total_Citas'] * 100).round(2)

    orden_dias = {'lunes': 1, 'martes': 2, 'miércoles': 3, 'jueves': 4, 'viernes': 5, 'sábado': 6, 'domingo': 7}
    reporte['Orden'] = reporte['Dia_Semana'].map(orden_dias)
    return reporte.sort_values(by='Orden').drop(columns=['Orden'])


def generar_reporte_turno(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa asistencias e inasistencias por turno (Matutino vs Vespertino)."""
    df = _preparar_columnas_numericas(df)
    reporte = df.groupby('Turno').agg(
        Total_Citas=('Estado', 'count'),
        Atendidos=('Asiste_Num', 'sum'),
        Inasistencias=('NoAsiste_Num', 'sum')
    ).reset_index()

    reporte['% Asistencia'] = (reporte['Atendidos'] / reporte['Total_Citas'] * 100).round(2)
    reporte['% Inasistencia'] = (reporte['Inasistencias'] / reporte['Total_Citas'] * 100).round(2)

    return reporte.sort_values(by='Total_Citas', ascending=False)