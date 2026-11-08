from services.api_client import consumir_api


def obtener_servicios():
    """Obtiene el listado de servicios activos desde el backend."""
    return consumir_api("GET", "/servicios")


def crear_servicio(token, nombre, descripcion, precio):
    """Solicita al backend la creación de un servicio. Requiere autenticación de administrador."""

    if not token:
        return 401, {
            "ok": False,
            "error": {
                "code": 401,
                "message": "Debés iniciar sesión para gestionar servicios."
            }
        }

    datos = {
        "nombre": nombre,
        "descripcion": descripcion,
        "precio": precio
    }

    return consumir_api(
        metodo="POST",
        endpoint="/servicios",
        datos=datos,
        headers={
            "Authorization": f"Bearer {token}"
        }
    )


def actualizar_servicio(token, servicio_id, nombre, descripcion, precio):
    """Solicita al backend la modificación de un servicio existente."""

    if not token:
        return 401, {
            "ok": False,
            "error": {
                "code": 401,
                "message": "Debés iniciar sesión para gestionar servicios."
            }
        }

    datos = {
        "nombre": nombre,
        "descripcion": descripcion,
        "precio": precio
    }

    return consumir_api(
        metodo="PUT",
        endpoint=f"/servicios/{servicio_id}",
        datos=datos,
        headers={
            "Authorization": f"Bearer {token}"
        }
    )


def desactivar_servicio(token, servicio_id):
    """Solicita al backend la baja de un servicio existente."""

    if not token:
        return 401, {
            "ok": False,
            "error": {
                "code": 401,
                "message": "Debés iniciar sesión para gestionar servicios."
            }
        }

    return consumir_api(
        metodo="DELETE",
        endpoint=f"/servicios/{servicio_id}",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )