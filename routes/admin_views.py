from flask import Blueprint, render_template

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
    return render_template("admin/gestion-servicios.html")

@admin_views.route("/validar-qr")
def validar_qr():
    return render_template("admin/validar-qr.html")