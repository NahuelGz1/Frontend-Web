from flask import Blueprint, render_template, request
from services.api_client import consumir_api

admin_views = Blueprint("admin_views", __name__, url_prefix="/admin")

@admin_views.route("/estadisticas")
def estadisticas():
    return render_template("admin/estadisticas.html")

@admin_views.route("/peliculas")
def peliculas():
    return render_template("admin/gestion-peliculas.html")

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
            f"/funciones/salas/{sala_id}",
            datos=datos,
        )

    status_code, respuesta = consumir_api(
        "GET",
        "/funciones/salas",
    )
    status_locales, respuesta_locales = consumir_api(
        "GET",
        "/funciones/locales",
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
                #ajusta el formato del datetime para que sea compatible con el back
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
        "/funciones/salas",
    )

    status_locales, respuesta_locales = consumir_api(
        "GET",
        "/funciones/locales",
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

@admin_views.route("/servicios")
def servicios():
    return render_template("admin/gestion-servicios.html")

@admin_views.route("/validar-qr")
def validar_qr():
    return render_template("admin/validar-qr.html")