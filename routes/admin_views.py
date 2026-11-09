import secrets
from flask import Blueprint, render_template, request, url_for, redirect, session
from services.api_client import consumir_api
from services.gestion_servicios_service import obtener_servicios
from services.gestion_servicios_service import crear_servicio
from services.gestion_servicios_service import actualizar_servicio
from services.gestion_servicios_service import desactivar_servicio
from services.gestion_peliculas_service import obtener_peliculas
from services.gestion_peliculas_service import buscar_peliculas_tmdb
from services.gestion_peliculas_service import crear_pelicula

admin_views = Blueprint("admin_views", __name__, url_prefix="/admin")

@admin_views.route("/estadisticas")
def estadisticas():
    return render_template("admin/estadisticas.html")




@admin_views.route("/peliculas", methods=["GET", "POST"])
def peliculas():
    mensaje = session.pop("mensaje_peliculas", None)

    buscar = request.args.get("buscar", "").strip()
    titulo_tmdb = request.args.get("tmdb_buscar", "").strip()

    tmdb_abierto = (
        request.args.get("tmdb") == "1"
        or "tmdb_buscar" in request.args
    )

    resultados_tmdb = []
    error_tmdb = None

    # Token CSRF para proteger los formularios
    csrf_actual = session.get("csrf_peliculas")

    if not csrf_actual:
        csrf_actual = secrets.token_urlsafe(32)
        session["csrf_peliculas"] = csrf_actual

    # 1. Procesar la creación de una película
    if request.method == "POST":
        tmdb_abierto = True

        csrf_recibido = request.form.get("csrf_token", "")
        accion = request.form.get("accion")

        if not secrets.compare_digest(csrf_recibido, csrf_actual):
            mensaje = "Formulario inválido. Recargá la página."

        elif accion == "crear_tmdb":
            token = session.get("token")

            titulo = request.form.get("titulo", "").strip()
            sinopsis = request.form.get("sinopsis", "").strip()
            poster = request.form.get("poster", "").strip()
            genero = request.form.get("genero", "").strip()
            clasificacion = request.form.get("clasificacion", "")

            try:
                duracion = int(request.form.get("duracion", ""))
            except (ValueError, TypeError):
                duracion = 0

            if not token:
                mensaje = "Debés iniciar sesión como administrador."

            elif not titulo or len(titulo) > 150:
                mensaje = "Ingresá un título válido."

            elif not genero or len(genero) > 50:
                mensaje = "Ingresá un género válido."

            elif duracion < 1 or duracion > 999:
                mensaje = "La duración debe estar entre 1 y 999 minutos."

            elif clasificacion not in ("ATP", "+13", "+16", "+18"):
                mensaje = "Seleccioná una clasificación válida."

            elif len(poster) > 255:
                mensaje = "La URL del póster es demasiado larga."

            else:
                estado_creacion, respuesta_creacion = crear_pelicula(
                    token=token,
                    titulo=titulo,
                    sinopsis=sinopsis or None,
                    poster=poster or None,
                    duracion=duracion,
                    clasificacion=clasificacion,
                    genero=genero
                )

                if estado_creacion == 201 and respuesta_creacion.get("ok"):
                    session["mensaje_peliculas"] = (
                        "Película creada correctamente. "
                        "Aparecerá en cartelera cuando tenga "
                        "una función programada."
                    )

                    return redirect(url_for("admin_views.peliculas"))

                mensaje = (
                    respuesta_creacion.get("error") or {}
                ).get(
                    "message",
                    "No se pudo crear la película."
                )

        else:
            mensaje = "Esta operación todavía no está disponible."

    # 2. Buscar películas en TMDB
    if "tmdb_buscar" in request.args:

        if not titulo_tmdb:
            error_tmdb = "Ingresá un título para buscar."

        else:
            token = session.get("token")

            estado_tmdb, respuesta_tmdb = buscar_peliculas_tmdb(
                token,
                titulo_tmdb
            )

            if estado_tmdb == 200 and respuesta_tmdb.get("ok"):
                resultados_tmdb = respuesta_tmdb.get("data") or []

            else:
                error_tmdb = (
                    respuesta_tmdb.get("error") or {}
                ).get(
                    "message",
                    "No se pudo realizar la búsqueda en TMDB."
                )

    # 3. Obtener las películas desde el backend
    estado, respuesta = obtener_peliculas()

    if estado != 200 or not respuesta.get("ok"):
        return render_template(
            "admin/gestion-peliculas.html",
            peliculas=[],
            pelicula_editar=None,
            filtros={"buscar": buscar},
            tmdb_abierto=tmdb_abierto,
            tmdb_titulo=titulo_tmdb,
            resultados_tmdb=resultados_tmdb,
            error_tmdb=error_tmdb,
            mensaje=mensaje or "No se pudieron cargar las películas.",
            csrf_token=csrf_actual
        ), 502

    # 4. Adaptar los datos al HTML
    peliculas_preparadas = []

    for pelicula in respuesta.get("data") or []:
        datos = pelicula.copy()

        datos["duracion_minutos"] = pelicula.get("duracion")
        datos["afiche_url"] = pelicula.get("poster")

        datos["anio"] = "—"
        datos["disponible_desde"] = "—"
        datos["disponible_hasta"] = "—"
        datos["activa"] = True

        peliculas_preparadas.append(datos)

    # 5. Filtrar películas por título
    if buscar:
        peliculas_preparadas = [
            pelicula
            for pelicula in peliculas_preparadas
            if buscar.casefold() in pelicula["titulo"].casefold()
        ]

    # 6. Renderizar la página
    return render_template(
        "admin/gestion-peliculas.html",
        peliculas=peliculas_preparadas,
        pelicula_editar=None,
        filtros={"buscar": buscar},
        tmdb_abierto=tmdb_abierto,
        tmdb_titulo=titulo_tmdb,
        resultados_tmdb=resultados_tmdb,
        error_tmdb=error_tmdb,
        mensaje=mensaje,
        csrf_token=csrf_actual
    )


@admin_views.route("/salas", methods=["GET", "POST"])
def salas():
    if request.method == "POST":
        sala_id = request.form.get("sala_id")
        filas = int(request.form.get("filas", 0))
        butacas_por_fila = int(request.form.get("butacas_por_fila", 0))

        datos = {
            "nombre": request.form.get("nombre"),
            "capacidad": filas * butacas_por_fila,
            "local": request.form.get("complejo_id"),
        }

        consumir_api(
            "PATCH",
            f"/salas/{sala_id}",
            datos=datos,
        )

    status_code, respuesta = consumir_api(
        "GET",
        "/salas",
    )
    status_locales, respuesta_locales = consumir_api(
        "GET",
        "/locales",
    )

    salas = []
    if status_code == 200:
        salas = respuesta.get("data", [])

    sala_actual = None
    editar_sala = request.args.get("editar_sala")
    if editar_sala:
        for sala in salas:
            if str(sala["id"]) == editar_sala:
                sala_actual = sala
                break

    return render_template(
        "admin/gestion-funciones.html",
        salas=salas,
        funciones=[],
        peliculas=[],
        complejos=[
            {"id": local, "nombre": local}
            for local in (
                respuesta_locales.get("data", [])
                if status_locales == 200
                else []
            )
        ],
        sala_editar=sala_actual,
    )

@admin_views.route("/funciones", methods=["GET", "POST"])
def funciones():
    if request.method == "POST":
        accion = request.form.get("accion")
        funcion_id = request.form.get("funcion_id")

        if accion == "guardar_funcion":
            datos = {
                "id_pelicula": int(request.form["pelicula_id"]),
                "id_sala": int(request.form["sala_id"]),
                "fecha_hora_proyeccion": request.form["fecha_hora"].replace("T", " ") + ":00",
            }

            if funcion_id:
                status_code, respuesta = consumir_api(
                    "PATCH",
                    f"/funciones/{funcion_id}",
                    datos=datos,
                )
            else:
                status_code, respuesta = consumir_api(
                    "POST",
                    "/funciones",
                    datos=datos,
                )

        elif accion == "cambiar_estado":
            status_code, respuesta = consumir_api(
                "DELETE",
                f"/funciones/{funcion_id}",
            )

    status_funciones, respuesta_funciones = consumir_api(
        "GET",
        "/funciones",
    )

    status_salas, respuesta_salas = consumir_api(
        "GET",
        "/salas",
    )

    status_locales, respuesta_locales = consumir_api(
        "GET",
        "/locales",
    )

    status_peliculas, respuesta_peliculas = consumir_api(
        "GET",
        "/peliculas/cartelera",
    )

    return render_template(
        "admin/gestion-funciones.html",
        funciones=(
            respuesta_funciones.get("data", [])
            if status_funciones == 200
            else []
        ),
        salas=(
            respuesta_salas.get("data", [])
            if status_salas == 200
            else []
        ),
        complejos=[
            {"id": local, "nombre": local}
            for local in (
                respuesta_locales.get("data", [])
                if status_locales == 200
                else []
            )
        ],
        peliculas=(
            respuesta_peliculas.get("data", [])
            if status_peliculas == 200
            else []
        ),
    )


@admin_views.route("/servicios", methods=["GET", "POST"])
def servicios():
    mensaje = None

    csrf_actual = session.get("csrf_servicios")

    if not csrf_actual:
        csrf_actual = secrets.token_urlsafe(32)
        session["csrf_servicios"] = csrf_actual

    if request.method == "POST":

        csrf_recibido = request.form.get("csrf_token", "")

        if not secrets.compare_digest(csrf_recibido, csrf_actual):
            mensaje = "Formulario inválido. Recargá la página."

        else:
            accion = request.form.get("accion")
            servicio_id = request.form.get("servicio_id", "").strip()
            token = session.get("token")

            if accion == "guardar":

                nombre = request.form.get("nombre", "").strip()
                descripcion = request.form.get("descripcion", "").strip()

                try:
                    precio = float(request.form.get("precio", ""))
                except (ValueError, TypeError):
                    precio = 0

                imagen = request.files.get("imagen")

                if servicio_id and not servicio_id.isdigit():
                    mensaje = "El ID del servicio no es válido."

                elif not nombre or not descripcion or precio <= 0:
                    mensaje = "Completá correctamente todos los campos."

                elif precio >= 100000000:
                    mensaje = "El precio ingresado es demasiado grande."

                elif request.form.get("activo") == "0":
                    mensaje = "Para desactivar un servicio, usá el botón Dar de baja."

                elif imagen and imagen.filename:
                    mensaje = "La API todavía no admite imágenes de servicios."

                elif not token:
                    mensaje = "Debés iniciar sesión como administrador."

                else:
                    if servicio_id:
                        estado, respuesta = actualizar_servicio(
                            token,
                            servicio_id,
                            nombre,
                            descripcion,
                            precio
                        )
                    else:
                        estado, respuesta = crear_servicio(
                            token,
                            nombre,
                            descripcion,
                            precio
                        )

                    if estado in (200, 201) and respuesta.get("ok"):
                        return redirect(url_for("admin_views.servicios"))

                    mensaje = respuesta.get("error", {}).get(
                        "message",
                        "No se pudo guardar el servicio."
                    )

            elif accion in ("cambiar_estado", "eliminar"):

                if not servicio_id.isdigit():
                    mensaje = "El ID del servicio no es válido."

                elif not token:
                    mensaje = "Debés iniciar sesión como administrador."

                else:
                    estado, respuesta = desactivar_servicio(
                        token,
                        servicio_id
                    )

                    if estado == 200 and respuesta.get("ok"):
                        return redirect(url_for("admin_views.servicios"))

                    mensaje = respuesta.get("error", {}).get(
                        "message",
                        "No se pudo desactivar el servicio."
                    )

            else:
                mensaje = "Acción no reconocida."

    estado, respuesta = obtener_servicios()

    if estado != 200 or not respuesta.get("ok"):
        return render_template(
            "admin/gestion-servicios.html",
            servicios=[],
            servicio_editar=None,
            mensaje=mensaje or "No se pudieron cargar los servicios.",
            csrf_token=csrf_actual
        ), 502

    lista_servicios = respuesta.get("data") or []

    for servicio in lista_servicios:
        precio = float(servicio["precio"])

        servicio["precio_formateado"] = f"$ {precio:.2f}"

        servicio["activo"] = True

    servicio_editar = None
    id_editar = request.args.get("editar", type=int)

    if id_editar is not None:
        servicio_editar = next(
            (
                servicio
                for servicio in lista_servicios
                if servicio.get("id") == id_editar
            ),
            None
        )

    return render_template(
        "admin/gestion-servicios.html",
        servicios=lista_servicios,
        servicio_editar=servicio_editar,
        mensaje=mensaje,
        csrf_token=csrf_actual
    )


@admin_views.route("/validar-qr")
def validar_qr():
    return render_template("admin/validar-qr.html")