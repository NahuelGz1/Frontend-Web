from flask import Blueprint, render_template, request, url_for, flash
from services.api_client import consumir_api

admin_views = Blueprint("admin_views", __name__, url_prefix="/admin")

@admin_views.route("/estadisticas")
def estadisticas():
    status_code, respuesta = consumir_api("GET", "/dashboard/ocupacion")

    error_api = False
    if status_code != 200:
        error_api = True
        flash("No se pudieron cargar las estadísticas. El servicio de reportes no está disponible.", "error")
        data = {}
    else:
        data = respuesta.get("data", {}) if isinstance(respuesta, dict) else {}

    resumen_raw = data.get("resumen_general", {})
    vendidas = int(resumen_raw.get("total_vendidas", 0))
    canceladas = int(resumen_raw.get("total_canceladas", 0))
    emitidas = int(resumen_raw.get("total_generadas", 0))
    ingresos_totales = float(resumen_raw.get("total_ingresos", 0))
    cap_total = sum(int(p.get("capacidad_total_ofertada", 0)) for p in data.get("por_pelicula", []))

    resumen = {
        "entradas_netas": vendidas,
        "entradas_emitidas": emitidas,
        "entradas_canceladas": canceladas,
        "capacidad_total": cap_total,
        "ocupacion_porcentaje": round((vendidas / cap_total * 100), 1) if cap_total > 0 else 0,
        "ingresos_entradas": f"$ {ingresos_totales:,.0f}".replace(",", ".") if ingresos_totales > 0 else "$ 0",
        "tasa_cancelacion": round((canceladas / emitidas * 100), 1) if emitidas > 0 else 0,
    }

    ocupacion_funciones = [
        {
            "pelicula_titulo": f.get("pelicula_titulo", ""),
            "fecha_hora": str(f.get("fecha_hora_proyeccion", "")),
            "complejo_nombre": f.get("cine_local", "Cine"),
            "sala_nombre": f.get("sala_nombre", ""),
            "entradas_netas": int(f.get("butacas_ocupadas", 0)),
            "capacidad": int(f.get("sala_capacidad", 0)),
            "ocupacion_porcentaje": round((int(f.get("butacas_ocupadas", 0)) / (int(f.get("sala_capacidad", 1)) or 1) * 100), 1),
            "entradas_emitidas": int(f.get("butacas_ocupadas", 0)) + int(f.get("butacas_canceladas", 0)),
            "entradas_canceladas": int(f.get("butacas_canceladas", 0)),
            "ingresos_formateados": f"$ {float(f.get('total_ingresos', 0)):,.0f}".replace(",", ".") if f.get("total_ingresos") else "$ 0"
        } for f in data.get("por_funcion", [])
    ]

    ocupacion_peliculas = [
        {
            "titulo": p.get("pelicula_titulo", ""),
            "cantidad_funciones": int(p.get("total_funciones", 0)),
            "entradas_netas": int(p.get("total_entradas_vendidas", 0)),
            "capacidad": int(p.get("capacidad_total_ofertada", 0)),
            "ocupacion_porcentaje": round((int(p.get("total_entradas_vendidas", 0)) / (int(p.get("capacidad_total_ofertada", 1)) or 1) * 100), 1),
            "ingresos_formateados": f"$ {float(p.get('total_ingresos', 0)):,.0f}".replace(",", ".") if p.get("total_ingresos") else "$ 0"
        } for p in data.get("por_pelicula", [])
    ]

    ventas_genero = [
        {
            "nombre": g.get("genero", "Sin Género"),
            "entradas_netas": int(g.get("total_entradas", 0)),
            "porcentaje": round((int(g.get("total_entradas", 0)) / vendidas * 100), 1) if vendidas > 0 else 0,
            "ingresos_formateados": f"$ {float(g.get('total_ingresos', 0)):,.0f}".replace(",", ".") if g.get("total_ingresos") else "$ 0"
        } for g in data.get("por_genero", [])
    ]

    raw_franjas = [
        {
            "nombre": f"{int(h.get('hora', 0)):02d}:00 hs",
            "entradas_netas": int(h.get("total_entradas", 0)),
            "cantidad_funciones": 1,
            "porcentaje": round((int(h.get("total_entradas", 0)) / vendidas * 100), 1) if vendidas > 0 else 0,
            "ingresos_formateados": f"$ {float(h.get('total_ingresos', 0)):,.0f}".replace(",", ".") if h.get("total_ingresos") else "$ 0"
        } for h in data.get("por_franja_horaria", [])
    ]

    ventas_franjas = [SimpleNamespace(**item) for item in raw_franjas]

    return render_template(
        "admin/estadisticas.html",
        resumen=resumen,
        ocupacion_funciones=ocupacion_funciones,
        ocupacion_peliculas=ocupacion_peliculas,
        ventas_genero=ventas_genero,
        ventas_franjas=ventas_franjas,
        cancelaciones=[],
        error_api=error_api
    )

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

@admin_views.route("/servicios")
def servicios():
    return render_template("admin/gestion-servicios.html")

@admin_views.route("/validar-qr")
def validar_qr():
    return render_template("admin/validar-qr.html")