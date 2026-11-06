from flask import Blueprint, render_template, redirect, url_for, request, session
from secrets import token_urlsafe, compare_digest

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

@auth_views_bp.route("/cambiar-contrasena", methods=["GET", "POST"])
def cambiar_contrasena():
    """
    Muestra el formulario de cambio de contraseña y valida
    los datos ingresados por el usuario.
    """

    csrf_token = session.get("csrf_cambio_contrasena")

    if not csrf_token:
        csrf_token = token_urlsafe(32)
        session["csrf_cambio_contrasena"] = csrf_token

    if request.method == "GET":
        return render_template(
            "auth/cambiar-contrasena.html",
            csrf_token=csrf_token
        )

    token_recibido = request.form.get("csrf_token", "")

    if not token_recibido or not compare_digest(token_recibido, csrf_token):
        return render_template(
            "auth/cambiar-contrasena.html",
            csrf_token=csrf_token,
            error="Solicitud inválida. Volvé a intentar."
        ), 400

    contrasena_actual = request.form.get("password_actual", "")
    contrasena_nueva = request.form.get("password_nueva", "")
    confirmar_contrasena = request.form.get("confirm_password", "")

    if not contrasena_actual or not contrasena_nueva or not confirmar_contrasena:
        return render_template(
            "auth/cambiar-contrasena.html",
            csrf_token=csrf_token,
            error="Todos los campos son obligatorios."
        ), 400

    if contrasena_nueva != confirmar_contrasena:
        return render_template(
            "auth/cambiar-contrasena.html",
            csrf_token=csrf_token,
            error="Las contraseñas nuevas no coinciden."
        ), 400

    if contrasena_actual == contrasena_nueva:
        return render_template(
            "auth/cambiar-contrasena.html",
            csrf_token=csrf_token,
            error="La contraseña nueva debe ser diferente de la actual."
        ), 400

    return render_template(
        "auth/cambiar-contrasena.html",
        csrf_token=csrf_token,
        error="Falta conectar la autenticación para completar el cambio."
    ), 503