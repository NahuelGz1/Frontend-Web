# Lo que el cliente va eligiendo queda en session["compra"]: id_funcion, butacas y servicios
# Despues de comprar, session["compra_confirmada"] tiene lo que muestra compra-exitosa.html
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app, session

from services.api_client import consumir_api
from utils.butacas import (
    etiquetas_butacas,
    texto_butacas,
    ubicacion_butaca,
)

MAXIMO_BUTACAS_POR_COMPRA = 10
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
    return {"Authorization": "Bearer " + session.get(CLAVE_TOKEN, "")}

def _numero_con_puntos(monto):
    return f"{monto:,.0f}".replace(",", ".")


def formatear_precio(monto):
    return f"${_numero_con_puntos(monto)}"


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
        return None, "La función que elegiste no existe o ya no está disponible. Elegí otra en la cartelera."
    return None, _mensaje_de_error(status_code, respuesta, ERROR_GENERICO)


def _obtener_poster(pelicula_id):
    status_code, respuesta = consumir_api("GET", f"/peliculas/{pelicula_id}")
    if status_code != 200:
        return ""
    pelicula = respuesta.get("data") or {}
    return pelicula.get("poster_url") or pelicula.get("poster") or ""


def disponibilidad_estacionamiento(funcion_id):
    status_code, respuesta = consumir_api("GET", f"/funciones/{funcion_id}/estacionamiento")
    if status_code != 200:
        current_app.logger.warning("No se pudo consultar el estacionamiento de la función %s (HTTP %s)",
                                   funcion_id, status_code)
        return None, "No pudimos consultar la disponibilidad de estacionamiento. Intentá nuevamente."
    datos = respuesta.get("data")
    disponibles = datos.get("disponibles") if isinstance(datos, dict) else None
    if type(disponibles) is not int or not 0 <= disponibles <= 20:
        current_app.logger.error("Respuesta inválida de disponibilidad de estacionamiento para la función %s",
                                 funcion_id)
        return None, "No pudimos consultar la disponibilidad de estacionamiento. Intentá nuevamente."
    return disponibles, None


def _servicios_con_precio(elegidos, cantidad_entradas, funcion_id):
    if not elegidos:
        return [], None, None
    status_code, respuesta = consumir_api("GET", "/servicios")
    if status_code != 200:
        return None, None, "No pudimos cargar los servicios adicionales. Intentá de nuevo."
    catalogo = {servicio["id"]: servicio for servicio in respuesta.get("data") or []}
    hay_estacionamiento = any(
        "estacionamiento" in (catalogo.get(elegido.get("id_servicio")) or {}).get("nombre", "").lower()
        for elegido in elegidos
    )
    limite_estacionamiento = 0
    if hay_estacionamiento:
        disponibles, error = disponibilidad_estacionamiento(funcion_id)
        if error:
            return None, None, error
        limite_estacionamiento = min(cantidad_entradas, disponibles)
    servicios = []
    ajuste_estacionamiento = False
    for elegido in elegidos:
        servicio = catalogo.get(elegido.get("id_servicio"))
        cantidad = elegido.get("cantidad")
        if servicio and isinstance(cantidad, int) and cantidad > 0:
            nombre_normalizado = servicio.get("nombre", "").lower()

            if "estacionamiento" in nombre_normalizado:
                cantidad_original = cantidad
                cantidad = min(cantidad, limite_estacionamiento)
                limite_estacionamiento -= cantidad
                ajuste_estacionamiento |= cantidad != cantidad_original
            elif "vip" in nombre_normalizado:
                cantidad = min(cantidad, cantidad_entradas)

            if cantidad > 0:
                servicios.append({
                    "id_servicio": servicio["id"],
                    "nombre": servicio["nombre"],
                    "cantidad": cantidad,
                    "precio": float(servicio["precio"])
                })
    aviso = None
    if ajuste_estacionamiento:
        aviso = "La disponibilidad de estacionamiento cambió. Revisá las cantidades y el total antes de confirmar."
    elif len(servicios) < len(elegidos):
        aviso = "Algún servicio que elegiste ya no está disponible y lo quitamos del resumen."
    return servicios, aviso, None

def armar_filas(butacas):
    filas = []
    for butaca in sorted(butacas, key=lambda b: b["numero_butaca"]):
        numero_butaca = butaca["numero_butaca"]
        nombre, numero = ubicacion_butaca(numero_butaca)
        if not filas or filas[-1]["nombre"] != nombre:
            filas.append({"nombre": nombre, "butacas": []})
        filas[-1]["butacas"].append({
            "id": numero_butaca,
            "numero": numero,
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
    if funcion.get("estado") == "agotada":
        return {**vacio, "error_mapa": "Esta función está agotada, no quedan butacas libres. Elegí otro horario."}

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
        etiquetas = etiquetas_butacas(ocupadas)
        return siguen_libres, f"Estas butacas ya están ocupadas: {etiquetas}. Elegí otras."
    return sorted(elegidas), None


def guardar_seleccion(funcion_id, butacas):
    anterior = session.get(CLAVE_COMPRA) or {}
    session[CLAVE_COMPRA] = {"id_funcion": funcion_id, "butacas": butacas,
                             "servicios": anterior.get("servicios", [])}


def seleccion_previa(funcion_id):
    compra = session.get(CLAVE_COMPRA) or {}
    return compra.get("butacas", []) if compra.get("id_funcion") == funcion_id else []


def servicios_seleccionados():
    return {
        s["id_servicio"]: s["cantidad"]
        for s in (session.get(CLAVE_COMPRA) or {}).get("servicios", [])
    }


def guardar_servicios(formulario):
    compra = session.get(CLAVE_COMPRA) or {}
    tiene_compra_nueva = bool(compra.get("id_funcion") and compra.get("butacas"))
    id_compra_adjunta = compra.get("id_compra_adjunta")

    entrada_adjunta = None
    if id_compra_adjunta:
        entrada_adjunta = next(
            (e for e in obtener_entradas_disponibles_usuario() if e["id_compra"] == id_compra_adjunta),
            None,
        )
        if not entrada_adjunta:
            limpiar_seleccion_entrada()
            return "La entrada seleccionada ya no está disponible. Elegí otra o continuá sin entrada."

    elegidos = []
    for campo in formulario:
        if not campo.startswith("cantidad_"):
            continue
        identificador = campo.removeprefix("cantidad_")
        valores = formulario.getlist(campo)
        if (not identificador.isascii() or not identificador.isdigit()
                or len(valores) != 1 or not re.fullmatch(r"[0-9]{1,4}", valores[0])):
            return "Ingresá cantidades enteras entre 0 y 9999."
        cantidad = int(valores[0])
        if cantidad:
            elegidos.append({"id_servicio": int(identificador), "cantidad": cantidad})

    if not tiene_compra_nueva and not elegidos:
        return "Elegí al menos un servicio para continuar al pago."

    if elegidos:
        codigo, respuesta = consumir_api("GET", "/servicios")
        if codigo != 200:
            return "No pudimos validar los servicios. Intentá nuevamente."
        catalogo = {s["id"]: s for s in respuesta.get("data") or []}

        if tiene_compra_nueva:
            max_est = len(compra["butacas"])
            max_vip = len(compra["butacas"])
            id_funcion_check = compra["id_funcion"]
        elif entrada_adjunta:
            max_est = max(0, entrada_adjunta["cantidad_entradas"] - entrada_adjunta["estacionamiento_previo"])
            max_vip = max(0, entrada_adjunta["cantidad_entradas"] - entrada_adjunta["vip_previo"])
            id_funcion_check = entrada_adjunta["id_funcion"]
        else:
            max_est = 0
            max_vip = 0
            id_funcion_check = None

        cantidad_estacionamiento = 0
        ids_elegidos = set()
        for elegido in elegidos:
            servicio = catalogo.get(elegido["id_servicio"])
            if not servicio or not servicio.get("activo", True):
                return "Algún servicio ya no está disponible. Revisá tu selección."
            if elegido["id_servicio"] in ids_elegidos:
                return "Hay servicios repetidos. Revisá tu selección."
            ids_elegidos.add(elegido["id_servicio"])
            nombre = servicio["nombre"].lower()
            if "estacionamiento" in nombre:
                if not id_funcion_check:
                    return "Estacionamiento requiere una entrada asociada."
                if elegido["cantidad"] > max_est:
                    return f"Podés agregar como máximo {max_est} estacionamiento(s) a esta entrada."
                cantidad_estacionamiento += elegido["cantidad"]
            elif "vip" in nombre:
                if not id_funcion_check:
                    return "Acceso VIP requiere una entrada asociada."
                if elegido["cantidad"] > max_vip:
                    return f"Podés agregar como máximo {max_vip} acceso(s) VIP a esta entrada."

        if cantidad_estacionamiento and id_funcion_check:
            disponibles, error = disponibilidad_estacionamiento(id_funcion_check)
            if error:
                return error
            if cantidad_estacionamiento > disponibles:
                return f"No hay suficientes espacios de estacionamiento disponibles para esta función. Quedan {disponibles} lugares."

    compra["servicios"] = elegidos
    session[CLAVE_COMPRA] = compra
    return None

def funcion_en_curso():
    return (session.get(CLAVE_COMPRA) or {}).get("id_funcion")


def email_del_usuario():
    usuario = session.get("usuario") or {}
    if usuario.get("email"):
        return usuario["email"]
    status_code, respuesta = consumir_api("GET", "/auth/usuarios/me", headers=_cabecera_autorizacion())
    return (respuesta.get("data") or {}).get("email", "") if status_code == 200 else ""


def email_de_contacto():
    compra = session.get(CLAVE_COMPRA) or {}
    return compra.get("email_contacto") or email_del_usuario()


def guardar_email_contacto(email):
    email = (email or "").strip().lower()
    if len(email) > 100 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False
    compra = session.get(CLAVE_COMPRA) or {}
    compra["email_contacto"] = email
    session[CLAVE_COMPRA] = compra
    return True


def armar_resumen(incluir_servicios=True):
    compra = session.get(CLAVE_COMPRA) or {}
    id_compra_adjunta = compra.get("id_compra_adjunta")

    # MODO 2: Servicios adjuntos a una entrada ya comprada
    if id_compra_adjunta:
        entrada = next(
            (e for e in obtener_entradas_disponibles_usuario() if e["id_compra"] == id_compra_adjunta),
            None,
        )
        if not entrada:
            limpiar_seleccion_entrada()
            return None, "La entrada seleccionada ya no está disponible."

        max_est = max(0, entrada["cantidad_entradas"] - entrada["estacionamiento_previo"])
        servicios, aviso, error = [], None, None
        if incluir_servicios:
            servicios, aviso, error = _servicios_con_precio(
                compra.get("servicios") or [], max_est, entrada["id_funcion"]
            )
            if error:
                return None, error
            if not servicios:
                return None, "Elegí al menos un servicio para adjuntar a tu entrada."
            compra["servicios"] = [{"id_servicio": s["id_servicio"], "cantidad": s["cantidad"]} for s in servicios]
            session[CLAVE_COMPRA] = compra

        subtotal_servicios = sum(s["precio"] * s["cantidad"] for s in servicios)
        vista = {
            "funcion": {
                "pelicula": entrada["pelicula"],
                "fecha": entrada["fecha"],
                "horario": entrada["horario"],
                "complejo": entrada["complejo"],
                "sala": entrada["sala"],
                "butacas": f"Butacas: {entrada['butacas']}",
            },
            "cantidad_entradas": entrada["cantidad_entradas"],
            "precio_entrada": "$0",
            "subtotal_entradas": "$0 (ya abonadas)",
            "servicios_seleccionados": [
                {"nombre": f"{s['nombre']} x{s['cantidad']}", "subtotal": formatear_precio(s["precio"] * s["cantidad"])}
                for s in servicios
            ],
            "subtotal_servicios": formatear_precio(subtotal_servicios),
            "total_compra": _numero_con_puntos(subtotal_servicios),
            "resumen": {"modo": "compra_existente", "codigo_operacion": entrada["codigo_operacion"]},
        }
        return {
            "modo": "compra_existente",
            "id_compra_adjunta": id_compra_adjunta,
            "id_funcion": entrada["id_funcion"],
            "butacas": [],
            "servicios": servicios,
            "aviso": aviso,
            "vista": vista,
        }, None

    # MODO 3: Compra de servicios solos (sin función ni entrada adjunta)
    if not compra.get("id_funcion") or not compra.get("butacas"):
        if not incluir_servicios or not compra.get("servicios"):
            return None, "Primero elegí una función, una entrada disponible o algún servicio."
        servicios, aviso, error = _servicios_con_precio(compra.get("servicios") or [], 0, None)
        if error:
            return None, error
        if not servicios:
            return None, "Elegí al menos un servicio para continuar."
        compra["servicios"] = [{"id_servicio": s["id_servicio"], "cantidad": s["cantidad"]} for s in servicios]
        session[CLAVE_COMPRA] = compra
        subtotal_servicios = sum(s["precio"] * s["cantidad"] for s in servicios)
        vista = {
            "funcion": {"pelicula": {"titulo": "Compra solo servicios", "poster_url": ""}},
            "cantidad_entradas": 0,
            "precio_entrada": "$0",
            "subtotal_entradas": "$0",
            "servicios_seleccionados": [
                {"nombre": f"{s['nombre']} x{s['cantidad']}", "subtotal": formatear_precio(s["precio"] * s["cantidad"])}
                for s in servicios
            ],
            "subtotal_servicios": formatear_precio(subtotal_servicios),
            "total_compra": _numero_con_puntos(subtotal_servicios),
            "resumen": {"modo": "solo_servicios"},
        }
        return {
            "modo": "solo_servicios",
            "id_compra_adjunta": None,
            "id_funcion": None,
            "butacas": [],
            "servicios": servicios,
            "aviso": aviso,
            "vista": vista,
        }, None

    # MODO 1: Compra nueva con entrada en curso
    funcion, error = _obtener_funcion(compra["id_funcion"])
    if error:
        return None, error
    fecha = _fecha_de_funcion(funcion)
    if fecha is None or fecha <= _ahora():
        return None, "Esta función ya comenzó. Elegí otra en la cartelera."

    butacas = compra["butacas"]

    servicios, aviso = [], None
    if incluir_servicios:
        servicios, aviso, error = _servicios_con_precio(
            compra.get("servicios") or [], len(butacas), compra["id_funcion"]
        )
        if error:
            return None, error
        compra["servicios"] = [{"id_servicio": s["id_servicio"], "cantidad": s["cantidad"]} for s in servicios]
        session[CLAVE_COMPRA] = compra

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
            "butacas": texto_butacas(butacas),
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
        "resumen": {"modo": "nueva_entrada"},
    }
    return {
        "modo": "nueva_entrada",
        "id_compra_adjunta": None,
        "id_funcion": compra["id_funcion"],
        "butacas": butacas,
        "servicios": servicios,
        "aviso": aviso,
        "vista": vista,
    }, None

def _datos_compra_exitosa(vista, compra_api):
    entradas = []
    for entrada in compra_api.get("entradas") or []:
        fila, numero = ubicacion_butaca(entrada["numero_butaca"])
        entradas.append({
            "fila": fila,
            "numero": numero,
            "codigo": entrada.get("codigo_qr_texto", ""),
            "qr_url": f"data:image/png;base64,{entrada['qr_imagen_base64']}" if entrada.get("qr_imagen_base64") else "",
        })
    return {
        "funcion": vista["funcion"],
        "resumen": {
            "subtotal_entradas": vista["subtotal_entradas"],
            "servicios": vista["servicios_seleccionados"],
            "subtotal_servicios": vista["subtotal_servicios"],
            "total": f"${vista['total_compra']} ARS",
        },
        "reserva": {"id_compra": compra_api.get("id_compra"),
                    "codigo": f"CP-{compra_api.get('id_compra')}", "entradas": entradas},
    }


def confirmar_compra(resumen):
    servicios_payload = [
        {"id_servicio": s["id_servicio"], "cantidad": s["cantidad"], "precio": s["precio"]}
        for s in resumen["servicios"]
    ]
    id_compra_adjunta = resumen.get("id_compra_adjunta")

    if id_compra_adjunta:
        status_code, respuesta = consumir_api(
            "POST",
            f"/compras/{id_compra_adjunta}/servicios",
            datos={"servicios": servicios_payload, "email_contacto": email_de_contacto()},
            headers=_cabecera_autorizacion(),
        )
    else:
        cuerpo = {
            "id_funcion": resumen["id_funcion"],
            "butacas": resumen["butacas"],
            "servicios": servicios_payload,
            "email_contacto": email_de_contacto(),
        }
        status_code, respuesta = consumir_api("POST", "/compras", datos=cuerpo, headers=_cabecera_autorizacion())

    if not 200 <= status_code < 300:
        mensaje = _mensaje_de_error(status_code, respuesta, "No pudimos confirmar la compra. Intentá de nuevo en unos minutos.")
        if status_code in (400, 409) and (
            "estacionamiento" in mensaje.lower() or "servicio" in mensaje.lower() or "vip" in mensaje.lower()
        ):
            return False, mensaje, "servicios"
        return False, mensaje, "butacas" if (resumen.get("butacas") and 400 <= status_code < 500 and status_code != 401) else None

    session[CLAVE_COMPRA_CONFIRMADA] = _datos_compra_exitosa(resumen["vista"], respuesta.get("data") or {})
    session.pop(CLAVE_COMPRA, None)
    return True, None, False


def id_compra_confirmada():
    return ((session.get(CLAVE_COMPRA_CONFIRMADA) or {}).get("reserva") or {}).get("id_compra")


def datos_confirmacion(datos):
    funcion = datos["funcion"]
    fecha = datetime.fromisoformat(funcion["fecha_hora_proyeccion"])
    reserva = datos["reserva"]
    entradas = []
    for entrada in reserva["entradas"]:
        fila, numero = ubicacion_butaca(entrada["numero_butaca"])
        entradas.append({
            **entrada, "fila": fila, "numero": numero, "codigo": entrada["codigo_qr"],
            "qr_url": f"data:image/png;base64,{entrada['qr_imagen_base64']}",
        })
    qr_64 = datos.get("qr_imagen_base64") or reserva.get("qr_imagen_base64")
    qr_url_compra = f"data:image/png;base64,{qr_64}" if qr_64 else (entradas[0]["qr_url"] if entradas else "")
    resumen = datos["resumen"]
    subtotal_entradas = float(resumen["subtotal_entradas"])
    subtotal_servicios = float(resumen["subtotal_servicios"])
    return {
        "qr_url": qr_url_compra,
        "codigo_qr": reserva.get("codigo_qr") or (entradas[0]["codigo"] if entradas else ""),
        "funcion": {
            **funcion, "fecha": fecha.strftime("%d/%m/%Y"), "horario": fecha.strftime("%H:%M"),
            "complejo": funcion["sala"]["local"],
            "butacas": texto_butacas([e["numero_butaca"] for e in reserva["entradas"]]),
        },
        "reserva": {**reserva, "entradas": entradas},
        "resumen": {
            "cantidad_entradas": len(entradas),
            "subtotal_entradas": formatear_precio(subtotal_entradas),
            "subtotal_servicios": formatear_precio(subtotal_servicios),
            "total": formatear_precio(subtotal_entradas + subtotal_servicios) + " ARS",
            "servicios": [
                {"nombre": f"{s['nombre']} x{s['cantidad']}",
                 "subtotal": formatear_precio(float(s["precio"]) * s["cantidad"])}
                for s in resumen["servicios"]
            ],
        },
    }

def preparar_datos_documento(datos):
    if not datos:
        return {}
    reserva = datos.get("reserva") or {}
    entradas_raw = reserva.get("entradas") or []
    butacas_nums = []
    entradas_formateadas = []
    qr_imagen = datos.get("qr_imagen_base64") or reserva.get("qr_imagen_base64")

    for e in entradas_raw:
        num = e.get("numero_butaca") or e.get("numero")
        if num is not None:
            try:
                num_int =int(num)
                butacas_nums.append(num_int)
                fila, col = ubicacion_butaca(num_int)
                codigo_butaca = f"{fila}{col}"
            except (ValueError, TypeError):
                fila, col, codigo_butaca = "", num, str(num)
        else:
            fila, col, codigo_butaca = "", "", ""

        if not qr_imagen and e.get("qr_imagen_base64"):
            qr_imagen = e.get("qr_imagen_base64")
        entradas_formateadas.append({
            **e,
            "fila": fila,
            "numero": col,
            "codigo_butaca": codigo_butaca,
        })
    butacas_texto = reserva.get("butacas_texto") or texto_butacas(butacas_nums)
    butacas_listado = re.sub(r"^Butacas?:?\s+", "", butacas_texto, flags=re.IGNORECASE)
    codigo_qr = datos.get("compra", {}).get("codigo_qr") or reserva.get("codigo_qr") or (entradas_raw[0].get("codigo_qr") if entradas_raw else "")
    return {
        **datos,
        "qr_imagen_base64": qr_imagen,
        "butacas_texto": butacas_texto,
        "butacas_listado": butacas_listado,
        "codigo_qr": codigo_qr,
        "reserva": {
            **reserva,
            "qr_imagen_base64": qr_imagen,
            "butacas_texto": butacas_texto,
            "codigo_qr": codigo_qr,
            "entradas": entradas_formateadas,
        },
    }


def obtener_entradas_disponibles_usuario():
    if not hay_sesion_iniciada():
        return []
    status_code, respuesta = consumir_api(
        "GET", "/auth/usuarios/me/perfil-completo", headers=_cabecera_autorizacion()
    )
    if status_code != 200 or not isinstance(respuesta.get("data"), dict):
        return []

    proximas = respuesta["data"].get("entradas_proximas") or []
    resultado = []
    for ent in proximas:
        if not ent.get("id_compra"):
            continue
        numeros = [int(n) for n in ent.get("numeros_butacas") or []]
        butacas_txt = ent.get("butacas") or (etiquetas_butacas(numeros) if numeros else "")
        cant_entradas = int(ent.get("cantidad_entradas") or len(numeros) or 1)
        servicios_previos = ent.get("servicios") or []
        est_previo = sum(
            int(s.get("cantidad") or 1) for s in servicios_previos
            if "estacionamiento" in str(s.get("nombre", "")).lower()
        )
        vip_previo = sum(
            int(s.get("cantidad") or 1) for s in servicios_previos
            if "vip" in str(s.get("nombre", "")).lower()
        )
        resultado.append({
            "id_compra": int(ent["id_compra"]),
            "id_funcion": ent.get("id_funcion"),
            "codigo_operacion": ent.get("codigo_operacion") or f"CP-{ent['id_compra']}",
            "pelicula": ent.get("pelicula") or {"titulo": "", "poster_url": ""},
            "fecha": ent.get("fecha", ""),
            "horario": ent.get("horario", ""),
            "complejo": ent.get("complejo", ""),
            "sala": ent.get("sala", ""),
            "butacas": butacas_txt,
            "cantidad_entradas": cant_entradas,
            "estacionamiento_previo": est_previo,
            "vip_previo": vip_previo,
        })
    return resultado


def compra_adjunta_en_curso():
    return (session.get(CLAVE_COMPRA) or {}).get("id_compra_adjunta")


def seleccionar_compra_adjunta(compra_id):
    anterior = session.get(CLAVE_COMPRA) or {}
    session[CLAVE_COMPRA] = {
        "id_compra_adjunta": int(compra_id),
        "servicios": anterior.get("servicios", []),
        "email_contacto": anterior.get("email_contacto"),
    }


def limpiar_seleccion_entrada():
    anterior = session.get(CLAVE_COMPRA) or {}
    session[CLAVE_COMPRA] = {
        "servicios": anterior.get("servicios", []),
        "email_contacto": anterior.get("email_contacto"),
    }