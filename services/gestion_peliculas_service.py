from services.api_client import consumir_api

def obtener_peliculas():
    """Obtiene las películas de la cartelera desde el backend."""
    return consumir_api(
        metodo="GET",
        endpoint="/peliculas/cartelera"
    )


def obtener_pelicula(pelicula_id):
    """Obtiene los detalles de una película específica."""
    return consumir_api(
        metodo="GET",
        endpoint=f"/peliculas/{pelicula_id}"
    )


def buscar_peliculas_tmdb(token, titulo):
    """Busca películas en TMDB mediante el backend."""
    if not token:
        return 401, {
            "ok": False,
            "error": {
                "code": 401,
                "message": "Debés iniciar sesión como administrador."
            }
        }

    if not titulo or not titulo.strip():
        return 400, {
            "ok": False,
            "error": {
                "code": 400,
                "message": "Ingresá un título para buscar."
            }
        }

    return consumir_api(
        metodo="GET",
        endpoint="/peliculas/buscar-externa",
        params={
            "titulo": titulo.strip()
        },
        headers={
            "Authorization": f"Bearer {token}"
        }
    )


def crear_pelicula(
    token,
    titulo,
    sinopsis,
    poster,
    duracion,
    clasificacion,
    genero
):
    """Solicita al backend la creación de una película."""

    if not token:
        return 401, {
            "ok": False,
            "error": {
                "code": 401,
                "message": "Debés iniciar sesión como administrador."
            }
        }

    datos = {
        "titulo": titulo,
        "sinopsis": sinopsis,
        "poster": poster,
        "duracion": duracion,
        "clasificacion": clasificacion,
        "genero": genero
    }

    return consumir_api(
        metodo="POST",
        endpoint="/peliculas",
        datos=datos,
        headers={
            "Authorization": f"Bearer {token}"
        }
    )
