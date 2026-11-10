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
    return consumir_api("GET", "/auth/usuarios/me", headers={"Authorization": f"Bearer {token}"})


def cerrar_sesion(token):
    return consumir_api("POST", "/auth/logout", headers={"Authorization": f"Bearer {token}"})
