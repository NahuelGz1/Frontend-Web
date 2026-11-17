from services.api_client import consumir_api


def obtener_servicios():
    return consumir_api("GET", "/servicios?incluir_inactivos=1")


def _sin_sesion():
    return 401, {"ok": False, "error": {"code": 401, "message": "Debés iniciar sesión para gestionar servicios."}}


def crear_servicio(token, nombre, descripcion, precio, categoria, imagen_url=None):
    if not token:
        return _sin_sesion()
    return consumir_api(
        "POST",
        "/servicios",
        datos={"nombre": nombre, "descripcion": descripcion, "precio": precio,
               "categoria": categoria, "imagen_url": imagen_url},
        headers={"Authorization": "Bearer " + token},
    )


def actualizar_servicio(token, servicio_id, nombre, descripcion, precio, categoria, imagen_url=None):
    if not token:
        return _sin_sesion()
    return consumir_api(
        "PUT",
        f"/servicios/{servicio_id}",
        datos={"nombre": nombre, "descripcion": descripcion, "precio": precio,
               "categoria": categoria, "imagen_url": imagen_url},
        headers={"Authorization": "Bearer " + token},
    )


def desactivar_servicio(token, servicio_id):
    if not token:
        return _sin_sesion()
    return consumir_api(
        "DELETE",
        f"/servicios/{servicio_id}",
        headers={"Authorization": "Bearer " + token},
    )


def cambiar_estado_servicio(token, servicio_id, activo):
    if not token:
        return _sin_sesion()
    return consumir_api(
        "PATCH",
        f"/servicios/{servicio_id}/estado",
        datos={"activo": activo},
        headers={"Authorization": "Bearer " + token},
    )
