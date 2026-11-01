from flask import Flask
from routes import admin_views_bp

app = Flask(__name__)
app.config["SECRET_KEY"] = "cine_paradiso_secret_key"

app.register_blueprint(admin_views_bp)

if __name__ == "__main__":
    app.run(port=3000, debug=True)
