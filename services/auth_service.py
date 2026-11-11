from services.api_client import consumir_api


def iniciar_sesion(email, password):
    return consumir_api("POST", "/auth/login", datos={"email": email, "password": password})


def registrar(nombre, email, password):
    return consumir_api("POST", "/auth/register", datos={
        "nombre": nombre, "email": email, "password": password,
    })


def recuperar(email):
    return consumir_api("POST", "/auth/forgot-password", datos={"email": email})


def restablecer(token, password):
    return consumir_api("POST", "/auth/reset-password", datos={"token": token, "password": password})


def perfil(token):
    return consumir_api("GET", "/auth/usuarios/me", headers={"Authorization": "Bearer " + token})


def cerrar_sesion(token):
    return consumir_api("POST", "/auth/logout", headers={"Authorization": "Bearer " + token})

def cambiar_contrasena(token, contrasena_actual, contrasena_nueva):
    return consumir_api(
        "PATCH",
        "/auth/usuarios/me/password",
        datos={
            "contrasena_actual": contrasena_actual,
            "contrasena_nueva": contrasena_nueva,
        },
        headers={"Authorization": f"Bearer {token}"},
    )


def actualizar_perfil(token, nombre, email):
    return consumir_api(
        "PATCH",
        "/auth/usuarios/me",
        datos={"nombre": nombre, "email": email},
        headers={"Authorization": f"Bearer {token}"},
    )