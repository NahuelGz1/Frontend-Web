import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from routes.auth_security import validar_csrf, usuario_valido, requiere_sesion
from services import auth_service


auth_views_bp = Blueprint("auth_views", __name__, url_prefix="/auth")


@auth_views_bp.before_request
def proteger_formularios():
    if request.method == "POST":
        validar_csrf()


def mostrar(plantilla, error=None, codigo=200):
    valores = {clave: request.form.get(clave, "") for clave in ("nombre", "apellido", "email")}
    return render_template(f"auth/{plantilla}.html", error_auth=error, valores=valores), codigo


def email_formulario():
    email = request.form.get("email", "").strip().lower()
    if len(email) > 100 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Ingresá un correo electrónico válido.")
    return email


def nueva_password(campo="password"):
    password = request.form.get(campo, "")
    if not 8 <= len(password) <= 128:
        raise ValueError("La contraseña debe tener entre 8 y 128 caracteres.")
    if password != request.form.get("confirm_password"):
        raise ValueError("Las contraseñas no coinciden.")
    return password


def error_respuesta(respuesta):
    error = respuesta.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    current_app.logger.error("Respuesta de autenticación incompleta")
    return "No fue posible completar la operación. Intentá nuevamente."


@auth_views_bp.route("/iniciar-sesion", methods=["GET", "POST"])
def iniciar_sesion():
    if request.method == "POST":
        session.pop("access_token", None)
        session.pop("usuario", None)
        try:
            email = email_formulario()
            password = request.form.get("password", "")
            if not 1 <= len(password) <= 128:
                raise ValueError("Ingresá tu contraseña.")
        except ValueError as error:
            return mostrar("iniciar-sesion", str(error), 400)
        codigo, respuesta = auth_service.iniciar_sesion(email, password)
        if codigo != 200:
            return mostrar("iniciar-sesion", error_respuesta(respuesta), codigo)
        datos = respuesta.get("data")
        if not isinstance(datos, dict) or not isinstance(datos.get("token"), str) or not datos["token"] or not usuario_valido(datos.get("usuario")):
            current_app.logger.error("Login sin token o usuario válido")
            return mostrar("iniciar-sesion", "Respuesta de autenticación inválida.", 502)
        session.clear()
        session["access_token"] = datos["token"]
        session["usuario"] = datos["usuario"]
        session.permanent = True
        current_app.session_interface.regenerate(session)
        destino = "admin_views.estadisticas" if datos["usuario"]["rol"] == "administrador" else "cliente_views.inicio"
        return redirect(url_for(destino), code=303)
    return mostrar("iniciar-sesion")


@auth_views_bp.route("/cerrar-sesion", methods=["GET", "POST"])
def cerrar_sesion():
    if request.method == "GET":
        return render_template("auth/cerrar-sesion.html")
    token = session.get("access_token")
    notificacion_fallida = False
    if token:
        codigo, _ = auth_service.cerrar_sesion(token)
        notificacion_fallida = codigo not in (200, 401)
    session.clear()
    if notificacion_fallida:
        flash("Se cerró la sesión local, pero no se pudo notificar al servidor.", "error")
    flash("Sesión cerrada.", "success")
    return redirect(url_for("auth_views.iniciar_sesion"), code=303)


@auth_views_bp.route("/registrarse", methods=["GET", "POST"])
def registrarse():
    if request.method == "POST":
        try:
            nombre = request.form.get("nombre", "").strip()
            apellido = request.form.get("apellido", "").strip()
            completo = f"{nombre} {apellido}"
            if not nombre or not apellido or len(completo) > 100:
                raise ValueError("Ingresá nombre y apellido (hasta 100 caracteres en total).")
            email = email_formulario()
            password = nueva_password()
        except ValueError as error:
            return mostrar("registrarse", str(error), 400)
        codigo, respuesta = auth_service.registrar(completo, email, password)
        if codigo != 201:
            return mostrar("registrarse", error_respuesta(respuesta), codigo)
        flash("Cuenta creada. Ya podés iniciar sesión.", "success")
        return redirect(url_for("auth_views.iniciar_sesion"), code=303)
    return mostrar("registrarse")


@auth_views_bp.route("/recuperar-contrasena", methods=["GET", "POST"])
def recuperar_contrasena():
    if request.method == "POST":
        try:
            email = email_formulario()
        except ValueError as error:
            return mostrar("recuperar-contrasena", str(error), 400)
        codigo, respuesta = auth_service.recuperar(email)
        if codigo != 200:
            return mostrar("recuperar-contrasena", error_respuesta(respuesta), codigo)
        flash("Si el correo está asociado a una cuenta, recibirás un enlace.", "success")
        return redirect(url_for("auth_views.recuperar_contrasena"), code=303)
    return mostrar("recuperar-contrasena")


@auth_views_bp.route("/restablecer-contrasena", methods=["GET", "POST"])
def restablecer_contrasena():
    if request.method == "GET" and "token" in request.args:
        session.pop("reset_token", None)
        token = request.args.get("token", "")
        if not token or len(token) > 2048:
            return mostrar("restablecer-contrasena", "El enlace es inválido.", 400)
        session["reset_token"] = token
        return redirect(url_for("auth_views.restablecer_contrasena"), code=303)
    token = session.get("reset_token")
    if not token:
        return mostrar("restablecer-contrasena", "Abrí el enlace enviado a tu correo para restablecer la contraseña.", 400)
    if request.method == "POST":
        try:
            password = nueva_password("password_nueva")
        except ValueError as error:
            return mostrar("restablecer-contrasena", str(error), 400)
        codigo, respuesta = auth_service.restablecer(token, password)
        if codigo != 200:
            return mostrar("restablecer-contrasena", error_respuesta(respuesta), codigo)
        session.clear()
        flash("Contraseña restablecida. Iniciá sesión con tu nueva clave.", "success")
        return redirect(url_for("auth_views.iniciar_sesion"), code=303)
    return mostrar("restablecer-contrasena")


@auth_views_bp.route("/cambiar-contrasena")
@requiere_sesion
def cambiar_contrasena():
    return render_template("auth/cambiar-contrasena.html")
