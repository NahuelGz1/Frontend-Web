import requests
from flask import current_app, has_request_context, session


def consumir_api(metodo, endpoint, datos=None, params=None, headers=None):
    url = current_app.config["API_BASE_URL"].rstrip("/") + "/" + endpoint.lstrip("/")
    cabeceras = {"Accept": "application/json"}
    if has_request_context() and session.get("access_token"):
        cabeceras["Authorization"] = f"Bearer {session['access_token']}"
    if headers:
        cabeceras.update(headers)
    try:
        response = requests.request(
            method=metodo.upper(), url=url, json=datos, params=params,
            headers=cabeceras, timeout=10, allow_redirects=False,
        )
    except requests.exceptions.Timeout:
        current_app.logger.warning("Tiempo de espera agotado al consultar la API")
        return error_api(504, "El servidor tardó demasiado. Intentá nuevamente.")
    except requests.exceptions.RequestException:
        current_app.logger.warning("No se pudo conectar con la API")
        return error_api(503, "No se pudo conectar con el servidor. Intentá más tarde.")
    try:
        contenido = response.json()
    except ValueError:
        current_app.logger.error("Respuesta no JSON de la API (HTTP %s)", response.status_code)
        return error_api(502, "El servidor devolvió una respuesta inválida.")
    if not isinstance(contenido, dict) or not isinstance(contenido.get("ok"), bool):
        current_app.logger.error("Contrato JSON inválido de la API")
        return error_api(502, "El servidor devolvió una respuesta inválida.")
    if 300 <= response.status_code < 400 or (response.status_code < 400) != contenido["ok"]:
        current_app.logger.error("Estado HTTP inconsistente con la respuesta de la API")
        return error_api(502, "El servidor devolvió una respuesta inválida.")
    return response.status_code, contenido


def error_api(codigo, mensaje):
    return codigo, {"ok": False, "error": {"code": codigo, "message": mensaje}}
