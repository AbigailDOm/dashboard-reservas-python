import io
import psutil
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from src.transform import cargar_y_convertir_excel, agregar_columnas_calculadas
from src.report import (
    generar_reporte_prestadores,
    generar_reporte_servicios,
    generar_reporte_origen,
    generar_reporte_prestador_servicio,
    generar_reporte_origen_servicio,
    generar_reporte_por_hora_cerrada,
    generar_reporte_dia_semana,
    generar_reporte_turno
)

# Genera en memoria un archivo Excel con las 8 pestañas basándose en los datos filtrados
@st.cache_data(show_spinner="Generando reporte ejecutivo...")
def generar_excel_resumen_ejecutivo(df_filtrado: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        generar_reporte_prestadores(df_filtrado).to_excel(writer, sheet_name='Por Prestador', index=False)
        generar_reporte_servicios(df_filtrado).to_excel(writer, sheet_name='Por Servicio', index=False)
        generar_reporte_prestador_servicio(df_filtrado).to_excel(writer, sheet_name='Prestador x Servicio', index=False)
        generar_reporte_origen_servicio(df_filtrado).to_excel(writer, sheet_name='Origen x Servicio', index=False)
        generar_reporte_por_hora_cerrada(df_filtrado).to_excel(writer, sheet_name='Por Hora Cerrada', index=False)
        generar_reporte_dia_semana(df_filtrado).to_excel(writer, sheet_name='Por Dia Semana', index=False)
        generar_reporte_turno(df_filtrado).to_excel(writer, sheet_name='Por Turno', index=False)
        generar_reporte_origen(df_filtrado).to_excel(writer, sheet_name='Por Origen', index=False)

    buffer.seek(0)
    return buffer.getvalue()

# Configuración de página
st.set_page_config(
    page_title="Panel Analítico de Reservas IMO",
    layout="wide"
)

# Paleta de colores extraída de la referencia UI
PRIMARY_CYAN = "#4CB5E5"
SECONDARY_INDIGO = "#4A52C8"
BG_LIGHT = "#F3F6FD"
TEXT_DARK = "#1E293B"
CARD_BG = "#FFFFFF"
SUCCESS_GREEN = "#38C1B3"
DANGER_RED = "#FF6B6B"

# Inyección CSS limpia para Tarjetas KPI y Pestañas
st.markdown("""
    <style>
    /* 1. Fondo e interfaz adaptable de tarjetas KPI */
    [data-testid="stMetric"] {
        background-color: var(--background-secondary-color) !important;
        padding: 18px;
        border-radius: 16px;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
    }

    /* 2. Color dinámico de etiquetas (Títulos de los KPIs) */
    [data-testid="stMetricLabel"] label, 
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] span {
        color: var(--text-color) !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }

    /* 3. Color dinámico de los valores numéricos */
    [data-testid="stMetricValue"] div, 
    [data-testid="stMetricValue"] p,
    [data-testid="stMetricValue"] span {
        color: var(--text-color) !important;
        font-weight: 700 !important;
    }

    /* 4. Estilo de las pestañas */
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
    }

    .stTabs [aria-selected="true"] {
        background-color: rgba(76, 181, 229, 0.25) !important;
        color: var(--text-color) !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Panel Analítico de Reservas IMO")
st.markdown("Visualiza y analiza la atención médica por Prestador, Servicio, Canal de Origen y Horarios.")

# Sidebar - Carga de Datos con validación de peso y límites
st.sidebar.header("Cargar Datos")
archivo_subido = st.sidebar.file_uploader("Sube el archivo Excel (.xlsx)", type=["xlsx"])

if archivo_subido is not None:
    # 1. Validar el tamaño del archivo en MB antes de procesar
    tamanio_bytes = archivo_subido.size
    tamanio_mb = tamanio_bytes / (1024 * 1024)

    proceso = psutil.Process(os.getpid())
    memoria_actual_mb = proceso.memory_info().rss / (1024 * 1024)
    print(
        f"[LOG TÉCNICO] Archivo subido: {tamanio_mb:.2f} MB | Memoria RAM actual del servidor: {memoria_actual_mb:.2f} MB")

    LIMITE_MAXIMO_MB = 30.0  # Límite preventivo de seguridad

    if tamanio_mb > LIMITE_MAXIMO_MB:
        st.error(
            f"🚫 **Archivo demasiado pesado:** El archivo pesa **{tamanio_mb:.1f} MB**, superando el límite de seguridad de **{LIMITE_MAXIMO_MB} MB**. "
            "Por favor, reduce el rango de fechas o divide el archivo para evitar saturar los recursos del servidor."
        )
    else:
        # Carga normal si pasa la validación de peso
        archivo_subido.seek(0)
        df = cargar_y_convertir_excel(archivo_subido)
        df_procesado = agregar_columnas_calculadas(df)

        # ==========================================
        # 2. SIDEBAR FILTROS OPERATIVOS (Rango de Fechas)
        # ==========================================
        st.sidebar.header("Filtros Operativos")

        min_date = df_procesado['Fecha de realización'].min().date()
        max_date = df_procesado['Fecha de realización'].max().date()

        st.sidebar.markdown("📅 **Filtrar por Rango de Fechas**")

        rango_fechas = st.sidebar.date_input(
            "Selecciona el periodo:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        # Filtro 2: Día de la Semana
        dias_ordenados = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        dias_presentes = [d for d in dias_ordenados if d in df_procesado['Dia_Semana'].unique()]
        dia_seleccionado = st.sidebar.multiselect("Día de la Semana:", options=dias_presentes, default=dias_presentes)

        # Filtro 3: Turno
        turnos_disponibles = sorted(df_procesado['Turno'].dropna().unique().tolist())
        turno_seleccionado = st.sidebar.multiselect("Turno Horario:", options=turnos_disponibles,
                                                    default=turnos_disponibles)

        # Filtro 4: Prestador
        prestadores_disponibles = ["Todos"] + sorted(df_procesado['Prestador'].dropna().unique().tolist())
        prestador_seleccionado = st.sidebar.selectbox("Prestador:", prestadores_disponibles)

        # Filtro 5: Servicio (Multiselect)
        servicios_disponibles = sorted(df_procesado['Servicio'].dropna().unique().tolist())
        servicios_seleccionados = st.sidebar.multiselect(
            "Servicio(s):",
            options=servicios_disponibles,
            default=servicios_disponibles
        )

        # Filtro 6: Canal / Origen
        origen_disponibles = ["Todos"] + sorted(df_procesado['Origen_Resumen'].dropna().unique().tolist())
        origen_seleccionado = st.sidebar.selectbox("Origen:", origen_disponibles)

        # --- APLICAR FILTROS OPERATIVOS (BLINDADO) ---
        if isinstance(rango_fechas, tuple):
            if len(rango_fechas) == 2:
                fecha_inicio, fecha_fin = rango_fechas
            elif len(rango_fechas) == 1:
                fecha_inicio = fecha_fin = rango_fechas[0]
            else:
                fecha_inicio, fecha_fin = min_date, max_date
        else:
            fecha_inicio = fecha_fin = rango_fechas if rango_fechas else min_date

        # Si por alguna razón el usuario deja una fecha vacía, asignamos los límites
        if not fecha_inicio:
            fecha_inicio = min_date
        if not fecha_fin:
            fecha_fin = max_date

        df_filtrado = df_procesado[
            (df_procesado['Fecha de realización'].dt.date >= fecha_inicio) &
            (df_procesado['Fecha de realización'].dt.date <= fecha_fin) &
            (df_procesado['Dia_Semana'].isin(dia_seleccionado)) &
            (df_procesado['Turno'].isin(turno_seleccionado)) &
            (df_procesado['Servicio'].isin(servicios_seleccionados))
            ]

        if prestador_seleccionado != "Todos":
            df_filtrado = df_filtrado[
                df_filtrado['Prestadores'] == prestador_seleccionado] if 'Prestadores' in df_filtrado.columns else \
            df_filtrado[df_filtrado['Prestador'] == prestador_seleccionado]

        if origen_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Origen_Resumen'] == origen_seleccionado]

        # Botón de Descarga en la Barra Lateral
        st.sidebar.markdown("---")
        st.sidebar.header("Exportar Reporte")

        excel_bytes = generar_excel_resumen_ejecutivo(df_filtrado)

        st.sidebar.download_button(
            label="Descargar Resumen Ejecutivo (.xlsx)",
            data=excel_bytes,
            file_name="resumen_ejecutivo_reservas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="btn_descarga_resumen_sidebar"  # <--- Agregamos esta llave única
        )

        # Botón de Descarga en la Barra Lateral
        st.sidebar.markdown("---")
        st.sidebar.header("Exportar Reporte")

        excel_bytes = generar_excel_resumen_ejecutivo(df_filtrado)

        st.sidebar.download_button(
            label="Descargar Resumen Ejecutivo (.xlsx)",
            data=excel_bytes,
            file_name="resumen_ejecutivo_reservas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # Botón de Descarga en la Barra Lateral
    st.sidebar.markdown("---")
    st.sidebar.header("Exportar Reporte")

    excel_bytes = generar_excel_resumen_ejecutivo(df_filtrado)

    st.sidebar.download_button(
        label="Descargar Resumen Ejecutivo (.xlsx)",
        data=excel_bytes,
        file_name="resumen_ejecutivo_reservas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    # 3. Tarjetas KPIs (Alineación 100% exacta con reservas_procesadas)
    st.subheader("Indicadores Clave")
    col1, col2, col3, col4, col5 = st.columns(5)

    total_reservas = len(df_filtrado)

    # La fuente de verdad única es la columna 'Asistencia'
    total_asistencias = (df_filtrado['Asistencia'] == 'Asiste').sum()
    total_inasistencias = (df_filtrado['Asistencia'] == 'No Asiste').sum()

    pct_asistencia = (total_asistencias / total_reservas * 100) if total_reservas > 0 else 0
    pct_inasistencia = (total_inasistencias / total_reservas * 100) if total_reservas > 0 else 0

    col1.metric("Total Reservas", f"{total_reservas:,d}")
    col2.metric("Asistencias", f"{total_asistencias:,d}")
    col3.metric("Inasistencias", f"{total_inasistencias:,d}")
    col4.metric("% Cumplimiento", f"{pct_asistencia:.1f}%")
    col5.metric("% Inasistencia", f"{pct_inasistencia:.1f}%")

    st.markdown("---")

    # ==========================================
    # SECCIÓN: INSIGHTS AUTOMÁTICOS INTELIGENTES
    # ==========================================

    st.subheader("Hallazgos Clave del Periodo Seleccionado")

    if not df_filtrado.empty:
        rep_serv_insight = generar_reporte_servicios(df_filtrado)

        if not rep_serv_insight.empty:
            # 1. Porcentaje más alto de inasistencia (Severidad del Comportamiento)
            peor_pct_row = rep_serv_insight.sort_values(by='% Inasistencia', ascending=False).iloc[0]
            servicio_pct_alto = peor_pct_row['Servicio']
            pct_alto = peor_pct_row['% Inasistencia']

            # 2. Mayor volumen absoluto de inasistencias (Impacto Operativo Real)
            peor_vol_row = rep_serv_insight.sort_values(by='Inasistencias', ascending=False).iloc[0]
            servicio_vol_alto = peor_vol_row['Servicio']
            vol_alto = peor_vol_row['Inasistencias']
        else:
            servicio_pct_alto, pct_alto = "N/A", 0
            servicio_vol_alto, vol_alto = "N/A", 0

        # 3. Calcular el prestador con menor atención efectiva
        # (Solo lo calculamos y mostramos si hay múltiples prestadores y NO se ha filtrado uno solo)
        mostrar_prestador_insight = False
        nombre_prestador, total_atendidos_prestador = "N/A", 0

        if prestador_seleccionado == "Todos":
            rep_prest_insight = generar_reporte_prestadores(df_filtrado)
            # Verificamos si realmente hay más de un prestador en los datos filtrados actuales
            if len(rep_prest_insight) > 1:
                prestador_bajo = rep_prest_insight.sort_values(by='Atendidos', ascending=True).iloc[0]
                nombre_prestador = prestador_bajo['Prestador']
                total_atendidos_prestador = prestador_bajo['Atendidos']
                mostrar_prestador_insight = True

        # 4. Calcular el día de la semana con mayor volumen de inasistencias
        rep_dia_insight = generar_reporte_dia_semana(df_filtrado)
        if not rep_dia_insight.empty:
            peor_dia = rep_dia_insight.sort_values(by='Inasistencias', ascending=False).iloc[0]
            nombre_dia = peor_dia['Dia_Semana']
            total_inasistencias_dia = peor_dia['Inasistencias']
        else:
            nombre_dia = "N/A"
            total_inasistencias_dia = 0

        # --- REDACCIÓN DINÁMICA DE LOS TEXTOS ---

        if pct_alto > 0:
            texto_severidad = (
                f"**Severidad del Comportamiento (% Crítico):** El servicio **{servicio_pct_alto}** "
                f"presenta el porcentaje más alto de inasistencia con un **{pct_alto}%**, lo que indica que el proceso "
                f"de confirmación, recordatorio o el interés del paciente requiere atención en este rubro."
            )
        else:
            texto_severidad = (
                f"**Desempeño Destacado (% de Asistencia):** El servicio **{servicio_pct_alto}** "
                f"registra un **0.0% de inasistencia**, alcanzando un cumplimiento perfecto en el periodo."
            )

        if vol_alto > 0:
            texto_volumen = (
                f"**Impacto Operativo Real (Volumen de Faltas):** El servicio **{servicio_vol_alto}** "
                f"acumula la mayor cantidad de horas muertas, registrando un total de **{vol_alto:,d}** citas perdidas."
            )
        else:
            texto_volumen = (
                f"**Impacto Operativo Real (Volumen de Faltas):** No se registran citas perdidas "
                f"por ausentismo en los servicios analizados, operando con saldo blanco."
            )

        if total_inasistencias_dia > 0:
            texto_dia = (
                f"**Día con mayor ausentismo:** El día **{nombre_dia}** acumula la mayor cantidad de inasistencias "
                f"a nivel global, sumando **{total_inasistencias_dia:,d}** casos."
            )
        else:
            texto_dia = (
                f"**Análisis por Día:** No se detectan inasistencias significativas distribuidas en los días de la semana."
            )

        # Construimos la lista de viñetas dinámicamente
        viñetas = [
            f"* {texto_severidad}",
            f"* {texto_volumen}"
        ]

        # Agregamos la línea del prestador SOLAMENTE si hay una comparativa real multicaso
        if mostrar_prestador_insight:
            viñetas.append(
                f"**Prestador con menor flujo efectivo:** **{nombre_prestador}** registra el menor volumen "
                f"de atenciones efectivas (*En Espera*), con **{total_atendidos_prestador:,d}** citas en comparación con el resto del equipo."
            )

        viñetas.append(f"* {texto_dia}")

        # Mostrar los insights limpios
        st.info(
            f"**Resumen Ejecutivo Dinámico:**\n\n" + "\n".join(viñetas)
        )
    else:
        st.warning("⚠️ No hay datos disponibles para los filtros seleccionados.")

    st.markdown("---")

    # 4. Gráficos
    st.subheader("Distribución Operativa")
    col_hora, col_dia = st.columns(2)

    with col_hora:
        # Generamos el reporte y renombramos las columnas para estandarizar las etiquetas a 'Asiste' y 'No Asiste'
        rep_hora = generar_reporte_por_hora_cerrada(df_filtrado).rename(
            columns={'Atendidos': 'Asiste', 'Inasistencias': 'No Asiste'}
        )

        fig_hora = px.bar(
            rep_hora,
            x='Hora_Bloque',
            y=['Asiste', 'No Asiste'],
            title="Asistencias e Inasistencias por Bloque Horario",
            barmode='stack',
            color_discrete_map={'Asiste': SECONDARY_INDIGO, 'No Asiste': PRIMARY_CYAN},
            labels={'value': 'Cantidad de Citas', 'Hora_Bloque': 'Hora', 'variable': 'Estado'}
        )
        fig_hora.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(title_font_color="gray", font_color="gray"),
            xaxis=dict(title_font_color="gray", tickfont_color="gray"),
            yaxis=dict(title_font_color="gray", tickfont_color="gray")
        )
        st.plotly_chart(fig_hora, use_container_width=True)

    with col_dia:
        rep_dia = df_filtrado.groupby(['Dia_Semana', 'Asistencia']).size().reset_index(name='Citas')
        fig_dia = px.bar(
            rep_dia,
            x='Dia_Semana',
            y='Citas',
            color='Asistencia',
            title="Demanda por Día de la Semana",
            barmode='group',
            color_discrete_map={'Asiste': SECONDARY_INDIGO, 'No Asiste': PRIMARY_CYAN},
            category_orders={'Dia_Semana': dias_ordenados},
            labels={'Citas': 'Cantidad de Citas', 'Dia_Semana': 'Día', 'Asistencia': 'Estado'}
        )
        fig_dia.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(title_font_color="gray", font_color="gray"),
            xaxis=dict(title_font_color="gray", tickfont_color="gray"),
            yaxis=dict(title_font_color="gray", tickfont_color="gray")
        )
        st.plotly_chart(fig_dia, use_container_width=True)

    st.markdown("---")

    # 5. Tablas Desglosadas
    st.subheader("Tablas Detalladas")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Origen x Servicio",
        "Prestador x Servicio",
        "Por Hora Cerrada",
        "Por Servicio",
        "Por Prestador"
    ])

    with tab1:
        st.dataframe(generar_reporte_origen_servicio(df_filtrado), use_container_width=True)

    with tab2:
        st.dataframe(generar_reporte_prestador_servicio(df_filtrado), use_container_width=True)

    with tab3:
        st.dataframe(generar_reporte_por_hora_cerrada(df_filtrado), use_container_width=True)

    with tab4:
        st.dataframe(generar_reporte_servicios(df_filtrado), use_container_width=True)

    with tab5:
        st.dataframe(generar_reporte_prestadores(df_filtrado), use_container_width=True)

else:
    st.info("👈 Sube el archivo Excel en la barra lateral para generar el panel analítico.")