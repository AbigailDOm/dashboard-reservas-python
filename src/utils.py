import glob
import os


def obtener_ultimo_archivo_excel(carpeta_data: str = 'data') -> str:
    """
    Busca y devuelve la ruta del archivo .xlsx más reciente dentro de la carpeta indicada.
    Si no encuentra ninguno, lanza un error claro.
    """
    patron_busqueda = os.path.join(carpeta_data, '*.xlsx')
    archivos = glob.glob(patron_busqueda)

    if not archivos:
        raise FileNotFoundError(f"❌ No se encontraron archivos .xlsx en la carpeta '{carpeta_data}'.")

    # Ordenar archivos por fecha de última modificación (el más reciente al final)
    archivo_mas_reciente = max(archivos, key=os.path.getmtime)
    return archivo_mas_reciente