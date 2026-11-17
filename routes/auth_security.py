import hmac
import secrets
from functools import wraps

from flask import abort, current_app, flash, g, redirect, request, session, url_for

from services import auth_service


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def validar_csrf():
    recibido = request.form.get("csrf_token", "")
    esperado = session.get("csrf_token")
    if not esperado or not hmac.compare_digest(esperado.encode(), recibido.encode()):
        current_app.logger.warning("Formulario rechazado por CSRF")
        abort(400, description="El formulario venció. Recargá la página e intentá nuevamente.")


def usuario_valido(usuario):
    return (
        isinstance(usuario, dict)
        and isinstance(usuario.get("id"), int)
        and isinstance(usuario.get("nombre"), str)
        and isinstance(usuario.get("email"), str)
        and usuario.get("rol") in ("cliente", "administrador")
    )


def verificar_sesion(rol=None):
    token = session.get("access_token")
    if not token:
        flash("Iniciá sesión para acceder.", "error")
        return redirect(url_for("auth_views.iniciar_sesion"))
    codigo, respuesta = auth_service.perfil(token)
    if codigo in (401, 403, 404):
        session.clear()
        flash("Tu sesión ya no es válida. Ingresá nuevamente.", "error")
        return redirect(url_for("auth_views.iniciar_sesion"))
    usuario = respuesta.get("data")
    if codigo != 200 or not usuario_valido(usuario):
        current_app.logger.error("No se pudo verificar la sesión con la API")
        abort(503, description="No se pudo verificar tu sesión. Intentá más tarde.")
    if rol and usuario["rol"] != rol:
        abort(403, description="Tu cuenta no tiene permiso para acceder a esta página.")
    session["usuario"] = usuario
    g.current_user = {**usuario, "is_authenticated": True}
    return None


def requiere_sesion(vista):
    @wraps(vista)
    def protegida(*args, **kwargs):
        rechazo = verificar_sesion()
        return rechazo if rechazo is not None else vista(*args, **kwargs)
    return protegida
