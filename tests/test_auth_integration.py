import os
import re
import tempfile
import time
import unittest
import uuid
from urllib.parse import urlsplit

import requests
from cachelib.file import FileSystemCache

from app import create_app


@unittest.skipUnless(
    os.getenv("TEST_API_URL") and os.getenv("TEST_MAIL_URL"),
    "Requiere backend/MySQL y Mailpit aislados",
)
class AuthIntegrationTest(unittest.TestCase):
    def test_registro_login_correo_reset_y_login_nuevo(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                "TESTING": True, "SECRET_KEY": "test-key-not-for-production-123456789",
                "SESSION_CACHELIB": FileSystemCache(directory),
                "API_BASE_URL": os.environ["TEST_API_URL"],
            })
            client = app.test_client()
            email = f"auth-{uuid.uuid4().hex}@example.test"

            def post(ruta, **campos):
                client.get("/auth/iniciar-sesion")
                with client.session_transaction() as session:
                    csrf = session["csrf_token"]
                return client.post("/auth/" + ruta, data={"csrf_token": csrf, **campos})

            self.assertEqual(post(
                "registrarse", nombre="Persona", apellido="Integracion", email=email,
                password="Password-inicial-67", confirm_password="Password-inicial-67",
            ).status_code, 303)
            self.assertEqual(post(
                "iniciar-sesion", email=email, password="Password-inicial-67",
            ).status_code, 303)
            self.assertEqual(client.get("/admin/estadisticas").status_code, 403)
            with client.session_transaction() as session:
                acceso_anterior = session["access_token"]
            self.assertEqual(post("recuperar-contrasena", email=email).status_code, 303)
            mensaje_id = None
            for _ in range(20):
                response = requests.get(os.environ["TEST_MAIL_URL"] + "/api/v1/messages", timeout=5)
                response.raise_for_status()
                for mensaje in response.json()["messages"]:
                    if any(destino["Address"] == email for destino in mensaje["To"]):
                        mensaje_id = mensaje["ID"]
                        break
                if mensaje_id:
                    break
                time.sleep(0.1)
            self.assertIsNotNone(mensaje_id, "No llegó el correo de recuperación al buzón local")
            correo = requests.get(
                os.environ["TEST_MAIL_URL"] + f"/api/v1/message/{mensaje_id}", timeout=5,
            )
            correo.raise_for_status()
            enlace = re.search(r"https?://[^\s]+", correo.json()["Text"]).group()
            parsed = urlsplit(enlace)
            response = client.get(parsed.path + "?" + parsed.query)
            self.assertEqual(response.status_code, 303)
            self.assertNotIn("token=", response.location)
            self.assertEqual(post(
                "restablecer-contrasena", password_nueva="Password-nueva-67",
                confirm_password="Password-nueva-67",
            ).status_code, 303)
            self.assertEqual(post(
                "iniciar-sesion", email=email, password="Password-inicial-67",
            ).status_code, 401)
            self.assertEqual(post(
                "iniciar-sesion", email=email, password="Password-nueva-67",
            ).status_code, 303)
            response = requests.get(
                os.environ["TEST_API_URL"] + "/auth/usuarios/me",
                headers={"Authorization": "Bearer " + acceso_anterior}, timeout=5,
            )
            self.assertEqual(response.status_code, 401)
            client.get(parsed.path + "?" + parsed.query)
            self.assertEqual(post(
                "restablecer-contrasena", password_nueva="Password-tercera-67",
                confirm_password="Password-tercera-67",
            ).status_code, 400)
            self.assertEqual(post("cerrar-sesion").status_code, 303)


if __name__ == "__main__":
    unittest.main()
