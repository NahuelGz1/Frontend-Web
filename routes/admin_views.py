import secrets
import re
import base64
from datetime import datetime
from urllib.parse import quote

from flask import abort, Blueprint, current_app, flash, make_response, redirect, render_template, request, session, url_for

from routes.auth_security import (
    csrf_token as obtener_csrf_token,
    validar_csrf,
    verificar_sesion
)

from services.api_client import consumir_api, descargar_api
from services.estadisticas_service import obtener_estadisticas_dashboard
from utils.butacas import etiqueta_butaca, etiquetas_butacas
from services.admin_service import (
    dar_de_baja_administrador,
    habilitar_administrador,
    obtener_administradores,
    dar_de_baja_empleado,
    habilitar_empleado,
    obtener_empleados
)
from services.gestion_peliculas_service import (
    actualizar_pelicula,
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


def _imagen_servicio_desde_formulario(archivo):
    if not archivo or not archivo.filename:
        return None, None
    contenido = archivo.read(5 * 1024 * 1024 + 1)
    if len(contenido) > 5 * 1024 * 1024:
        return None, "La imagen no puede superar los 5 MB."
    tipos_permitidos = {"image/png": "png", "image/jpeg": "jpeg"}
    tipo = archivo.mimetype or ""
    if tipo not in tipos_permitidos:
        return None, "La imagen debe estar en formato JPG o PNG."
    contenido_codificado = base64.b64encode(contenido).decode("ascii")
    return f"data:{tipo};base64,{contenido_codificado}", None

@admin_views.before_request
def proteger_admin():
    if request.method == "POST":
        validar_csrf()
    if request.endpoint == "admin_views.validar_qr":
        return verificar_sesion(("administrador", "empleado"))
    return verificar_sesion("administrador")

@admin_views.route("/estadisticas")
def estadisticas():
    token = session.get("access_token")
    complejo_filtro = request.args.get("complejo", "").strip()
    periodo_filtro = request.args.get("periodo", "").strip()
    estado_locales, respuesta_locales = consumir_api("GET", "/funciones/locales")

    status_code, datos_estadisticas = obtener_estadisticas_dashboard(
        token, complejo_filtro or None, periodo_filtro or None
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
        periodos=datos_estadisticas.get("periodos", []),
        filtros={"complejo": complejo_filtro, "periodo": periodo_filtro},
        error_api=error_api
    )


@admin_views.route("/estadisticas/exportar-pdf")
def exportar_estadisticas_pdf():
    params = {}
    complejo = request.args.get ("complejo", "").strip()
    periodo = request.args.get("periodo", "").strip()

    if complejo:
        params["complejo"] = complejo
    if periodo:
        params["periodo"] = periodo


    status, contenido, cabeceras = descargar_api("/dashboard/ocupacion/pdf", params=params)

    
    if status != 200 or not contenido:
        abort(502)

    respuesta = make_response(contenido)
    respuesta.status_code = 200
    respuesta.headers["Content-Type"] = "application/pdf"
    respuesta.headers["Content-Disposition"] = (
        cabeceras.get("Content-Disposition")
        or 'attachment; filename="reporte_de_ventas_cine_paradiso.pdf"'
    )
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


@admin_views.route("/habilitar-admins", methods=["GET", "POST"])
def habilitar_admins():
    usuario = session.get("usuario", {})
    if usuario.get("email", "").casefold() != current_app.config["SUPER_ADMIN_EMAIL"]:
        abort(403)

    mensaje = None
    error = None
    email = ""
    rol_seleccionado = "administrador"
    administrador_creado = None
    empleado_creado = None
    if request.method == "POST":
        accion = request.form.get("accion")
        if accion == "dar_de_baja":
            id_usuario = request.form.get("id_admin", "")
            rol_baja = request.form.get("rol", "administrador")
            if not id_usuario.isdigit():
                error = "El cuenta seleccionado no es válido."
            elif rol_baja == "empleado":
                estado, respuesta = dar_de_baja_empleado(id_usuario)
                if estado == 200 and respuesta.get("ok"):
                    mensaje = "La cuenta dejó de tener permisos de empleado"
                else:
                    error = (respuesta.get("error") or {}).get(
                        "message", "No se pudo dar de baja al empleado.")
            else:
                estado, respuesta = dar_de_baja_administrador(id_usuario)
                if estado == 200 and respuesta.get("ok"):
                    mensaje = "La cuenta dejó de tener permisos de administración."
                else:
                    error = (respuesta.get("error") or {}).get(
                        "message", "No se pudo dar de baja al administrador."
                    )
        else:
            email = request.form.get("email", "").strip().lower()
            rol_seleccionado = request.form.get("rol", "administrador")
            if not email or len(email) > 100 or "@" not in email:
                error = "Ingresá un correo electrónico válido."
            elif rol_seleccionado not in ("administrador", "empleado"):
                error = "Selecciona un rol valido"
            elif rol_seleccionado == "empleado":
                estado, respuesta = habilitar_empleado(email)
                if estado == 200 and respuesta.get("ok"):
                    mensaje = "La cuenta fue habilitada como empleada."
                    empleado_creado = respuesta.get("data")
                    email = ""
                else:
                    error = (respuesta.get("error") or {}).get("message", "No se pudo habilitar la cuenta.")
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
    estado_empls, respuesta_empls = obtener_empleados()
    empleados = respuesta_empls.get("data", []) if estado_empls == 200 else []
    if administrador_creado and not any(
        str(item.get("id")) == str(administrador_creado.get("id"))
        for item in administradores
    ):
        administradores.append(administrador_creado)
    if estado_admins != 200:
        api_error = respuesta_admins.get("error") or {}
        error = error or api_error.get("message", "No se pudo cargar la lista de administradores.")
    if empleado_creado and not any(
        str(item.get("id")) == str(empleado_creado.get("id"))
        for item in empleados
    ):
        empleados.append(empleado_creado)
    if estado_empls != 200:
        api_error = respuesta_empls.get("error") or {}
        error = error or api_error.get("message", "No se pudo cargar la lista de empleados.")

    return render_template(
        "admin/habilitar-admins.html",
        email=email,
        rol=rol_seleccionado,
        mensaje=mensaje,
        error=error,
        csrf_token=obtener_csrf_token(),
        administradores=administradores,
        empleados=empleados,
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
    formulario_pelicula = None
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

        elif accion == "guardar":
            pelicula_id = request.form.get("pelicula_id", "")
            if not pelicula_id.isascii() or not pelicula_id.isdigit() or int(pelicula_id) < 1:
                mensaje = "La película seleccionada no es válida."
            else:
                id_editar = int(pelicula_id)
                duracion_texto = request.form.get("duracion_minutos", "").strip()
                estado_texto = request.form.get("activa", "")
                formulario_pelicula = {
                    "titulo": request.form.get("titulo", "").strip(),
                    "sinopsis": request.form.get("sinopsis", "").strip(),
                    "duracion_minutos": duracion_texto,
                    "clasificacion": request.form.get("clasificacion", ""),
                    "genero": request.form.get("genero", "").strip(),
                    "activa": estado_texto == "1",
                }
                imagen_url, error_imagen = _imagen_servicio_desde_formulario(request.files.get("afiche"))
                if not duracion_texto.isascii() or not duracion_texto.isdigit() or not 1 <= int(duracion_texto) <= 999:
                    mensaje = "La duración debe estar entre 1 y 999 minutos."
                elif estado_texto not in ("0", "1"):
                    mensaje = "Seleccioná un estado válido."
                elif error_imagen:
                    mensaje = error_imagen
                else:
                    datos = {
                        "titulo": formulario_pelicula["titulo"],
                        "sinopsis": formulario_pelicula["sinopsis"],
                        "duracion": int(duracion_texto),
                        "clasificacion": formulario_pelicula["clasificacion"],
                        "genero": formulario_pelicula["genero"],
                        "activo": estado_texto == "1",
                    }
                    if imagen_url is not None:
                        datos["poster"] = imagen_url
                    estado, respuesta = actualizar_pelicula(session.get("access_token"), pelicula_id, datos)
                    if estado == 200 and respuesta.get("ok"):
                        session["mensaje_peliculas"] = "Película actualizada correctamente."
                        return _admin_anchor_redirect("admin_views.peliculas", f"pelicula-{pelicula_id}")
                    error = respuesta.get("error") or {}
                    detalles = error.get("details")
                    mensaje = error.get("message") or "No se pudo actualizar la película."
                    if isinstance(detalles, dict) and detalles:
                        mensaje += " " + " ".join(f"{campo}: {detalle}." for campo, detalle in detalles.items())
                if request.files.get("afiche") and request.files["afiche"].filename:
                    mensaje += " Volvé a seleccionar el afiche antes de guardar."

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
        elif formulario_pelicula is not None:
            pelicula_editar.update(formulario_pelicula)

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
        capacidad = request.form.get("capacidad", "").strip()
        if not capacidad.isdigit() or int(capacidad) <= 0:
            session["mensaje_sala"] = {
                "texto": "La capacidad debe ser un número entero mayor a cero.",
                "tipo": "error",
            }
            return redirect(url_for("admin_views.funciones", editar_sala=sala_id))

        datos = {
            "nombre": request.form.get("nombre"),
            "capacidad": int(capacidad),
            "local": request.form.get("complejo_id"),
        }

        status_sala, respuesta_sala = consumir_api(
            "PATCH",
            f"/funciones/salas/{sala_id}",
            datos=datos,
        )
        if status_sala == 200 and respuesta_sala.get("ok"):
            session["mensaje_sala"] = {"texto": "La configuración de la sala se guardó correctamente.", "tipo": "success"}
            return redirect(url_for("admin_views.funciones", editar_sala=sala_id))
        session["mensaje_sala"] = {
            "texto": (respuesta_sala.get("error") or {}).get(
                "message", "No se pudo guardar la configuración de la sala."
            ),
            "tipo": "error",
        }
        return redirect(url_for("admin_views.funciones", editar_sala=sala_id))

    return redirect(url_for(
        "admin_views.funciones",
        editar_sala=request.args.get("editar_sala", ""),
    ))


ESTADOS_FUNCION = {
    "en_venta": ("En venta", "badge-success"),
    "agotada": ("Agotada", "badge-danger"),
    "venta_cerrada": ("Venta cerrada", "badge-danger"),
    "finalizada": ("Finalizada", ""),
    "cancelada": ("Cancelada", "badge-danger"),
}


def _plural(cantidad, singular, plural):
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _mensaje_cancelacion(datos):
    compras = int(datos.get("compras_afectadas") or 0)
    if not compras:
        return "Se canceló la función. No tenía entradas vendidas, así que no hubo devoluciones."
    total = f"${int(datos.get('total_devuelto') or 0):,}".replace(",", ".")
    mensaje = (
        f"Se canceló la función: se devolvieron {_plural(int(datos.get('entradas_canceladas') or 0), 'entrada', 'entradas')} "
        f"de {_plural(compras, 'compra', 'compras')} ({total}) y sus QR ya no son válidos."
    )
    sin_mail = compras - int(datos.get("correos_enviados") or 0)
    if sin_mail:
        mensaje += f" No se pudo enviar el mail a {_plural(sin_mail, 'comprador', 'compradores')}, revisá la configuración del correo."
    return mensaje


def _preparar_estado_funcion(funcion):
    # el back manda el estado calculado, si no viene se arma con la fecha y el activo
    estado = funcion.get("estado")
    if estado not in ESTADOS_FUNCION:
        if funcion.get("cancelada"):
            estado = "cancelada"
        elif funcion["fecha_hora"] <= datetime.now():
            estado = "finalizada"
        else:
            estado = "en_venta" if funcion["activa"] else "venta_cerrada"
    funcion["estado"] = estado
    funcion["estado_texto"], funcion["estado_clase"] = ESTADOS_FUNCION[estado]
    funcion["finalizada"] = estado == "finalizada"
    funcion["cancelada"] = estado == "cancelada"
    cerrada = funcion["finalizada"] or funcion["cancelada"]

    vendidas = int(funcion.get("entradas_vendidas") or 0)
    funcion["entradas_vendidas"] = vendidas
    funcion["puede_editar"] = not cerrada and vendidas == 0
    funcion["puede_eliminar"] = funcion["puede_editar"]
    funcion["puede_cambiar_estado"] = not cerrada
    funcion["puede_activar"] = (
        funcion["pelicula_activa"] and not funcion["pelicula_eliminada"]
        and funcion["sala_activa"]
    )
    # con ventas no se puede eliminar, pero si cancelar devolviendo el dinero
    funcion["puede_cancelar"] = not cerrada and vendidas > 0

    if funcion["cancelada"]:
        funcion["motivo_bloqueo"] = (
            f"Función cancelada ({funcion.get('motivo_cancelacion') or 'sin motivo'}). "
            "La función permanece en el historial."
        )
    elif funcion["finalizada"]:
        funcion["motivo_bloqueo"] = "La función ya se proyectó: queda en el historial y no se puede modificar."
    elif vendidas:
        funcion["motivo_bloqueo"] = (
            "Tiene entradas vendidas: no se puede editar ni eliminar para preservar las compras. "
            "Podés cancelar la función para devolver el dinero."
        )
    else:
        funcion["motivo_bloqueo"] = None


@admin_views.route("/funciones", methods=["GET", "POST"])
def funciones():
    aviso_sala = session.pop("mensaje_sala", None)
    mensaje = None
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

        elif accion == "cambiar_estado_sala":
            sala_id = request.form.get("sala_id")
            activo = request.form.get("activo") == "1"
            status_code, respuesta = consumir_api(
                "PATCH", f"/funciones/salas/{sala_id}", datos={"activo": activo}
            )
            if status_code == 200 and respuesta.get("ok"):
                mensaje_estado = (
                    "La sala quedó habilitada para nuevas funciones."
                    if activo else "La sala quedó en mantenimiento y no acepta nuevas ventas."
                )
                mensaje_tipo = "success"
            else:
                mensaje = (respuesta.get("error") or {}).get(
                    "message", "No se pudo cambiar el estado de la sala."
                )
                mensaje_tipo = "error"
            session["mensaje_sala"] = {
                "texto": mensaje_estado or mensaje,
                "tipo": mensaje_tipo or "error",
            }
            return redirect(url_for("admin_views.funciones"))
        elif accion in ("cambiar_estado", "eliminar", "cancelar", "destacar"):
            if accion == "destacar":
                status_code, respuesta = consumir_api(
                    "PUT", f"/funciones/{funcion_id}/destacar"
                )
                if status_code == 200 and respuesta.get("ok"):
                    mensaje_estado = "La película se seleccionó como destacada de la semana."
                    mensaje_tipo = "success"
                else:
                    mensaje_estado = None
                    mensaje = (respuesta.get("error") or {}).get(
                        "message", "No se pudo destacar la película."
                    )
                    mensaje_tipo = "error"
            elif accion == "cancelar":
                status_code, respuesta = consumir_api(
                    "PUT",
                    f"/funciones/{funcion_id}/cancelar",
                    datos={"motivo": request.form.get("motivo", "")},
                )
                if status_code == 200 and respuesta.get("ok"):
                    mensaje_estado = _mensaje_cancelacion(respuesta.get("data") or {})
                    mensaje_tipo = "success"
                else:
                    mensaje = (respuesta.get("error") or {}).get(
                        "message", "No se pudo cancelar la función."
                    )
                    mensaje_tipo = "error"
            elif accion == "eliminar":
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
                    resultado = respuesta.get("data") or {}
                    pelicula = (resultado.get("pelicula") or {}).get("titulo")
                    fecha = resultado.get("fecha_hora_proyeccion")
                    identificacion = f" ({pelicula}, {fecha})" if pelicula and fecha else f" (ID {funcion_id})"
                    estado_resultado = resultado.get("estado")
                    if estado_resultado == "en_venta":
                        mensaje_estado = f"La función{identificacion} está a la venta."
                    elif estado_resultado == "agotada":
                        mensaje_estado = f"La función{identificacion} está activa, pero agotada."
                    elif estado_resultado == "venta_cerrada":
                        mensaje_estado = f"La venta de la función{identificacion} está cerrada."
                        if not activo:
                            mensaje_estado += " Las entradas vendidas siguen siendo válidas."
                    else:
                        mensaje_estado = f"Se actualizó el estado de la función{identificacion}."
                    mensaje_tipo = "success"
                else:
                    mensaje_estado = None
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

    if any(status != 200 for status in (status_funciones, status_salas, status_locales, status_peliculas)):
        current_app.logger.error("No se pudieron cargar todos los datos de gestión de funciones")
        mensaje = mensaje or "No se pudieron cargar todos los datos de funciones, salas o películas. Intentá nuevamente."
        mensaje_tipo = "error"

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
        funcion["pelicula_titulo"] = funcion.get("pelicula", {}).get("titulo", "")
        funcion["complejo_nombre"] = funcion.get("sala", {}).get("local", "")
        funcion["sala_nombre"] = funcion.get("sala", {}).get("nombre", "")
        funcion["precio_formateado"] = f"$ {funcion.get('precio_entrada', 0)}"
        funcion["pelicula_activa"] = bool(funcion.get("pelicula_activa", funcion.get("pelicula", {}).get("activa", True)))
        funcion["pelicula_eliminada"] = bool(funcion.get("pelicula_eliminada", funcion.get("pelicula", {}).get("eliminada", False)))
        funcion["sala_activa"] = bool(funcion.get("sala", {}).get("activo", funcion.get("sala_activa", True)))
        funcion["activa"] = bool(funcion.get("activo", True)) and funcion["pelicula_activa"] and not funcion["pelicula_eliminada"] and funcion["sala_activa"]
        _preparar_estado_funcion(funcion)

    if estado_filtro == "activas":
        funciones = [funcion for funcion in funciones if funcion["estado"] in ("en_venta", "agotada")]
    elif estado_filtro == "inactivas":
        funciones = [funcion for funcion in funciones if funcion["estado"] in ("venta_cerrada", "cancelada")]
    elif estado_filtro == "finalizadas":
        funciones = [funcion for funcion in funciones if funcion["finalizada"]]
    # primero las proximas (activas antes que inactivas) y al final las que ya pasaron
    funciones.sort(key=lambda funcion: (funcion["finalizada"], not funcion["activa"], funcion["fecha_hora"]))

    salas = (
        respuesta_salas.get("data", [])
        if status_salas == 200
        else []
    )
    for sala in salas:
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
        elif not funcion_editar["puede_editar"]:
            mensaje_estado = funcion_editar["motivo_bloqueo"]
            mensaje_tipo = "error"
            funcion_editar = None
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
            funcion_editar["pelicula_id"] = funcion_editar.get(
                "pelicula", {}
            ).get("id")
            complejo_form = str(funcion_editar.get("sala", {}).get("local", ""))

    funcion_cancelar = None
    id_cancelar = request.args.get("cancelar", type=int)
    if id_cancelar is not None:
        funcion_cancelar = next((f for f in funciones if f.get("id") == id_cancelar), None)
        if funcion_cancelar is None:
            mensaje_estado = "No se encontró la función seleccionada."
            mensaje_tipo = "error"
        elif not funcion_cancelar["puede_cancelar"]:
            mensaje_estado = funcion_cancelar["motivo_bloqueo"] or (
                "Esta función no tiene entradas vendidas: podés eliminarla o desactivarla."
            )
            mensaje_tipo = "error"
            funcion_cancelar = None

    sala_actual = next(
        (sala for sala in salas if str(sala.get("id")) == editar_sala),
        None,
    ) if editar_sala else None

    return render_template(
        "admin/gestion-funciones.html",
        funciones=funciones,
        funcion_editar=funcion_editar,
        funcion_cancelar=funcion_cancelar,
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
        aviso_sala=aviso_sala,
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
                imagen_url, error_imagen = _imagen_servicio_desde_formulario(imagen)

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
                elif error_imagen:
                    mensaje = error_imagen
                else:
                    if servicio_id:
                        estado, respuesta = actualizar_servicio(
                            token, servicio_id, nombre, descripcion, precio,
                            categoria, imagen_url
                        )
                    else:
                        estado, respuesta = crear_servicio(
                            token, nombre, descripcion, precio, categoria, imagen_url
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


CATEGORIAS_QR = (
    ("entradas", "Entradas", "Cada entrada se canjea por separado."),
    ("vip", "Acceso VIP", "Cada acceso VIP se canjea por separado."),
    ("servicios", "Servicios", "Snacks, pochoclos y bebidas: cada entrega se canjea por separado."),
    ("estacionamiento", "Estacionamiento", "Cada auto se canjea por separado."),
)
CLAVES_CATEGORIAS_QR = {clave for clave, _, _ in CATEGORIAS_QR}


def _mensaje_error_api(respuesta, por_defecto):
    return (respuesta.get("error") or {}).get("message", por_defecto)


def _formatear_fecha_hora(valor):
    try:
        return datetime.strptime(valor, "%a, %d %b %Y %H:%M:%S GMT").strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return valor or ""


def _vista_qr(data, categoria, codigo_qr):
    categorias = data.get("categorias") or {}
    actual = categorias.get(categoria) or {}
    items = actual.get("items") or []

    if categoria == "entradas":
        unidades = [
            {
                "id_entrada": item["id"],
                "etiqueta": f"Butaca {etiqueta_butaca(item['numero_butaca'])}",
                "consumido": item["estado"] == "utilizada",
                "cancelada": item["estado"] == "cancelada",
            }
            for item in items
        ]
    else:
        unidades = []
        for item in items:
            for indice in range(item.get("cantidad", 0)):
                etiqueta = f"Auto {len(unidades) + 1}" if categoria == "estacionamiento" else item["nombre"]
                unidades.append({
                    "id_detalle": item["id_detalle"],
                    "etiqueta": etiqueta,
                    "detalle": "" if categoria == "estacionamiento" else f"Unidad {indice + 1} de {item['cantidad']}",
                    "consumido": indice < item.get("cantidad_usada", 0),
                })

    con_items = [c for c in categorias.values() if c.get("total", 0) > 0]
    qr_cerrado = bool(con_items) and all(c.get("pendientes", 0) == 0 for c in con_items)

    return {
        "codigo_qr": codigo_qr,
        "qr_cerrado": qr_cerrado and not data.get("compra_cancelada"),
        "categoria": categoria,
        "categoria_nombre": next(n for c, n, _ in CATEGORIAS_QR if c == categoria),
        "pelicula": data.get("pelicula") or "Película no especificada",
        "fecha_hora": _formatear_fecha_hora(data.get("fecha_hora")),
        "complejo": data.get("complejo") or "",
        "sala": data.get("sala") or "",
        "butacas_texto": etiquetas_butacas(data.get("butacas") or []) or "Sin butacas activas",
        "compra_cancelada": bool(data.get("compra_cancelada")),
        "fuera_de_fecha": data.get("valida") is False,
        "estado_validacion": data.get("estado_validacion"),
        "mensaje_validacion": data.get("mensaje_validacion") or "",
        "utilizados": actual.get("utilizados", 0),
        "pendientes": actual.get("pendientes", 0),
        "unidades": unidades,
        "pestanas": [
            {
                "clave": clave,
                "nombre": nombre,
                "pendientes": (categorias.get(clave) or {}).get("pendientes", 0),
                "total": (categorias.get(clave) or {}).get("total", 0),
                "activa": clave == categoria,
            }
            for clave, nombre, _ in CATEGORIAS_QR
        ],
    }


def _consultar_vista_qr(codigo_qr, categoria):
    status_code, respuesta = consumir_api("GET", f"/compras/qr/{quote(codigo_qr, safe='')}")
    if status_code != 200:
        return None, _mensaje_error_api(
            respuesta, "El código QR presentado no es válido o no existe."
        )
    return _vista_qr(respuesta.get("data") or {}, categoria, codigo_qr), None


def _estado_qr(vista, aviso, error):
    rechazo = {"titulo": "Resultado · Acceso rechazado", "aprobada": False,
               "mensaje_estado": "Rechazada · Sin ingreso"}
    mensaje = (aviso or {}).get("mensaje") or error
    if vista is None:
        if not (aviso or error):
            return None
        return {**rechazo, "estado": "Código no reconocido",
                "detalle": mensaje or "Revisá el identificador y consultá soporte si persiste."}
    if vista["compra_cancelada"]:
        return {**rechazo, "estado": "Entrada cancelada",
                "detalle": "La compra está cancelada. No permitas el ingreso y derivá la consulta a atención."}
    if vista["fuera_de_fecha"]:
        anticipada = vista["estado_validacion"] == "funcion_anticipada"
        return {**rechazo, "estado": "Función aún no habilitada" if anticipada else "Función vencida",
                "detalle": vista["mensaje_validacion"] or "La función está fuera de la ventana de ingreso permitida."}
    if aviso and aviso["aprobada"]:
        if vista["qr_cerrado"]:
            return {"titulo": "Resultado · QR cerrado", "aprobada": True,
                    "mensaje_estado": "Acceso registrado",
                    "estado": "Canje completo · QR cerrado",
                    "detalle": "Se canjearon todos los servicios del QR. Ya no admite nuevos canjes."}
        return {"titulo": "Resultado · Canje registrado", "aprobada": True,
                "mensaje_estado": "Acceso registrado",
                "estado": f"{vista['categoria_nombre']} canjeado",
                "detalle": aviso["mensaje"]}
    if aviso:
        ya_usado = "ya fue" in mensaje or "ya fueron" in mensaje
        return {**rechazo,
                "estado": "Entrada ya utilizada" if vista["categoria"] == "entradas" and ya_usado
                else ("Servicio ya utilizado" if ya_usado else "Canje no permitido"),
                "detalle": mensaje}
    if vista["qr_cerrado"]:
        return {**rechazo, "titulo": "Resultado · QR cerrado",
                "mensaje_estado": "Rechazada · QR cerrado",
                "estado": "QR ya canjeado por completo",
                "detalle": "Todos los servicios de esta compra ya fueron canjeados. No permitas un segundo ingreso."}
    return {"titulo": "Resultado · Compra válida", "aprobada": True,
            "mensaje_estado": "Aprobada · QR único",
            "estado": f"Pendiente de canje · {vista['categoria_nombre']}",
            "detalle": "Verificá función, fecha y butacas. Luego canjeá la categoría elegida."}


@admin_views.route("/validar-qr", methods=["GET", "POST"])
def validar_qr():
    vista = None
    aviso = None
    error = None
    categoria = request.form.get("categoria", "entradas")
    if categoria not in CLAVES_CATEGORIAS_QR:
        categoria = "entradas"

    if request.method == "POST":
        accion = request.form.get("accion")
        codigo_qr = request.form.get("codigo_qr", "").strip()

        if not codigo_qr:
            error = "Por favor, ingresá un identificador de QR válido."
        elif accion == "canjear":
            datos = {"codigo_qr": codigo_qr, "categoria": categoria}
            for campo in ("id_detalle", "id_entrada"):
                valor = request.form.get(campo, type=int)
                if valor is not None:
                    datos[campo] = valor
            status_code, respuesta = consumir_api("POST", "/compras/validar-qr", datos=datos)
            if status_code == 200:
                vista = _vista_qr(respuesta.get("data") or {}, categoria, codigo_qr)
                aviso = {"aprobada": True, "mensaje": "Canje registrado correctamente."}
            else:
                aviso = {
                    "aprobada": False,
                    "mensaje": _mensaje_error_api(respuesta, "No se pudo registrar el canje."),
                }
                vista, _ = _consultar_vista_qr(codigo_qr, categoria)
        elif accion == "consultar":
            vista, error = _consultar_vista_qr(codigo_qr, categoria)
        else:
            error = "La acción solicitada no es válida."

    return render_template(
        "admin/validar-qr.html",
        vista=vista,
        aviso=aviso,
        error=error,
        estado=_estado_qr(vista, aviso, error),
        categorias=CATEGORIAS_QR,
        categoria=categoria,
        csrf_token=obtener_csrf_token(),
    )
