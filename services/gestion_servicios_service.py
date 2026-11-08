from services.api_client import consumir_api


def obtener_servicios():
    """Obtiene el listado de servicios activos desde el backend."""
    return consumir_api("GET", "/servicios")