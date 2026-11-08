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

def _obtener_funcion(funcion_id):
    status_code, respuesta = consumir_api("GET", f"/funciones/{funcion_id}", headers=_cabecera_autorizacion())
    if status_code == 200:
        return respuesta.get("data") or {}, None
    if status_code == 401:
        return None, "Tu sesión venció. Volvé a iniciar sesión para seguir con la compra."
    if status_code == 404:
        return None, "La función que elegiste no existe."
    return None, _mensaje_de_error(status_code, respuesta, ERROR_GENERICO)


def _obtener_poster(pelicula_id):
    status_code, respuesta = consumir_api("GET", f"/peliculas/{pelicula_id}")
    if status_code != 200:
        return ""
    pelicula = respuesta.get("data") or {}
    return pelicula.get("poster_url") or pelicula.get("poster") or ""


def _servicios_con_precio(elegidos):
    # El precio sale del catalogo del back, no de lo que manda el navegador
    if not elegidos:
        return [], None, None
    status_code, respuesta = consumir_api("GET", "/servicios")
    if status_code != 200:
        return None, None, "No pudimos cargar los servicios adicionales. Intentá de nuevo."
    catalogo = {servicio["id"]: servicio for servicio in respuesta.get("data") or []}
    servicios = []
    for elegido in elegidos:
        servicio = catalogo.get(elegido.get("id_servicio"))
        cantidad = elegido.get("cantidad")
        if servicio and isinstance(cantidad, int) and cantidad > 0:
            servicios.append({"id_servicio": servicio["id"], "nombre": servicio["nombre"],
                              "cantidad": cantidad, "precio": float(servicio["precio"])})
    aviso = None
    if len(servicios) < len(elegidos):
        aviso = "Algún servicio que elegiste ya no está disponible y lo quitamos del resumen."
    return servicios, aviso, None

def armar_filas(butacas):
    filas = []
    for butaca in sorted(butacas, key=lambda b: b["numero_butaca"]):
        numero_butaca = butaca["numero_butaca"]
        indice_fila = (numero_butaca - 1) // BUTACAS_POR_FILA
        while len(filas) <= indice_fila:
            filas.append({"nombre": _nombre_fila(len(filas)), "butacas": []})
        filas[indice_fila]["butacas"].append({
            "id": numero_butaca,
            "numero": _ubicacion(numero_butaca)[1],
            "ocupada": butaca.get("estado") != "disponible",
        })
    return filas


def datos_del_mapa(funcion_id):
    vacio = {"funcion": {"id": funcion_id, "pelicula": {"titulo": ""}, "sala": {"nombre": ""},
                         "fecha": "", "horario": ""}, "filas": []}
    funcion, error = _obtener_funcion(funcion_id)
    if error:
        return {**vacio, "error_mapa": error}

    fecha = _fecha_de_funcion(funcion)
    if fecha is None or fecha <= _ahora():
        return {**vacio, "error_mapa": "Esta función ya comenzó. Elegí otra en la cartelera."}

    status_code, respuesta = consumir_api("GET", f"/funciones/{funcion_id}/butacas")
    if status_code != 200:
        return {**vacio, "error_mapa": _mensaje_de_error(status_code, respuesta, ERROR_GENERICO)}

    dia = f"{DIAS[fecha.weekday()]} {fecha:%d/%m/%Y}"
    return {
        "funcion": {
            "id": funcion_id,
            "precio": funcion.get("precio_entrada") or 0,
            "fecha": dia,
            "horario": fecha.strftime("%H:%M"),
            "pelicula": funcion.get("pelicula") or {},
            "sala": funcion.get("sala") or {},
        },
        "filas": armar_filas(respuesta.get("data") or []),
        "error_mapa": None,
    }


def validar_seleccion(valores, filas):
    existentes = {butaca["id"] for fila in filas for butaca in fila["butacas"]}
    libres = {butaca["id"] for fila in filas for butaca in fila["butacas"] if not butaca["ocupada"]}
    elegidas = {int(valor) for valor in valores if valor.isdigit()}
    siguen_libres = sorted(elegidas & libres)

    if not valores:
        return [], "Elegí al menos una butaca para continuar."
    if any(not valor.isdigit() for valor in valores) or not elegidas <= existentes:
        return siguen_libres, "Alguna de las butacas elegidas no existe en esta sala."
    if len(elegidas) > MAXIMO_BUTACAS_POR_COMPRA:
        return siguen_libres, f"Podés elegir hasta {MAXIMO_BUTACAS_POR_COMPRA} butacas por compra."
    ocupadas = sorted(elegidas - libres)
    if ocupadas:
        etiquetas = ", ".join(etiqueta_butaca(n) for n in ocupadas)
        return siguen_libres, f"Estas butacas ya están ocupadas: {etiquetas}. Elegí otras."
    return sorted(elegidas), None


def guardar_seleccion(funcion_id, butacas):
    anterior = session.get(CLAVE_COMPRA) or {}
    session[CLAVE_COMPRA] = {"id_funcion": funcion_id, "butacas": butacas,
                             "servicios": anterior.get("servicios", [])}


def seleccion_previa(funcion_id):
    compra = session.get(CLAVE_COMPRA) or {}
    return compra.get("butacas", []) if compra.get("id_funcion") == funcion_id else []

def funcion_en_curso():
    return (session.get(CLAVE_COMPRA) or {}).get("id_funcion")


def email_del_usuario():
    usuario = session.get("usuario") or {}
    if usuario.get("email"):
        return usuario["email"]
    status_code, respuesta = consumir_api("GET", "/auth/usuarios/me", headers=_cabecera_autorizacion())
    return (respuesta.get("data") or {}).get("email", "") if status_code == 200 else ""


def armar_resumen():
    compra = session.get(CLAVE_COMPRA) or {}
    if not compra.get("id_funcion") or not compra.get("butacas"):
        return None, "Primero elegí una función y tus butacas."

    funcion, error = _obtener_funcion(compra["id_funcion"])
    if error:
        return None, error
    fecha = _fecha_de_funcion(funcion)
    if fecha is None or fecha <= _ahora():
        return None, "Esta función ya comenzó. Elegí otra en la cartelera."

    servicios, aviso, error = _servicios_con_precio(compra.get("servicios") or [])
    if error:
        return None, error
    compra["servicios"] = [{"id_servicio": s["id_servicio"], "cantidad": s["cantidad"]} for s in servicios]
    session[CLAVE_COMPRA] = compra

    butacas = compra["butacas"]
    precio_entrada = float(funcion.get("precio_entrada") or 0)
    subtotal_entradas = precio_entrada * len(butacas)
    subtotal_servicios = sum(s["precio"] * s["cantidad"] for s in servicios)
    pelicula = funcion.get("pelicula") or {}
    sala = funcion.get("sala") or {}

    vista = {
        "funcion": {
            "pelicula": {"titulo": pelicula.get("titulo", ""), "poster_url": _obtener_poster(pelicula.get("id"))},
            "fecha": f"{DIAS[fecha.weekday()]}, {fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}",
            "horario": fecha.strftime("%H:%M"),
            "complejo": sala.get("local", ""),
            "sala": sala.get("nombre", ""),
            "butacas": _texto_butacas(butacas),
        },
        "cantidad_entradas": len(butacas),
        "precio_entrada": formatear_precio(precio_entrada),
        "subtotal_entradas": formatear_precio(subtotal_entradas),
        "servicios_seleccionados": [
            {"nombre": f"{s['nombre']} x{s['cantidad']}", "subtotal": formatear_precio(s["precio"] * s["cantidad"])}
            for s in servicios
        ],
        "subtotal_servicios": formatear_precio(subtotal_servicios),
        "total_compra": _numero_con_puntos(subtotal_entradas + subtotal_servicios),
    }
    return {"id_funcion": compra["id_funcion"], "butacas": butacas, "servicios": servicios,
            "aviso": aviso, "vista": vista}, None