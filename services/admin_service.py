from services.api_client import consumir_api


def habilitar_administrador(email):
    return consumir_api("POST", "/auth/usuarios/admins", datos={"email": email})


def obtener_administradores():
    return consumir_api("GET", "/auth/usuarios/admins")


def dar_de_baja_administrador(id_usuario):
    return consumir_api("DELETE", f"/auth/usuarios/admins/{id_usuario}")
