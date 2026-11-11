import os
from datetime import timedelta
from pathlib import Path

from cachelib.file import FileSystemCache
from dotenv import load_dotenv
from flask import Flask, g, render_template, request, session
from flask_session import Session

from routes.admin_views import admin_views
from routes.auth_security import csrf_token
from routes.auth_views import auth_views_bp
from routes.cliente_views import cliente_views_bp


def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        API_BASE_URL=os.getenv("API_BASE_URL", "http://127.0.0.1:5000/api"),
        SUPER_ADMIN_EMAIL=os.getenv("SUPER_ADMIN_EMAIL", "cine_paradiso@admin.com").strip().lower(),
        SESSION_TYPE="cachelib",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"] or len(app.config["SECRET_KEY"]) < 32:
        raise RuntimeError("Configurá SECRET_KEY con al menos 32 caracteres")
    if "SESSION_CACHELIB" not in app.config:
        directorio = Path(app.instance_path) / "sessions"
        directorio.mkdir(parents=True, exist_ok=True, mode=0o700)
        app.config["SESSION_CACHELIB"] = FileSystemCache(str(directorio), mode=0o600)
    Session(app)
    app.register_blueprint(admin_views)
    app.register_blueprint(auth_views_bp)
    app.register_blueprint(cliente_views_bp)

    @app.context_processor
    def contexto_auth():
        usuario = getattr(g, "current_user", None)
        if usuario is None and session.get("usuario"):
            usuario = {**session["usuario"], "is_authenticated": True}
        return {"csrf_token": csrf_token(), "current_user": usuario}

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(503)
    def error_formulario(error):
        return render_template("auth/error.html", mensaje=error.description), error.code

    @app.after_request
    def privacidad(response):
        if request.blueprint == "auth_views" or session.get("access_token"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
