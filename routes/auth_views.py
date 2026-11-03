from flask import Blueprint, render_template, redirect, url_for

auth_views_bp = Blueprint("auth_views", __name__, url_prefix="/auth")

@auth_views_bp.route("/iniciar-sesion")
def iniciar_sesion():
    return render_template("auth/iniciar-sesion.html")

@auth_views_bp.route("/cerrar-sesion")
def cerrar_sesion():
    return redirect(url_for("cliente_views.inicio"))

@auth_views_bp.route("/registrarse")
def registrarse():
    return render_template("auth/registrarse.html")

@auth_views_bp.route("/recuperar-contrasena")
def recuperar_contrasena():
    return render_template("auth/recuperar-contrasena.html")

@auth_views_bp.route("/restablecer-contrasena")
def restablecer_contrasena():
    return render_template("auth/restablecer-contrasena.html")

@auth_views_bp.route("/cambiar-contrasena")
def cambiar_contrasena():
    return render_template("auth/cambiar-contrasena.html")