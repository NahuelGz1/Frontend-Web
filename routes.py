from flask import Blueprint, render_template

admin_views_bp = Blueprint("admin_views", __name__, url_prefix="/admin")

@admin_views_bp.route("/peliculas")
def peliculas():
    return render_template("admin/gestion-peliculas.html")

@admin_views_bp.route("/funciones")
def funciones():
    return render_template("admin/gestion-funciones.html")

@admin_views_bp.route("/servicios")
def servicios():
    return render_template("admin/gestion-servicios.html")

@admin_views_bp.route("/validar-qr")
def validar_qr():
    return render_template("admin/validar-qr.html")

@admin_views_bp.route("/estadisticas")
def estadisticas():
    return render_template("admin/estadisticas.html")
