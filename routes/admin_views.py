import secrets
import re
import math
from datetime import datetime

from flask import abort, Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from routes.auth_security import (
    csrf_token as obtener_csrf_token,
    validar_csrf,
    verificar_sesion
)

from services.api_client import consumir_api
from services.estadisticas_service import obtener_estadisticas_dashboard
from services.admin_service import (
    dar_de_baja_administrador,
    habilitar_administrador,
    obtener_administradores,
)
from services.gestion_peliculas_service import (
    buscar_peliculas_tmdb,
    cambiar_estado_pelicula,
    crear_pelicula,
    eliminar_pelicula,
    obtener_peliculas
)
from services.gestion_servicios_service import (
    actualizar_servicio,
    crear_servicio,
    desactivar_servicio,
    cambiar_estado_servicio,
    obtener_servicios
)

admin_views = Blueprint("admin_views", __name__, url_prefix="/admin")


def _admin_anchor_redirect(endpoint, anchor):
    if anchor and re.fullmatch(r"[A-Za-z0-9_-]+", anchor):
        return redirect(f"{url_for(endpoint)}#{anchor}")
    return redirect(url_for(endpoint))

@admin_views.before_request
def proteger_admin():
    if request.method == "POST":
        validar_csrf()
    return verificar_sesion("administrador")

@admin_views.route("/estadisticas")
def estadisticas():
    token = session.get("access_token")
    complejo_filtro = request.args.get("complejo", "").strip()
    estado_locales, respuesta_locales = consumir_api("GET", "/funciones/locales")

    status_code, datos_estadisticas = obtener_estadisticas_dashboard(
        token, complejo_filtro or None
    )

    error_api = False
    if status_code != 200 or not datos_estadisticas:
        error_api = True
        flash("No se pudieron cargar las estadísticas. El servicio de reportes no está disponible.", "error")
        datos_estadisticas = {
            "resumen": {}, "ocupacion_funciones": [], "ocupacion_peliculas": [],
            "ventas_genero": [], "ventas_franjas": [], "cancelaciones": []
        }

    return render_template(
        "admin/estadisticas.html",
        resumen=datos_estadisticas.get("resumen"),
        ocupacion_funciones=datos_estadisticas.get("ocupacion_funciones"),
        ocupacion_peliculas=datos_estadisticas.get("ocupacion_peliculas"),
        ventas_genero=datos_estadisticas.get("ventas_genero"),
        ventas_franjas=datos_estadisticas.get("ventas_franjas"),
        cancelaciones=datos_estadisticas.get("cancelaciones"),
        complejos=[
            {"id": local, "nombre": local}
            for local in (
                respuesta_locales.get("data", [])
                if estado_locales == 200 else []
            )
        ],
        periodos=[],
        filtros={"complejo": complejo_filtro, "periodo": request.args.get("periodo", "")},
        error_api=error_api
    )


@admin_views.route("/habilitar-admins", methods=["GET", "POST"])
def habilitar_admins():
    usuario = session.get("usuario", {})
    if usuario.get("email", "").casefold() != current_app.config["SUPER_ADMIN_EMAIL"]:
        abort(403)

    mensaje = None
    error = None
    email = ""
    administrador_creado = None
    if request.method == "POST":
        accion = request.form.get("accion")
        if accion == "dar_de_baja":
            id_admin = request.form.get("id_admin", "")
            if not id_admin.isdigit():
                error = "El administrador seleccionado no es válido."
            else:
                estado, respuesta = dar_de_baja_administrador(id_admin)
                if estado == 200 and respuesta.get("ok"):
                    mensaje = "La cuenta dejó de tener permisos de administración."
                else:
                    error = (respuesta.get("error") or {}).get(
                        "message", "No se pudo dar de baja al administrador."
                    )
        else:
            email = request.form.get("email", "").strip().lower()
            if not email or len(email) > 100 or "@" not in email:
                error = "Ingresá un correo electrónico válido."
            else:
                estado, respuesta = habilitar_administrador(email)
                if estado == 200 and respuesta.get("ok"):
                    mensaje = "La cuenta fue habilitada como administradora."
                    administrador_creado = respuesta.get("data")
                    email = ""
                else:
                    error = (
                        respuesta.get("error") or {}
                    ).get("message", "No se pudo habilitar la cuenta.")

    estado_admins, respuesta_admins = obtener_administradores()
    administradores = respuesta_admins.get("data", []) if estado_admins == 200 else []
    if administrador_creado and not any(
        str(item.get("id")) == str(administrador_creado.get("id"))
        for item in administradores
    ):
        administradores.append(administrador_creado)
    if estado_admins != 200:
        api_error = respuesta_admins.get("error") or {}
        error = error or api_error.get("message", "No se pudo cargar la lista de administradores.")

    return render_template(
        "admin/habilitar-admins.html",
        email=email,
        mensaje=mensaje,
        error=error,
        csrf_token=obtener_csrf_token(),
        administradores=administradores,
    )


@admin_views.route("/peliculas", methods=["GET", "POST"])
def peliculas():
    mensaje = session.pop("mensaje_peliculas", None)

    buscar = request.args.get("buscar", "").strip()
    titulo_tmdb = request.args.get("tmdb_buscar", "").strip()
    id_editar = request.args.get("editar", type=int)

    tmdb_abierto = (
            request.args.get("tmdb") == "1"
            or "tmdb_buscar" in request.args
    )

    resultados_tmdb = []
    error_tmdb = None
    pelicula_editar = None
    csrf_actual = obtener_csrf_token()

    if request.method == "POST":
        accion = request.form.get("accion")
        csrf_recibido = request.form.get("csrf_token", "")

        if not secrets.compare_digest(csrf_recibido, csrf_actual):
            mensaje = "Formulario inválido. Recargá la página."

        elif accion == "crear_tmdb":
            tmdb_abierto = True

            token = session.get("access_token")

            titulo = request.form.get("titulo", "").strip()
            sinopsis = request.form.get("sinopsis", "").strip()
            poster = request.form.get("poster", "").strip()
            genero = request.form.get("genero", "").strip()
            clasificacion = request.form.get("clasificacion", "")

            try:
                duracion = int(request.form.get("duracion", ""))
            except (ValueError, TypeError):
                duracion = 0

            if not titulo or len(titulo) > 150:
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

        elif accion in ("cambiar_estado", "eliminar"):
            pelicula_id = request.form.get("pelicula_id")
            token = session.get("access_token")
            estado = None
            if not pelicula_id or not pelicula_id.isdigit():
                mensaje = "La película seleccionada no es válida."
            elif accion == "cambiar_estado":
                activo = request.form.get("activo") == "1"
                estado, respuesta = cambiar_estado_pelicula(token, pelicula_id, activo)
                mensaje = ((respuesta.get("error") or {}).get("message")
                           if estado != 200 else "Estado de la película actualizado.")
            else:
                estado, respuesta = eliminar_pelicula(token, pelicula_id)
                mensaje = ((respuesta.get("error") or {}).get("message")
                           if estado != 200 else "La película fue retirada del catálogo.")
            if request.form.get("volver_a") and estado == 200:
                session["mensaje_peliculas"] = mensaje
                return _admin_anchor_redirect("admin_views.peliculas", request.form.get("volver_a"))

        else:
            mensaje = "Acción no reconocida."

    if "tmdb_buscar" in request.args:
        if not titulo_tmdb:
            error_tmdb = "Ingresá un título para buscar."
        else:
            token = session.get("access_token")
            estado_tmdb, respuesta_tmdb = buscar_peliculas_tmdb(token, titulo_tmdb)

            if estado_tmdb == 200 and respuesta_tmdb.get("ok"):
                resultados_tmdb = respuesta_tmdb.get("data") or []
            else:
                error_tmdb = (
                        respuesta_tmdb.get("error") or {}
                ).get(
                    "message",
                    "No se pudo realizar la búsqueda en TMDB."
                )

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

    peliculas_preparadas = []
    for pelicula in respuesta.get("data") or []:
        datos = pelicula.copy()
        datos["duracion_minutos"] = pelicula.get("duracion")
        datos["afiche_url"] = pelicula.get("poster")
        datos["anio"] = "—"
        datos["disponible_desde"] = "—"
        datos["disponible_hasta"] = "—"
        datos["activa"] = bool(pelicula.get("activo", True))
        peliculas_preparadas.append(datos)

    if id_editar is not None:
        pelicula_editar = next(
            (
                pelicula.copy()
                for pelicula in peliculas_preparadas
                if pelicula.get("id") == id_editar
            ),
            None
        )
        if pelicula_editar is None:
            mensaje = "No se encontró la película seleccionada."

    if buscar:
        peliculas_preparadas = [
            pelicula
            for pelicula in peliculas_preparadas
            if buscar.casefold() in pelicula["titulo"].casefold()
        ]

    return render_template(
        "admin/gestion-peliculas.html",
        peliculas=peliculas_preparadas,
        pelicula_editar=pelicula_editar,
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

        status_sala, respuesta_sala = consumir_api(
            "PATCH",
            f"/funciones/salas/{sala_id}",
            datos=datos,
        )
        if status_sala == 200 and respuesta_sala.get("ok"):
            return redirect(url_for("admin_views.funciones", editar_sala=sala_id))
        return redirect(url_for("admin_views.funciones", editar_sala=sala_id,
                                sala_error=(respuesta_sala.get("error") or {}).get(
                                    "message", "No se pudo guardar la configuración de la sala."
                                )))

    return redirect(url_for(
        "admin_views.funciones",
        editar_sala=request.args.get("editar_sala", ""),
    ))


@admin_views.route("/funciones", methods=["GET", "POST"])
def funciones():
    mensaje = request.args.get("sala_error")
    mensaje_guardado = session.pop("mensaje_funciones", None)
    if isinstance(mensaje_guardado, dict):
        mensaje_estado = mensaje_guardado.get("texto")
        mensaje_tipo = mensaje_guardado.get("tipo", "error")
    else:
        mensaje_estado = mensaje_guardado
        mensaje_tipo = "error" if mensaje_estado else None
    if mensaje:
        mensaje_tipo = "error"
    if request.method == "POST":
        accion = request.form.get("accion")
        funcion_id = request.form.get("funcion_id")

        if accion == "guardar_funcion":
            complejo_id = request.form.get("complejo_id", "").strip()
            sala_id = request.form.get("sala_id", "").strip()
            if not sala_id:
                mensaje = "Seleccioná una sala para la función."
                mensaje_tipo = "error"
                sala_id = None
            elif complejo_id:
                salas_disponibles = consumir_api(
                    "GET", "/funciones/salas", params={"local": complejo_id}
                )
                salas_del_complejo = (
                    salas_disponibles[1].get("data", [])
                    if salas_disponibles[0] == 200 else []
                )
                if not any(str(sala.get("id")) == sala_id for sala in salas_del_complejo):
                    mensaje = "La sala seleccionada no pertenece al complejo elegido."
                    mensaje_tipo = "error"
                    sala_id = None

            if sala_id is None:
                status_code, respuesta = 400, {"ok": False}
            else:
                datos = {
                    "id_pelicula": int(request.form["pelicula_id"]),
                    "id_sala": int(sala_id),
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

            if sala_id is not None and status_code in (200, 201) and respuesta.get("ok"):
                mensaje_estado = "La función se guardó correctamente."
                mensaje_tipo = "success"
            elif sala_id is not None:
                mensaje = (respuesta.get("error") or {}).get(
                    "message", "No se pudo guardar la función."
                )
                mensaje_tipo = "error"

        elif accion in ("cambiar_estado", "eliminar"):
            if accion == "eliminar":
                status_code, respuesta = consumir_api(
                    "DELETE", f"/funciones/{funcion_id}"
                )
                if status_code == 200 and respuesta.get("ok"):
                    mensaje_estado = "La función fue eliminada correctamente."
                    mensaje_tipo = "success"
                else:
                    mensaje = (respuesta.get("error") or {}).get(
                        "message", "No se pudo eliminar la función."
                    )
                    mensaje_tipo = "error"
            else:
                activo = request.form.get("activo") == "1"
                status_code, respuesta = consumir_api(
                    "PATCH",
                    f"/funciones/{funcion_id}/estado",
                    datos={"activo": activo},
                )
                if status_code == 200 and respuesta.get("ok"):
                    mensaje_estado = (
                        "La función fue activada correctamente."
                        if activo else "La función fue dada de baja correctamente."
                    )
                    mensaje_tipo = "success"
                else:
                    mensaje = (respuesta.get("error") or {}).get(
                        "message", "No se pudo cambiar el estado de la función."
                    )
                    mensaje_tipo = "error"
            if request.form.get("volver_a"):
                session["mensaje_funciones"] = {
                    "texto": mensaje_estado or mensaje,
                    "tipo": mensaje_tipo or "error",
                }
                return _admin_anchor_redirect("admin_views.funciones", request.form.get("volver_a"))

    status_funciones, respuesta_funciones = consumir_api(
        "GET", "/funciones?incluir_inactivas=1"
    )
    status_salas, respuesta_salas = consumir_api("GET", "/funciones/salas")
    status_locales, respuesta_locales = consumir_api("GET", "/funciones/locales")
    status_peliculas, respuesta_peliculas = consumir_api("GET", "/peliculas/admin")

    funciones = respuesta_funciones.get("data", []) if status_funciones == 200 else []
    complejo_filtro = request.args.get("complejo", "").strip()
    estado_filtro = request.args.get("estado", "todos").strip().lower()
    if complejo_filtro and complejo_filtro != "Todos":
        funciones = [
            funcion for funcion in funciones
            if str(funcion.get("sala", {}).get("local", "")).casefold()
            == complejo_filtro.casefold()
        ]
    for funcion in funciones:
        fecha = funcion.get("fecha_hora_proyeccion", "")
        try:
            fecha_obj = datetime.fromisoformat(str(fecha).replace("Z", "+00:00"))
        except ValueError:
            fecha_obj = None
        funcion["fecha_hora"] = fecha_obj or datetime.min
        funcion["venta_desde"] = funcion["fecha_hora"]
        funcion["venta_hasta"] = funcion["fecha_hora"]
        funcion["pelicula_titulo"] = funcion.get("pelicula", {}).get("titulo", "")
        funcion["complejo_nombre"] = funcion.get("sala", {}).get("local", "")
        funcion["sala_nombre"] = funcion.get("sala", {}).get("nombre", "")
        funcion["precio_formateado"] = f"$ {funcion.get('precio_entrada', 0)}"
        funcion["pelicula_activa"] = bool(funcion.get("pelicula_activa", funcion.get("pelicula", {}).get("activa", True)))
        funcion["pelicula_eliminada"] = bool(funcion.get("pelicula_eliminada", funcion.get("pelicula", {}).get("eliminada", False)))
        funcion["activa"] = bool(funcion.get("activo", True)) and funcion["pelicula_activa"] and not funcion["pelicula_eliminada"]

    if estado_filtro == "activas":
        funciones = [funcion for funcion in funciones if funcion["activa"]]
    elif estado_filtro == "inactivas":
        funciones = [funcion for funcion in funciones if not funcion["activa"]]
    funciones.sort(key=lambda funcion: (not funcion["activa"], funcion["fecha_hora"]))

    salas = (
        respuesta_salas.get("data", [])
        if status_salas == 200
        else []
    )
    for sala in salas:
        capacidad = int(sala.get("capacidad") or 0)
        filas = int(sala.get("filas") or max(1, round(math.sqrt(capacidad or 1))))
        sala["filas"] = filas
        sala["butacas_por_fila"] = int(
            sala.get("butacas_por_fila") or math.ceil(capacidad / filas)
        )
        sala["complejo_nombre"] = sala.get("local", "")

    editar_sala = request.args.get("editar_sala")
    complejo_form = request.args.get("complejo_form", "").strip()
    salas_formulario = salas
    funcion_editar = None
    id_editar_funcion = request.args.get("editar", type=int)
    if id_editar_funcion is not None:
        funcion_editar = next(
            (
                funcion.copy()
                for funcion in funciones
                if funcion.get("id") == id_editar_funcion
            ),
            None,
        )
        if funcion_editar is None:
            mensaje_estado = "No se encontró la función seleccionada."
            mensaje_tipo = "error"
        else:
            fecha_funcion = funcion_editar.get("fecha_hora_proyeccion", "")
            try:
                fecha_obj = datetime.fromisoformat(
                    str(fecha_funcion).replace("Z", "+00:00")
                )
                funcion_editar["fecha_hora_form"] = fecha_obj.strftime(
                    "%Y-%m-%dT%H:%M"
                )
            except ValueError:
                funcion_editar["fecha_hora_form"] = ""
            funcion_editar["venta_desde_form"] = funcion_editar["fecha_hora_form"]
            funcion_editar["venta_hasta_form"] = funcion_editar["fecha_hora_form"]
            funcion_editar["precio"] = funcion_editar.get("precio_entrada", 0)
            funcion_editar["pelicula_id"] = funcion_editar.get(
                "pelicula", {}
            ).get("id")
            complejo_form = str(funcion_editar.get("sala", {}).get("local", ""))

    sala_actual = next(
        (sala for sala in salas if str(sala.get("id")) == editar_sala),
        None,
    ) if editar_sala else None

    return render_template(
        "admin/gestion-funciones.html",
        funciones=funciones,
        funcion_editar=funcion_editar,
        filtros={"complejo": complejo_filtro},
        estado_filtro=estado_filtro,
        salas=salas,
        salas_formulario=salas_formulario,
        complejo_form=complejo_form,
        complejos=[
            {"id": local, "nombre": local}
            for local in (
                respuesta_locales.get("data", [])
                if status_locales == 200
                else []
            )
        ],
        peliculas=[
            pelicula for pelicula in (
                respuesta_peliculas.get("data", [])
                if status_peliculas == 200 else []
            )
            if pelicula.get("activo", True) and not pelicula.get("eliminada", False)
        ],
        sala_editar=sala_actual,
        csrf_token=obtener_csrf_token(),
        mensaje=mensaje,
        mensaje_estado=mensaje_estado,
        mensaje_tipo=mensaje_tipo,
    )


@admin_views.route("/servicios", methods=["GET", "POST"])
def servicios():
    mensaje = session.pop("mensaje_servicios", None)
    csrf_actual = obtener_csrf_token()

    if request.method == "POST":
        csrf_recibido = request.form.get("csrf_token", "")

        if not secrets.compare_digest(csrf_recibido, csrf_actual):
            mensaje = "Formulario inválido. Recargá la página."
        else:
            accion = request.form.get("accion")
            servicio_id = request.form.get("servicio_id", "").strip()
            token = session.get("access_token")

            if accion == "guardar":
                nombre = request.form.get("nombre", "").strip()
                descripcion = request.form.get("descripcion", "").strip()
                categoria = request.form.get("categoria", "")

                try:
                    precio = float(request.form.get("precio", ""))
                except (ValueError, TypeError):
                    precio = 0

                imagen = request.files.get("imagen")

                if servicio_id and not servicio_id.isdigit():
                    mensaje = "El ID del servicio no es válido."
                elif categoria not in ("Bebidas", "Pochoclos", "Snacks", "Mejoras de experiencia"):
                    mensaje = "Seleccioná una categoría válida."
                elif not nombre or not descripcion or precio <= 0:
                    mensaje = "Completá correctamente todos los campos."
                elif precio >= 100000000:
                    mensaje = "El precio ingresado es demasiado grande."
                elif request.form.get("activo") == "0":
                    mensaje = "Para desactivar un servicio, usá el botón Dar de baja."
                elif imagen and imagen.filename:
                    mensaje = "La API todavía no admite imágenes de servicios."
                else:
                    if servicio_id:
                        estado, respuesta = actualizar_servicio(
                            token, servicio_id, nombre, descripcion, precio, categoria
                        )
                    else:
                        estado, respuesta = crear_servicio(
                            token, nombre, descripcion, precio, categoria
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
                else:
                    if accion == "cambiar_estado":
                        activo = request.form.get("activo") == "1"
                        estado, respuesta = cambiar_estado_servicio(token, servicio_id, activo)
                    else:
                        estado, respuesta = desactivar_servicio(token, servicio_id)

                    if estado == 200 and respuesta.get("ok"):
                        mensaje = (
                            "El servicio fue activado correctamente."
                            if accion == "cambiar_estado" and request.form.get("activo") == "1"
                            else "El servicio fue dado de baja correctamente."
                            if accion == "cambiar_estado"
                            else "El servicio fue retirado del catálogo."
                        )
                    else:
                        mensaje = respuesta.get("error", {}).get(
                            "message",
                            "No se pudo completar la operación."
                        )
                    if accion in ("cambiar_estado", "eliminar") and request.form.get("volver_a"):
                        session["mensaje_servicios"] = mensaje
                        return _admin_anchor_redirect("admin_views.servicios", request.form.get("volver_a"))
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
        servicio["activo"] = servicio.get("activo", True)

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


@admin_views.route("/validar-qr", methods=["GET", "POST"])
def validar_qr():
    resultado = None
    error = None

    if request.method == "POST":
        accion = request.form.get("accion")

        # Validar el código QR de una entrada
        if accion == "validar_qr":
            codigo_qr = request.form.get("codigo_qr", "").strip()

            if not codigo_qr:
                error = "Por favor, ingresá un identificador de QR válido."
            else:
                status_code, respuesta = consumir_api("POST", "/compras/validar-qr", datos={"codigo_qr": codigo_qr})

                if status_code == 200:
                    data = respuesta.get("data", {})
                    servicios = data.get("servicios_adicionales") or []
                    resultado = {
                        "titulo": "Resultado · Compra válida",
                        "aprobada": True,
                        "mensaje_estado": "Acceso registrado",
                        "detalle": "La función y la fecha fueron verificadas. Todas las butacas de la compra quedaron marcadas como utilizadas.",
                        "id_entrada": data.get("id_entrada"),
                        "codigo_qr": codigo_qr,
                        "estado": "Ingreso registrado · Entrada utilizada",
                        "butacas_texto": "Butacas: " + ", ".join(
                            str(numero) for numero in data.get("butacas", [])
                        ),
                        "funcion": {
                            "pelicula_titulo": data.get("pelicula", "Película no especificada"),
                            "fecha_hora": data.get("fecha_hora", ""),
                            "complejo_nombre": data.get("complejo", ""),
                            "sala_nombre": data.get("sala", ""),
                            "activa": True,
                        },
                        "servicios": [
                            {
                                "id": servicio.get("id_detalle"),
                                "id_detalle": servicio.get("id_detalle"),
                                "nombre": servicio.get("nombre", "Servicio"),
                                "detalle": f"Cantidad: {servicio.get('cantidad', 1)}",
                                "consumido": bool(servicio.get("usado")),
                                "tipo": "servicio",
                            }
                            for servicio in servicios
                        ],
                    }
                else:
                    resultado = {
                        "titulo": "Resultado · Acceso rechazado",
                        "aprobada": False,
                        "mensaje_estado": "Rechazada · Sin ingreso",
                        "estado": "Código no válido o ya utilizado",
                        "detalle": (respuesta.get("error") or {}).get(
                            "message", "El código QR presentado no es válido o ya fue utilizado."
                        ),
                        "servicios": [],
                    }

        # Validar la entrega de un servicio adicional
        elif accion == "validar_servicio":
            id_detalle = request.form.get("id_detalle")
            status_code, respuesta = consumir_api(
                "POST", "/compras/validar-servicio", datos={"id_detalle": id_detalle}
            )

            if status_code == 200:
                resultado = {
                    "titulo": "Resultado · Servicio validado",
                    "aprobada": True,
                    "mensaje_estado": "Acceso registrado",
                    "estado": "Servicio utilizado",
                    "detalle": "El servicio quedó marcado como utilizado y no puede volver a validarse.",
                    "servicios": [],
                }
            else:
                resultado = {
                    "titulo": "Resultado · Servicio rechazado",
                    "aprobada": False,
                    "mensaje_estado": "Rechazado · Sin entrega",
                    "estado": "Servicio no validado",
                    "detalle": (respuesta.get("error") or {}).get(
                        "message", "No se pudo validar la entrega del servicio."
                    ),
                    "servicios": [],
                }

    return render_template(
        "admin/validar-qr.html",
        resultado=resultado,
        validacion=resultado,
        error=error,
        csrf_token=obtener_csrf_token(),
        historial_entradas=[],
        historial_servicios=[],
    )