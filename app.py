import io
import psutil
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit_authenticator as stauth
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
from src.database import (
    inicializar_bd,
    registrar_actividad,
    guardar_reservas_en_bd,
    cargar_reservas_desde_bd,
    DB_NAME
)
import sqlite3

# Configuración de página (Debe ser lo primero de todo)
st.set_page_config(
    page_title="Panel Analítico de Reservas IMO",
    layout="wide"
)

# ==========================================
# 🔐 CONFIGURACIÓN DEL SISTEMA DE LOGIN
# ==========================================
try:
    inicializar_bd()

    # Cargamos las credenciales directamente desde st.secrets
    credentials = {
        "usernames": {
            username: dict(user_data)
            for username, user_data in st.secrets["credentials"]["usernames"].items()
        }
    }
except Exception as e:
    st.error(f"⚠️ Error crítico al cargar secretos: {e}")
    st.stop()

# Inicializamos el autenticador permitiendo el manejo automático de contraseñas de la versión actual
authenticator = stauth.Authenticate(
    credentials,
    cookie_name="imo_dashboard_cookie",
    key="imo_super_secret_key",
    cookie_expiry_days=1
)

if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
    st.session_state['name'] = None
    st.session_state['username'] = None

# Formulario de Login Corporativo Unificado
if st.session_state['authentication_status'] != True:
    _, col_centro, _ = st.columns([1, 1.2, 1])

    with col_centro:
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
            <style>
                [data-testid="stForm"] {
                    background-color: var(--background-secondary-color);
                    padding: 30px;
                    border-radius: 16px;
                    border: 1px solid rgba(128, 128, 128, 0.2);
                    box-shadow: 0px 6px 16px rgba(0, 0, 0, 0.08);
                }
            </style>
        """, unsafe_allow_html=True)

        with st.form("form_login_unificado"):
            st.markdown("<h2 style='text-align: center; margin-bottom: 0px;'>Iniciar Sesión</h2>",
                        unsafe_allow_html=True)
            st.markdown(
                "<p style='text-align: center; color: gray; font-size: 14px; margin-top: 5px; margin-bottom: 25px;'>Panel Analítico Institucional (IMO)</p>",
                unsafe_allow_html=True)

            email_ingresado = st.text_input("Correo Institucional", placeholder="usuario@imo.com.mx")
            password_ingresada = st.text_input("Contraseña", type="password", placeholder="••••••••")

            st.markdown("<br>", unsafe_allow_html=True)
            submit_login = st.form_submit_button("Iniciar Sesión", use_container_width=True)

            if submit_login:
                if email_ingresado in credentials["usernames"]:
                    stored_password = credentials["usernames"][email_ingresado]["password"]

                    # Verificamos la contraseña en texto plano contra el hash almacenado usando la herramienta de la librería
                    password_valida = False
                    try:
                        password_valida = stauth.Hasher.check_pw(password_ingresada, stored_password)
                    except Exception:
                        # Fallback por si la contraseña en secrets estuviera accidentalmente en texto plano
                        password_valida = (password_ingresada == stored_password)

                    if password_valida:
                        st.session_state['authentication_status'] = True
                        st.session_state['name'] = credentials["usernames"][email_ingresado]["name"]
                        st.session_state['username'] = email_ingresado

                        registrar_actividad(email_ingresado, st.session_state['name'], "LOGIN",
                                            "Inicio de sesión exitoso")
                        st.rerun()
                    else:
                        st.error("❌ Contraseña incorrecta.")
                else:
                    st.error("🚫 El correo ingresado no está autorizado.")

        if st.session_state['authentication_status'] == False:
            st.warning("Por favor, verifica tus credenciales.")

    st.stop()

else:
    # -------------------------------------------------------------------------
    # SESIÓN ACTIVA: BARRA LATERAL Y NAVEGACIÓN ADMINISTRATIVA
    # -------------------------------------------------------------------------
    username = st.session_state['username']
    name = st.session_state['name']

    st.sidebar.markdown(f"*{name}*")

    modo_vista = "Tablero Analítico"
    if username == "vanessa.dominguez@imoiap.com.mx":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Panel de Administrador")
        modo_vista = st.sidebar.radio("Sección:",
                                      ["Tablero Analítico", "Cargar Reporte AgendaPro", "Bitácora de Auditoría"])

    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        registrar_actividad(username, name, "LOGOUT", "Cierre de sesión")
        st.session_state['authentication_status'] = None
        st.session_state['name'] = None
        st.session_state['username'] = None
        st.rerun()

    st.sidebar.markdown("---")

    # -------------------------------------------------------------------------
    # VISTA 1: CARGAR REPORTE AGENDAPRO (Solo Administrador)
    # -------------------------------------------------------------------------
    if modo_vista == "Cargar Reporte AgendaPro" and username == "v.dominguez@imo.com.mx":
        st.title("Ingesta de Datos (AgendaPro)")
        st.markdown(
            "Sube los reportes en Excel para alimentar la base de datos central de la institución. Los datos se acumularán de forma histórica.")

        archivo_admin = st.file_uploader("Selecciona el archivo Excel (.xlsx)", type=["xlsx"])

        if archivo_admin is not None:
            if st.button("Procesar e Inyectar a la Base de Datos", type="primary"):
                with st.spinner("Procesando y guardando registros en SQL..."):
                    try:
                        df_raw = cargar_y_convertir_excel(archivo_admin)
                        df_proc = agregar_columnas_calculadas(df_raw)
                        guardar_reservas_en_bd(df_proc)

                        registrar_actividad(username, name, "CARGA_DATOS",
                                            f"Se inyectaron {len(df_proc)} registros desde Excel")
                        st.success(
                            f"✅ ¡Se han cargado e inyectado exitosamente **{len(df_proc):,d}** registros a la base de datos!")
                    except Exception as e:
                        st.error(f"❌ Error al procesar el archivo: {e}")

        st.markdown("---")
        if st.button("⚠️ Reiniciar / Vaciar Base de Datos de Reservas"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reservas")
            conn.commit()
            conn.close()
            registrar_actividad(username, name, "RESET_BD", "Se vació la tabla de reservas")
            st.warning("La base de datos de reservas ha sido vaciada.")

        st.stop()

    # -------------------------------------------------------------------------
    # VISTA 2: BITÁCORA DE AUDITORÍA (Solo Administrador)
    # -------------------------------------------------------------------------
    if modo_vista == "Bitácora de Auditoría" and username == "v.dominguez@imo.com.mx":
        st.title("Bitácora de Auditoría y Actividad")
        st.markdown("Monitoreo en tiempo real de los accesos y movimientos de los usuarios en la plataforma.")

        try:
            conn = sqlite3.connect(DB_NAME)
            df_auditoria = pd.read_sql("SELECT * FROM auditoria ORDER BY id DESC", conn)
            conn.close()

            col_a, col_b = st.columns(2)
            col_a.metric("Total de Movimientos Registrados", len(df_auditoria))
            col_b.metric("Usuarios Distintos Activos",
                         df_auditoria['username'].nunique() if not df_auditoria.empty else 0)

            st.markdown("---")
            st.dataframe(df_auditoria, use_container_width=True)
        except Exception as e:
            st.error(f"Error al cargar la bitácora: {e}")

        st.stop()


    # -------------------------------------------------------------------------
    # VISTA 3: TABLERO ANALÍTICO PRINCIPAL (Con lectura automática desde SQL)
    # -------------------------------------------------------------------------

    @st.cache_data(show_spinner="Generando reporte ejecutivo...")
    def generar_excel_resumen_ejecutivo(df_filtrado: pd.DataFrame) -> bytes:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            generar_reporte_prestadores(df_filtrado).to_excel(writer, sheet_name='Por Prestador', index=False)
            generar_reporte_servicios(df_filtrado).to_excel(writer, sheet_name='Por Servicio', index=False)
            generar_reporte_prestador_servicio(df_filtrado).to_excel(writer, sheet_name='Prestador x Servicio',
                                                                     index=False)
            generar_reporte_origen_servicio(df_filtrado).to_excel(writer, sheet_name='Origen x Servicio', index=False)
            generar_reporte_por_hora_cerrada(df_filtrado).to_excel(writer, sheet_name='Por Hora Cerrada', index=False)
            generar_reporte_dia_semana(df_filtrado).to_excel(writer, sheet_name='Por Dia Semana', index=False)
            generar_reporte_turno(df_filtrado).to_excel(writer, sheet_name='Por Turno', index=False)
            generar_reporte_origen(df_filtrado).to_excel(writer, sheet_name='Por Origen', index=False)

        buffer.seek(0)
        return buffer.getvalue()


    # Inyección CSS limpia
    st.markdown("""
        <style>
        [data-testid="stMetric"] {
            background-color: var(--background-secondary-color) !important;
            padding: 18px;
            border-radius: 16px;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(128, 128, 128, 0.2) !important;
        }
        [data-testid="stMetricLabel"] label, 
        [data-testid="stMetricLabel"] p,
        [data-testid="stMetricLabel"] span {
            color: var(--text-color) !important;
            font-weight: 600 !important;
            font-size: 14px !important;
        }
        [data-testid="stMetricValue"] div, 
        [data-testid="stMetricValue"] p,
        [data-testid="stMetricValue"] span {
            color: var(--text-color) !important;
            font-weight: 700 !important;
        }
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

    # CARGAMOS LOS DATOS DIRECTAMENTE DESDE LA BASE DE DATOS SQL
    df_procesado = cargar_reservas_desde_bd()

    if not df_procesado.empty:
        if 'consulta_registrada' not in st.session_state:
            registrar_actividad(username, name, "CONSULTA_TABLERO",
                                f"Visualizó tablero con {len(df_procesado)} registros en SQL")
            st.session_state['consulta_registrada'] = True

        # Sidebar Filtros Operativos
        st.sidebar.header("Filtros Operativos")

        min_date = df_procesado['Fecha de realización'].min().date()
        max_date = df_procesado['Fecha de realización'].max().date()
        rango_fechas = st.sidebar.date_input(
            "Selecciona el periodo:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        dias_ordenados = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        dias_presentes = [d for d in dias_ordenados if d in df_procesado['Dia_Semana'].unique()]
        dia_seleccionado = st.sidebar.multiselect("Día de la Semana:", options=dias_presentes, default=dias_presentes)

        turnos_disponibles = sorted(df_procesado['Turno'].dropna().unique().tolist())
        turno_seleccionado = st.sidebar.multiselect("Turno Horario:", options=turnos_disponibles,
                                                    default=turnos_disponibles)

        prestadores_disponibles = ["Todos"] + sorted(df_procesado['Prestador'].dropna().unique().tolist())
        prestador_seleccionado = st.sidebar.selectbox("Prestador:", prestadores_disponibles)

        servicios_disponibles = sorted(df_procesado['Servicio'].dropna().unique().tolist())
        servicios_seleccionados = st.sidebar.multiselect("Servicio(s):", options=servicios_disponibles,
                                                         default=servicios_disponibles)

        origen_disponibles = ["Todos"] + sorted(df_procesado['Origen_Resumen'].dropna().unique().tolist())
        origen_seleccionado = st.sidebar.selectbox("Origen:", origen_disponibles)

        # Aplicar Filtros
        if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
            fecha_inicio, fecha_fin = rango_fechas
        else:
            fecha_inicio = fecha_fin = min_date

        df_filtrado = df_procesado[
            (df_procesado['Fecha de realización'].dt.date >= fecha_inicio) &
            (df_procesado['Fecha de realización'].dt.date <= fecha_fin) &
            (df_procesado['Dia_Semana'].isin(dia_seleccionado)) &
            (df_procesado['Turno'].isin(turno_seleccionado)) &
            (df_procesado['Servicio'].isin(servicios_seleccionados))
            ]

        if prestador_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Prestador'] == prestador_seleccionado]

        if origen_seleccionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Origen_Resumen'] == origen_seleccionado]

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

        # Tarjetas KPIs
        st.subheader("Indicadores Clave")
        col1, col2, col3, col4, col5 = st.columns(5)

        total_reservas = len(df_filtrado)
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
        # INSIGHTS INTELIGENTES ADAPTATIVOS
        # ==========================================
        st.subheader("Hallazgos Clave del Periodo Seleccionado")

        if not df_filtrado.empty:
            rep_serv_insight = generar_reporte_servicios(df_filtrado)

            if not rep_serv_insight.empty:
                total_servicios_analizados = len(rep_serv_insight)
                peor_pct_row = rep_serv_insight.sort_values(by='% Inasistencia', ascending=False).iloc[0]
                servicio_pct_alto = peor_pct_row['Servicio']
                pct_alto = peor_pct_row['% Inasistencia']

                peor_vol_row = rep_serv_insight.sort_values(by='Inasistencias', ascending=False).iloc[0]
                servicio_vol_alto = peor_vol_row['Servicio']
                vol_alto = peor_vol_row['Inasistencias']
            else:
                total_servicios_analizados = 0
                servicio_pct_alto, pct_alto = "N/A", 0
                servicio_vol_alto, vol_alto = "N/A", 0

            mostrar_prestador_insight = False
            nombre_prestador, total_atendidos_prestador = "N/A", 0

            if prestador_seleccionado == "Todos":
                rep_prest_insight = generar_reporte_prestadores(df_filtrado)
                if len(rep_prest_insight) > 1:
                    prestador_bajo = rep_prest_insight.sort_values(by='Atendidos', ascending=True).iloc[0]
                    nombre_prestador = prestador_bajo['Prestador']
                    total_atendidos_prestador = prestador_bajo['Atendidos']
                    mostrar_prestador_insight = True

            rep_dia_insight = generar_reporte_dia_semana(df_filtrado)
            if not rep_dia_insight.empty:
                peor_dia = rep_dia_insight.sort_values(by='Inasistencias', ascending=False).iloc[0]
                nombre_dia = peor_dia['Dia_Semana']
                total_inasistencias_dia = peor_dia['Inasistencias']
            else:
                nombre_dia = "N/A"
                total_inasistencias_dia = 0

            if total_servicios_analizados > 1:
                texto_severidad = f"**Severidad del Comportamiento (% Crítico):** El servicio **{servicio_pct_alto}** presenta el porcentaje más alto de inasistencia con un **{pct_alto}%**." if pct_alto > 0 else f"**Desempeño Destacado:** El servicio **{servicio_pct_alto}** registra un **0.0% de inasistencia**."
                texto_volumen = f"**Impacto Operativo Real:** El servicio **{servicio_vol_alto}** acumula **{vol_alto:,d}** citas perdidas." if vol_alto > 0 else f"**Impacto Operativo Real:** No se registran citas perdidas."
            else:
                texto_severidad = f"**Comportamiento del Servicio:** El servicio analizado (**{servicio_pct_alto}**) registra una inasistencia del **{pct_alto}%**." if pct_alto > 0 else f"**Comportamiento del Servicio:** El servicio analizado (**{servicio_pct_alto}**) registra **0.0% de inasistencia**."
                texto_volumen = f"**Volumen Operativo:** El servicio acumula **{vol_alto:,d}** citas perdidas." if vol_alto > 0 else f"**Volumen Operativo:** Operación con saldo blanco sin citas perdidas."

            texto_dia = f"**Día con mayor ausentismo:** El día **{nombre_dia}** suma **{total_inasistencias_dia:,d}** casos." if total_inasistencias_dia > 0 else f"**Análisis por Día:** Sin inasistencias significativas distribuidas."

            viñetas = [f"* {texto_severidad}", f"* {texto_volumen}"]
            if mostrar_prestador_insight:
                viñetas.append(
                    f"**Prestador con menor flujo efectivo:** **{nombre_prestador}** con **{total_atendidos_prestador:,d}** citas en espera.")
            viñetas.append(f"* {texto_dia}")

            st.info(f"**Resumen Ejecutivo Dinámico:**\n\n" + "\n".join(viñetas))
        else:
            st.warning("⚠️ No hay datos disponibles para los filtros seleccionados.")

        st.markdown("---")

        # Gráficos
        st.subheader("Distribución Operativa")
        col_hora, col_dia = st.columns(2)

        with col_hora:
            rep_hora = generar_reporte_por_hora_cerrada(df_filtrado).rename(
                columns={'Atendidos': 'Asiste', 'Inasistencias': 'No Asiste'})
            fig_hora = px.bar(
                rep_hora, x='Hora_Bloque', y=['Asiste', 'No Asiste'],
                title="Asistencias e Inasistencias por Bloque Horario", barmode='stack',
                color_discrete_map={'Asiste': "#4A52C8", 'No Asiste': "#4CB5E5"}
            )
            fig_hora.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_hora, use_container_width=True)

        with col_dia:
            rep_dia = df_filtrado.groupby(['Dia_Semana', 'Asistencia']).size().reset_index(name='Citas')
            fig_dia = px.bar(
                rep_dia, x='Dia_Semana', y='Citas', color='Asistencia',
                title="Demanda por Día de la Semana", barmode='group',
                color_discrete_map={'Asiste': "#4A52C8", 'No Asiste': "#4CB5E5"},
                category_orders={
                    'Dia_Semana': ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']}
            )
            fig_dia.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_dia, use_container_width=True)

        st.markdown("---")

        # Tablas Detalladas
        st.subheader("Tablas Detalladas")
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["Origen x Servicio", "Prestador x Servicio", "Por Hora Cerrada", "Por Servicio", "Por Prestador"]
        )
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
        st.warning("⚠️ La base de datos de reservas está vacía.")
        if username == "v.dominguez@imo.com.mx":
            st.info(
                "👈 Ve a la sección **'Cargar Reporte AgendaPro'** en el menú lateral para subir el archivo inicial.")
        else:
            st.info(
                "ℹ️ Por favor, contacta al administrador del sistema para que cargue los reportes iniciales en la base de datos.")