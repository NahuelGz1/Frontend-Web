import tempfile
import unittest
from unittest.mock import Mock, patch

import requests
from cachelib.file import FileSystemCache

from app import create_app


class AuthTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = create_app({
            "TESTING": True, "SECRET_KEY": "test-key-not-for-production-123456789",
            "SESSION_CACHELIB": FileSystemCache(self.directory.name),
            "API_BASE_URL": "http://api.test/api",
        })
        self.client = self.app.test_client()
        self.http = patch("services.api_client.requests.request").start()
        self.addCleanup(patch.stopall)

    def response(self, codigo=200, data=None, ok=True):
        result = Mock(status_code=codigo)
        result.json.return_value = {"ok": ok, "data": data} if ok else {
            "ok": False, "error": {"message": "Solicitud rechazada por la API"},
        }
        self.http.return_value = result

    def post(self, ruta, **datos):
        with self.client.session_transaction() as sesion:
            sesion["csrf_token"] = "csrf-prueba"
        return self.client.post("/auth/" + ruta, data={"csrf_token": "csrf-prueba", **datos})

    def login(self, rol="cliente"):
        self.usuario = {"id": 42, "nombre": "Persona Prueba", "email": "persona@example.test", "rol": rol}
        self.response(data={"token": "jwt-test-no-real", "usuario": self.usuario})
        return self.post("iniciar-sesion", email="persona@example.test", password="Password-prueba-67")

    def test_formularios_get_nativos_y_sin_peticiones_api(self):
        for ruta in ("iniciar-sesion", "registrarse", "recuperar-contrasena"):
            response = self.client.get("/auth/" + ruta)
            self.assertEqual(response.status_code, 200)
            self.assertIn('method="POST"', response.text)
            self.assertIn('name="csrf_token"', response.text)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.http.assert_not_called()

    def test_login_roles_sesion_server_side_y_regeneracion(self):
        for rol, destino in (("cliente", "/"), ("administrador", "/admin/estadisticas")):
            self.client.get("/auth/iniciar-sesion")
            anterior = self.client.get_cookie("session").value
            response = self.login(rol)
            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.location, destino)
            cookie = self.client.get_cookie("session")
            self.assertNotEqual(anterior, cookie.value)
            self.assertNotIn("jwt-test", cookie.value)
            self.assertTrue(cookie.http_only)
            with self.client.session_transaction() as sesion:
                self.assertEqual(sesion["usuario"]["rol"], rol)
                self.assertEqual(sesion["access_token"], "jwt-test-no-real")
                self.assertNotIn("password", sesion)
            argumentos = self.http.call_args.kwargs
            self.assertEqual(argumentos["url"], "http://api.test/api/auth/login")
            self.assertEqual(argumentos["timeout"], 10)
            self.assertFalse(argumentos["allow_redirects"])

    def test_csrf_incorrecto_no_llama_api(self):
        for ruta in ("iniciar-sesion", "registrarse", "recuperar-contrasena", "restablecer-contrasena", "cerrar-sesion"):
            response = self.client.post("/auth/" + ruta, data={"csrf_token": "invalido"})
            self.assertEqual(response.status_code, 400)
        self.http.assert_not_called()
        self.client.get("/auth/iniciar-sesion")
        self.assertEqual(self.client.post("/auth/iniciar-sesion", data={"csrf_token": "inválido"}).status_code, 400)

    def test_registro_mapea_nombre_y_omite_rol(self):
        self.response(201, data={"id": 42})
        response = self.post(
            "registrarse", nombre="Persona", apellido="Prueba", email="PERSONA@example.test",
            password="Password-prueba-67", confirm_password="Password-prueba-67", rol="administrador",
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.http.call_args.kwargs["json"], {
            "nombre": "Persona Prueba", "email": "persona@example.test", "password": "Password-prueba-67",
        })
        response = self.post("registrarse", nombre="Persona", apellido="Prueba", email="persona@example.test",
                             password="Password-prueba-67", confirm_password="otra")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('value="Password-prueba-67"', response.text)
        self.assertIn('value="Persona"', response.text)

    def test_recuperacion_y_reset_con_token_solo_en_servidor(self):
        self.response()
        self.assertEqual(self.post("recuperar-contrasena", email="persona@example.test").status_code, 303)
        response = self.client.get("/auth/restablecer-contrasena?token=token-de-correo")
        self.assertEqual(response.status_code, 303)
        self.assertNotIn("token=", response.location)
        response = self.client.get(response.location)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("token-de-correo", response.text)
        response = self.post("restablecer-contrasena", password_nueva="Password-nueva-67",
                             confirm_password="Password-nueva-67")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.http.call_args.kwargs["json"], {
            "token": "token-de-correo", "password": "Password-nueva-67",
        })
        with self.client.session_transaction() as sesion:
            self.assertNotIn("reset_token", sesion)

    def test_reset_sin_token_no_llama_api(self):
        self.assertEqual(self.client.get("/auth/restablecer-contrasena").status_code, 400)
        self.http.assert_not_called()

    def test_errores_http_timeout_json_y_login_incompleto(self):
        for codigo in (400, 401, 409, 503):
            self.response(codigo, ok=False)
            response = self.post("iniciar-sesion", email="persona@example.test", password="pass")
            self.assertEqual(response.status_code, codigo)
            self.assertIn("Solicitud rechazada", response.text)
        self.http.side_effect = requests.Timeout
        self.assertEqual(self.post("iniciar-sesion", email="persona@example.test", password="pass").status_code, 504)
        self.http.side_effect = requests.ConnectionError
        self.assertEqual(self.post("iniciar-sesion", email="persona@example.test", password="pass").status_code, 503)
        self.http.side_effect = None
        self.response()
        self.http.return_value.json.side_effect = ValueError()
        self.assertEqual(self.post("iniciar-sesion", email="persona@example.test", password="pass").status_code, 502)
        self.response(data={"usuario": {"rol": "administrador"}})
        self.assertEqual(self.post("iniciar-sesion", email="persona@example.test", password="pass").status_code, 502)

    def test_admin_solo_por_rol_validado_en_api(self):
        self.assertEqual(self.client.get("/admin/estadisticas").status_code, 302)
        self.login()
        self.response(data=self.usuario)
        self.assertEqual(self.client.get("/admin/estadisticas").status_code, 403)
        self.usuario["rol"] = "administrador"
        self.response(data=self.usuario)
        self.assertEqual(self.client.get("/admin/estadisticas").status_code, 200)
        self.assertEqual(self.http.call_args.kwargs["headers"]["Authorization"], "Bearer jwt-test-no-real")
        self.response(401, ok=False)
        self.assertEqual(self.client.get("/admin/estadisticas").status_code, 302)
        with self.client.session_transaction() as sesion:
            self.assertNotIn("access_token", sesion)

    def test_logout_get_no_modifica_y_post_elimina_sesion(self):
        self.login()
        self.http.reset_mock()
        self.assertEqual(self.client.get("/auth/cerrar-sesion").status_code, 200)
        self.http.assert_not_called()
        self.response()
        self.assertEqual(self.post("cerrar-sesion").status_code, 303)
        with self.client.session_transaction() as sesion:
            self.assertNotIn("access_token", sesion)


if __name__ == "__main__":
    unittest.main()
