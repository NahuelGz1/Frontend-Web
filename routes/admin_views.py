from flask import Blueprint, render_template
from services.gestion_servicios_service import obtener_servicios

admin_views = Blueprint("admin_views", __name__, url_prefix="/admin")

@admin_views.route("/estadisticas")
def estadisticas():
    return render_template("admin/estadisticas.html")

@admin_views.route("/peliculas")
def peliculas():
    return render_template("admin/gestion-peliculas.html")

@admin_views.route("/funciones")
def funciones():
    return render_template("admin/gestion-funciones.html")

@admin_views.route("/servicios")
def servicios():
    """
    Obtiene los servicios del backend y los muestra
    en la pantalla de administración.
    """

    estado, respuesta = obtener_servicios()

    if estado != 200 or not respuesta.get("ok"):
        return render_template(
            "admin/gestion-servicios.html",
            servicios=[],
            mensaje="No se pudieron cargar los servicios."
        ), 502

    lista_servicios = respuesta.get("data") or []

    for servicio in lista_servicios:
        servicio["precio_formateado"] = f"$ {servicio['precio']:.2f}"
        servicio["activo"] = True

    return render_template(
        "admin/gestion-servicios.html",
        servicios=lista_servicios
    )

@admin_views.route("/validar-qr")
def validar_qr():
    return render_template("admin/validar-qr.html")