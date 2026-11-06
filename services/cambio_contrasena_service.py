from services.api_client import consumir_api


def solicitar_cambio_contrasena(token, contrasena_actual, contrasena_nueva):
    """
    Solicita al backend el cambio de contraseña de un usuario autenticado.
    """

    if not token:
        return 401, {
            "ok": False,
            "error": {
                "code": 401,
                "message": "Debés iniciar sesión para cambiar tu contraseña."
            }
        }

    return consumir_api(
        metodo="PATCH",
        endpoint="/auth/usuarios/me/password",
        datos={
            "contrasena_actual": contrasena_actual,
            "contrasena_nueva": contrasena_nueva
        },
        headers={
            "Authorization": f"Bearer {token}"
        }
    )