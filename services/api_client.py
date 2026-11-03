import os
import requests

# URL base del servidor backend (obtenida del .env o valor por defecto)
BACKEND_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:5000/api")

def consumir_api(metodo, endpoint, datos=None, params=None, headers=None):
    """
    Función helper centralizada para realizar peticiones HTTP al backend
    respetando los principios REST mediante la biblioteca 'requests'.

    :param metodo: Método HTTP ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')
    :param endpoint: Ruta relativa del backend (ej: '/compras/validar-qr')
    :param datos: Diccionario Python que se enviará serializado como JSON (body)
    :param params: Diccionario con parámetros de consulta para la URL (?key=val)
    :param headers: Cabeceras HTTP adicionales (ej: Authorization)
    :return: Tupla (status_code: int, respuesta_json: dict)
    """
    # Formatear la URL final asegurando la barra inicial
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    url = f"{BACKEND_URL}{endpoint}"

    # Cabeceras estándar para envío y recepción de JSON
    headers_base = {"Content-Type": "application/json"}
    if headers:
        headers_base.update(headers)

    try:
        # Petición HTTP síncrona
        response = requests.request(
            method=metodo.upper(),
            url=url,
            json=datos,
            params=params,
            headers=headers_base,
            timeout=10  # Tiempo máximo de espera en segundos
        )

        # Si el backend responde con contenido JSON, lo parseamos
        try:
            respuesta_data = response.json()
        except ValueError:
            # En caso de que la respuesta no sea JSON (ej. un error 500 crudo de Flask)
            respuesta_data = {
                "ok": False,
                "error": {
                    "code": response.status_code,
                    "message": "La respuesta del servidor no tiene formato JSON válido."
                }
            }

        return response.status_code, respuesta_data

    except requests.exceptions.ConnectionError:
        # Error al no poder conectar con el servidor (backend apagado o URL errónea)
        return 500, {
            "ok": False,
            "error": {
                "code": 500,
                "message": "No se pudo establecer conexión con el servidor backend. Verifique que esté en ejecución."
            }
        }
    except requests.exceptions.Timeout:
        # El backend tardó demasiado en responder
        return 504, {
            "ok": False,
            "error": {
                "code": 504,
                "message": "El servidor backend tardó demasiado tiempo en responder (Timeout)."
            }
        }
    except requests.exceptions.RequestException as e:
        # Cualquier otro error genérico de la librería requests
        return 500, {
            "ok": False,
            "error": {
                "code": 500,
                "message": f"Error en la petición HTTP: {str(e)}"
            }
        }