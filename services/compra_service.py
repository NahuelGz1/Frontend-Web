# Lo que el cliente va eligiendo queda en session["compra"]: id_funcion, butacas y servicios
# Despues de comprar, session["compra_confirmada"] tiene lo que muestra compra-exitosa.html
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from flask import session

from services.api_client import consumir_api

BUTACAS_POR_FILA = 10
MAXIMO_BUTACAS_POR_COMPRA = 10
LETRAS_FILAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre")
FORMATO_FECHA_API = "%Y-%m-%d %H:%M:%S"
ZONA_ARGENTINA = timezone(timedelta(hours=-3))

CLAVE_COMPRA = "compra"
CLAVE_COMPRA_CONFIRMADA = "compra_confirmada"
# Mismas claves que usa el inicio de sesion (3.1.1)
CLAVE_TOKEN = "access_token"
CLAVE_CSRF = "csrf_token"

ERROR_GENERICO = "No pudimos comunicarnos con el servidor. Intentá de nuevo en unos minutos."


def hay_sesion_iniciada():
    return bool(session.get(CLAVE_TOKEN))


def token_csrf():
    if CLAVE_CSRF not in session:
        session[CLAVE_CSRF] = secrets.token_urlsafe(32)
    return session[CLAVE_CSRF]


def csrf_valido(recibido):
    esperado = session.get(CLAVE_CSRF, "")
    return bool(esperado) and hmac.compare_digest(esperado.encode(), (recibido or "").encode())


def _cabecera_autorizacion():
    return {"Authorization": f"Bearer {session.get(CLAVE_TOKEN, '')}"}

def _numero_con_puntos(monto):
    return f"{monto:,.0f}".replace(",", ".")


def formatear_precio(monto):
    return f"${_numero_con_puntos(monto)}"


def _nombre_fila(indice):
    return LETRAS_FILAS[indice] if indice < len(LETRAS_FILAS) else str(indice + 1)


def _ubicacion(numero_butaca):
    # El back numera las butacas de 1 a capacidad, aca se pasa a fila y numero
    indice_fila, posicion = divmod(numero_butaca - 1, BUTACAS_POR_FILA)
    return _nombre_fila(indice_fila), posicion + 1


def etiqueta_butaca(numero_butaca):
    fila, numero = _ubicacion(numero_butaca)
    return f"{fila}{numero}"


def _texto_butacas(numeros):
    return "Butacas " + ", ".join(etiqueta_butaca(n) for n in sorted(numeros))


def _fecha_de_funcion(funcion):
    try:
        return datetime.strptime(funcion.get("fecha_hora_proyeccion") or "", FORMATO_FECHA_API)
    except ValueError:
        return None


def _ahora():
    return datetime.now(ZONA_ARGENTINA).replace(tzinfo=None)


def _mensaje_de_error(status_code, respuesta, por_defecto):
    if status_code >= 500:
        return por_defecto
    return (respuesta.get("error") or {}).get("message") or por_defecto

