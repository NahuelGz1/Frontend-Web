from flask import Blueprint, render_template, redirect, url_for, flash, abort, current_app, request, make_response
from services.api_client import consumir_api
from services import compra_service
from routes.auth_security import requiere_sesion

cliente_views_bp = Blueprint("cliente_views", __name__)

@cliente_views_bp.route("/")
def inicio():
    status_code, respuesta = consumir_api("GET", "/peliculas/cartelera")
    
    peliculas = []
    if status_code == 200:
        peliculas = respuesta.get("data") or []

    # Normalizamos los nombres de campos que espera inicio.html
    for peli in peliculas:
        if not peli.get("afiche_url"):
            peli["afiche_url"] = peli.get("poster")
        if not peli.get("duracion_minutos"):
            peli["duracion_minutos"] = peli.get("duracion")

    # La primera pelicula como destacada, las demas para la grilla de hoy
    pelicula_destacada = peliculas[0] if peliculas else None
    peliculas_hoy = peliculas[1:] if len(peliculas) > 1 else peliculas
    return render_template(
        "cliente/inicio.html",
        pelicula_destacada=pelicula_destacada,
        peliculas_hoy=peliculas_hoy,
        proximos_estrenos=[]
)



@cliente_views_bp.route("/cartelera")
def cartelera():
    status_code, respuesta = consumir_api("GET", "/peliculas/cartelera")

    peliculas = []
    if status_code == 200:
        peliculas = respuesta.get("data") or []

    for pelicula in peliculas:
        if not pelicula.get("poster_url"):
            pelicula["poster_url"] = pelicula.get("poster")

    return render_template("cliente/cartelera.html", peliculas=peliculas)



# Si entran a la ruta vacia sin ID (con o sin barra al final), los mandamos a la cartelera
@cliente_views_bp.route("/pelicula")
@cliente_views_bp.route("/pelicula/")
def detalle_pelicula_vacia():
    return redirect(url_for("cliente_views.cartelera"))

# Las rutas que esperan si o si un ID de película
@cliente_views_bp.route("/pelicula/<int:id>")
@cliente_views_bp.route("/pelicula/<int:pelicula_id>")
def detalle_pelicula(id=None, pelicula_id=None):
    pelicula_id = pelicula_id or id
    status_code, respuesta = consumir_api("GET", f"/peliculas/{pelicula_id}")

    # Si no se encuentra (404) o hubo error en el backend
    if status_code != 200:
        mensaje_error = respuesta.get("error", {}).get("message", "Película no encontrada.")
        flash(mensaje_error, "danger")
        return redirect(url_for("cliente_views.cartelera"))

    pelicula = respuesta.get("data") or {}

    if not pelicula.get("poster_url"):
        pelicula["poster_url"] = pelicula.get("poster")

    return render_template("cliente/detalle-pelicula.html", pelicula=pelicula)




@cliente_views_bp.route("/seleccion-funcion")
def seleccion_funcion():
    return render_template("cliente/seleccion_funcion.html")

@cliente_views_bp.route("/mapa-asientos")
def mapa_asientos():
    return render_template("cliente/mapa_asientos.html")

def _pedir_inicio_de_sesion():
    flash("Iniciá sesión para comprar entradas.", "warning")
    return redirect(url_for("auth_views.iniciar_sesion"))


@cliente_views_bp.route("/elegir-butacas")
@cliente_views_bp.route("/elegir-butacas/<int:funcion_id>", methods=["GET", "POST"])
def elegir_butacas(funcion_id=None):
    if funcion_id is None:
        flash("Elegí una función para ver sus butacas.", "warning")
        return redirect(url_for("cliente_views.cartelera"))
    if not compra_service.hay_sesion_iniciada():
        return _pedir_inicio_de_sesion()

    datos = compra_service.datos_del_mapa(funcion_id)
    seleccionadas = compra_service.seleccion_previa(funcion_id)
    error_seleccion = None

    if request.method == "POST" and not datos["error_mapa"]:
        if not compra_service.csrf_valido(request.form.get("csrf_token")):
            error_seleccion = "El formulario venció. Volvé a elegir tus butacas."
        else:
            seleccionadas, error_seleccion = compra_service.validar_seleccion(
                request.form.getlist("butacas"), datos["filas"]
            )
            if not error_seleccion:
                compra_service.guardar_seleccion(funcion_id, seleccionadas)
                return redirect(url_for("cliente_views.servicios"))

    return render_template(
        "cliente/elegir-butacas.html",
        **datos,
        seleccionadas=seleccionadas,
        error_seleccion=error_seleccion,
        csrf_token=compra_service.token_csrf(),
    ), 400 if error_seleccion else 200



@cliente_views_bp.route("/servicios")
def servicios():
    status_code, respuesta = consumir_api("GET", "/servicios")
    
    lista_servicios = []
    if status_code == 200:
        lista_servicios = respuesta.get("data") or []

    for servicio in lista_servicios:
        nombre = servicio.get("nombre", "").lower()
        
        if not servicio.get("categoria"):
            if "pochoclo" in nombre or "combo" in nombre:
                servicio["categoria"] = "pochoclos"

            elif "agua" in nombre or "gaseosa" in nombre or "bebida" in nombre:
                servicio["categoria"] = "bebidas"

            elif "estacionamiento" in nombre or "vip" in nombre:
                servicio["categoria"] = "mejoras de experiencia"
                
            else:
                servicio["categoria"] = "snacks"

        if not servicio.get("precio_formateado") and "precio" in servicio:
            servicio["precio_formateado"] = f"${int(servicio['precio']):,}".replace(",", ".")

    contexto_compra = None
    resumen, error = compra_service.armar_resumen()
    if not error and resumen:
        vista_funcion = resumen["vista"]["funcion"]
        cant_entradas = resumen["vista"]["cantidad_entradas"]
        precio_ent = resumen["vista"].get("subtotal_entradas", "0")
        total_ent_int = int(''.join(filter(str.isdigit, str(precio_ent))) or 0)
        contexto_compra = {
            "cantidad_entradas": cant_entradas,
            "total_entradas": total_ent_int,
            "entrada": {
                "cantidad": cant_entradas,
                "pelicula": vista_funcion["pelicula"].get("titulo", ""),
                "fecha": vista_funcion.get("fecha", ""),
                "sala": f"{vista_funcion.get('complejo', '')} - {vista_funcion.get('sala', '')}",
                "asientos": vista_funcion.get("butacas", ""),
            }
        }

    return render_template(
        "cliente/servicios.html",
        servicios=lista_servicios,
        contexto_compra=contexto_compra,
    )


@cliente_views_bp.route("/servicios/guardar", methods=["POST"])
def guardar_servicios():
    if not compra_service.hay_sesion_iniciada():
        return {"error": "No autorizado"}, 401

    datos = request.get_json(silent=True) or {}
    servicios_lista = datos.get("servicios", [])

    from flask import session
    compra = session.get(compra_service.CLAVE_COMPRA) or {}
    compra["servicios"] = servicios_lista
    session[compra_service.CLAVE_COMPRA] = compra

    return {"status": "ok", "redirect": url_for("cliente_views.pagar")}


@cliente_views_bp.route("/mi-perfil")
@requiere_sesion
def mi_perfil():
    status_code, respuesta = consumir_api("GET", "/auth/usuarios/me/perfil-completo")
    datos_perfil = respuesta.get("data")
    if status_code != 200 or not isinstance(datos_perfil, dict):
        current_app.logger.error("No se pudo obtener el perfil completo de la API")
        abort(503, description="No se pudo cargar tu perfil. Intentá más tarde.")
    return render_template("cliente/mi-perfil.html", **datos_perfil)


@cliente_views_bp.route("/pagar", methods=["GET", "POST"])
def pagar():
    if not compra_service.hay_sesion_iniciada():
        return _pedir_inicio_de_sesion()

    resumen, error = compra_service.armar_resumen()
    if error:
        flash(error, "warning")
        funcion_id = compra_service.funcion_en_curso()
        if funcion_id:
            return redirect(url_for("cliente_views.elegir_butacas", funcion_id=funcion_id))
        return redirect(url_for("cliente_views.cartelera"))
    if resumen["aviso"]:
        flash(resumen["aviso"], "warning")

    if request.method == "POST":
        if not compra_service.csrf_valido(request.form.get("csrf_token")):
            flash("El formulario venció. Revisá el resumen y confirmá de nuevo.", "warning")
            return redirect(url_for("cliente_views.pagar"))
        if not compra_service.guardar_email_contacto(request.form.get("email")):
            flash("Ingresá un email de contacto válido.", "warning")
            return redirect(url_for("cliente_views.pagar"))
        exito, mensaje, elegir_de_nuevo = compra_service.confirmar_compra(resumen)
        if exito:
            return redirect(url_for("cliente_views.compra_exitosa", compra_id=compra_service.id_compra_confirmada()))
        flash(mensaje, "danger")
        if elegir_de_nuevo:
            return redirect(url_for("cliente_views.elegir_butacas", funcion_id=resumen["id_funcion"]))
        return redirect(url_for("cliente_views.pagar"))

    return render_template(
        "cliente/pagar.html",
        **resumen["vista"],
        email_usuario=compra_service.email_de_contacto(),
        csrf_token=compra_service.token_csrf(),
    )

@cliente_views_bp.route("/compra-exitosa")
@cliente_views_bp.route("/compra-exitosa/")
def compra_exitosa_vacia():
    return redirect(url_for("cliente_views.cartelera"))

@cliente_views_bp.route("/compra-exitosa/<int:compra_id>")
def compra_exitosa(compra_id):
    status_code, respuesta = consumir_api("GET", f"/compras/{compra_id}")
    
    if status_code != 200:
        mensaje_error = respuesta.get("error", {}).get("message", "Compra no encontrada.")
        flash(mensaje_error, "danger")
        return redirect(url_for("cliente_views.cartelera"))
    
    datos = respuesta.get("data") or {}
    reserva = datos.get("reserva") or {}
    entradas = reserva.get("entradas") or datos.get("entradas") or []

    for entrada in entradas:
        if entrada.get("qr_imagen_base64"):
            entrada["qr_url"] = f"data:image/png;base64,{entrada['qr_imagen_base64']}"

    reserva["entradas"] = entradas

    return render_template("cliente/compra-exitosa.html", 
                            funcion = datos.get("funcion", {}), 
                            reserva = reserva,
                            resumen = datos.get("resumen", {}))


def _obtener_compra_para_documento(compra_id):
    status_code, respuesta = consumir_api("GET", f"/compras/{compra_id}")
    if status_code != 200:
        mensaje = respuesta.get("error", {}).get("message", "Compra no encontrada.")
        flash(mensaje, "danger")
        return None
    return respuesta.get("data") or {}


@cliente_views_bp.route("/compras/<int:compra_id>/entradas")
@requiere_sesion
def descargar_entradas(compra_id):
    datos = _obtener_compra_para_documento(compra_id)
    if datos is None:
        return redirect(url_for("cliente_views.mi_perfil"))
    respuesta = make_response(render_template("cliente/entradas.html", **datos))
    respuesta.headers["Content-Disposition"] = f"attachment; filename=entradas-CP-{compra_id}.html"
    return respuesta


@cliente_views_bp.route("/compras/<int:compra_id>/factura")
@requiere_sesion
def descargar_factura(compra_id):
    datos = _obtener_compra_para_documento(compra_id)
    if datos is None:
        return redirect(url_for("cliente_views.mi_perfil"))
    respuesta = make_response(render_template("cliente/factura.html", **datos))
    respuesta.headers["Content-Disposition"] = f"attachment; filename=factura-CP-{compra_id}.html"
    return respuesta

@cliente_views_bp.route("/cancelar-compra")
@cliente_views_bp.route("/cancelar-compra/")
def cancelar_compra_vacia():
    return redirect(url_for("cliente_views.cartelera"))

@cliente_views_bp.route("/cancelar-compra/<int:compra_id>")
@requiere_sesion
def cancelar_compra(compra_id):
    status_code, respuesta = consumir_api("GET", f"/compras/{compra_id}")

    if status_code != 200:
        mensaje_error = respuesta.get("error", {}).get("message", "Compra no encontrada.")
        flash(mensaje_error, "danger")
        return redirect(url_for("cliente_views.cartelera"))

    datos = respuesta.get("data") or {}

    return render_template("cliente/cancelar-compra.html",
                            funcion=datos.get("funcion", {}),
                            reserva=datos.get("reserva", {}),
                            resumen=datos.get("resumen", {}),
                            csrf_token=compra_service.token_csrf())

@cliente_views_bp.route("/reservas/<int:reserva_id>/cancelar", methods = ["POST"])
@requiere_sesion
def cancelar_reserva(reserva_id):
    if not compra_service.csrf_valido(request.form.get("csrf_token")):
        flash("El formulario venció. Volvé a intentar la cancelación.", "warning")
        return redirect(url_for("cliente_views.mi_perfil"))
    status_code, respuesta = consumir_api("PUT", f"/compras/{reserva_id}/cancelar")
    
    if status_code == 200:
        flash(respuesta.get("message", "Reserva cancelada exitosamente"), "success")
    else:
        mensaje_error = respuesta.get("error", {}).get("message", "Compra no encontrada.")
        flash(mensaje_error, "danger")

    return redirect(url_for("cliente_views.mi_perfil"))



@cliente_views_bp.route("/estrenos")
def estrenos():
    status_code, respuesta = consumir_api("GET", "/peliculas/estrenos")

    estrenos_lista = []
    if status_code == 200:
        estrenos_lista = respuesta.get("data") or []

    for pelicula in estrenos_lista:
        if not pelicula.get("poster_url"):
            pelicula["poster_url"] = pelicula.get("poster")

    return render_template("cliente/estrenos.html", peliculas=estrenos_lista)


@cliente_views_bp.route("/mi-perfil/editar", methods=["POST"])
@requiere_sesion
def editar_perfil():
    nombre_input = request.form.get("nombre", "").strip()
    apellido_input = request.form.get("apellido", "").strip()
    email_input = request.form.get("email", "").strip()

    # Validar la regla de Nombre + Apellido
    if (nombre_input and not apellido_input) or (apellido_input and not nombre_input):
        flash("Si querés modificar tu nombre, tenés que ingresar tanto el nombre como el apellido.", "warning")
        return redirect(url_for("cliente_views.mi_perfil"))

    datos = {}

    # Si completó Nombre y Apellido, los unificamos
    if nombre_input and apellido_input:
        datos["nombre"] = f"{nombre_input} {apellido_input}"

    # Si completó Email, lo agregamos
    if email_input:
        datos["email"] = email_input

    # Si envió el formulario totalmente vacío
    if not datos:
        flash("No ingresaste ningún dato para modificar.", "info")
        return redirect(url_for("cliente_views.mi_perfil"))

    status_code, respuesta = consumir_api("PATCH", "/auth/usuarios/me", datos=datos)

    if status_code == 200:
        flash("Perfil actualizado correctamente.", "success")
    else:
        mensaje_error = respuesta.get("error", {}).get("message") or "No se pudo actualizar el perfil."
        flash(mensaje_error, "danger")

    return redirect(url_for("cliente_views.mi_perfil"))