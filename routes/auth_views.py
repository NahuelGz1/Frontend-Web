from flask import Blueprint, render_template, redirect, url_for, request, flash
from services.api_client import consumir_api

auth_views_bp = Blueprint("auth_views", __name__, url_prefix="/auth")

@auth_views_bp.route("/iniciar-sesion")
def iniciar_sesion():
    return render_template("auth/iniciar-sesion.html")

@auth_views_bp.route("/cerrar-sesion")
def cerrar_sesion():
    return redirect(url_for("cliente_views.inicio"))

@auth_views_bp.route("/registrarse", methods=["GET", "POST"])
def registrarse():
    if request.method == "POST":
        nombre = request.form.get("nombre", "")
        apellido = request.form.get("apellido", "")
        email = request.form.get("email", "")
        password = request.form.get("password", "")

        payload = {
            "nombre": f"{nombre} {apellido}".strip(),
            "email": email,
            "password": password
        }

        status_code, respuesta = consumir_api("POST", "/auth/register", payload)

        if status_code in (200, 201):
            flash("¡Cuenta creada con éxito! Ya podés iniciar sesión.", "success")
            return redirect(url_for("auth_views.iniciar_sesion"))
        else:
            mensaje_error = respuesta.get("error", {}).get("message") or respuesta.get("message") or "Error al registrar usuario."
            flash(mensaje_error, "danger")

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