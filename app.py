import os
from dotenv import load_dotenv
from flask import Flask
from routes.admin_views import admin_views
from routes.auth_views import auth_views_bp
from routes.cliente_views import cliente_views_bp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secreto_por_defecto")

app.register_blueprint(admin_views)
app.register_blueprint(auth_views_bp)
app.register_blueprint(cliente_views_bp)

if __name__ == "__main__":
    puerto = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=puerto, debug=True)