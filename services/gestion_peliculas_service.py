from services.api_client import consumir_api


def obtener_peliculas():
    return consumir_api("GET", "/peliculas/admin")


def cambiar_estado_pelicula(token, pelicula_id, activo):
    return consumir_api(
        "PATCH",
        f"/peliculas/{pelicula_id}/estado",
        datos={"activo": activo},
        headers={"Authorization": "Bearer " + token},
    )


def eliminar_pelicula(token, pelicula_id):
    return consumir_api(
        "DELETE",
        f"/peliculas/{pelicula_id}",
        headers={"Authorization": "Bearer " + token},
    )


def obtener_pelicula(pelicula_id):
    return consumir_api("GET", f"/peliculas/{pelicula_id}")


def buscar_peliculas_tmdb(token, titulo):
    if not token:
        return 401, {"ok": False, "error": {"code": 401, "message": "Debés iniciar sesión como administrador."}}
    if not titulo or not titulo.strip():
        return 400, {"ok": False, "error": {"code": 400, "message": "Ingresá un título para buscar."}}
    return consumir_api(
        "GET",
        "/peliculas/buscar-externa",
        params={"titulo": titulo.strip()},
        headers={"Authorization": "Bearer " + token},
    )


def crear_pelicula(token, titulo, sinopsis, poster, duracion, clasificacion, genero):
    if not token:
        return 401, {"ok": False, "error": {"code": 401, "message": "Debés iniciar sesión como administrador."}}
    return consumir_api(
        "POST",
        "/peliculas",
        datos={"titulo": titulo, "sinopsis": sinopsis, "poster": poster,
               "duracion": duracion, "clasificacion": clasificacion, "genero": genero},
        headers={"Authorization": "Bearer " + token},
    )
