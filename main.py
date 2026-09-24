import os
import pandas as pd
from src.transform import cargar_y_convertir_excel, agregar_columnas_calculadas
from src.utils import obtener_ultimo_archivo_excel
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


def main():
    try:
        # 1. Obtener y transformar datos
        path_excel = obtener_ultimo_archivo_excel('data')
        print(f"📂 Archivo detectado: {path_excel}")

        df = cargar_y_convertir_excel(path_excel)
        df_procesado = agregar_columnas_calculadas(df)

        # 2. Generar todos los reportes solicitados por el cliente
        print("📊 Generando reportes analíticos...")
        rep_prestadores = generar_reporte_prestadores(df_procesado)
        rep_servicios = generar_reporte_servicios(df_procesado)
        rep_origen = generar_reporte_origen(df_procesado)
        rep_p_s = generar_reporte_prestador_servicio(df_procesado)
        rep_o_s = generar_reporte_origen_servicio(df_procesado)
        rep_hora = generar_reporte_por_hora_cerrada(df_procesado)
        rep_dia = generar_reporte_dia_semana(df_procesado)
        rep_turno = generar_reporte_turno(df_procesado)

        # 3. Guardar en disco
        os.makedirs('output', exist_ok=True)
        path_csv_salida = os.path.join('output', 'reservas_procesadas.csv')
        path_reporte_excel = os.path.join('output', 'resumen_ejecutivo.xlsx')

        # Guardar CSV procesado
        df_procesado.to_csv(path_csv_salida, index=False, encoding='utf-8-sig')

        # Guardar Excel con pestañas desglosadas
        with pd.ExcelWriter(path_reporte_excel, engine='openpyxl') as writer:
            rep_prestadores.to_excel(writer, sheet_name='Por Prestador', index=False)
            rep_servicios.to_excel(writer, sheet_name='Por Servicio', index=False)
            rep_p_s.to_excel(writer, sheet_name='Prestador x Servicio', index=False)
            rep_o_s.to_excel(writer, sheet_name='Origen x Servicio', index=False)
            rep_hora.to_excel(writer, sheet_name='Por Hora Cerrada', index=False)
            rep_dia.to_excel(writer, sheet_name='Por Dia Semana', index=False)
            rep_turno.to_excel(writer, sheet_name='Por Turno', index=False)
            rep_origen.to_excel(writer, sheet_name='Por Origen', index=False)

        print(f"✅ ¡Proceso completado con éxito!")
        print(f"📄 CSV procesado: {path_csv_salida}")
        print(f"📊 Excel ejecutivo con 8 pestañas: {path_reporte_excel}")

    except Exception as error:
        print(f"⚠️ Ocurrió un error durante la ejecución: {error}")


if __name__ == '__main__':
    main()