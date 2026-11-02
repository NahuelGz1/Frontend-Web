# Frontend-Web

## Preparacion y pruebas

Con Python 3 instalado, ejecutar exclusivamente:

```sh
./init.sh
```

El script crea `.venv` e instala la version de Flask declarada en
[requirements.txt](requirements.txt), incluyendo Jinja2. No requiere claves
ni una API para las pruebas de la maqueta.

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Las pruebas renderizan el layout real con rutas publicas de prueba; verifican
datos, enlaces, recursos estaticos, escape HTML, funciones agotadas, lista vacia
y errores. No sustituyen pruebas de integracion con la API.

## Seleccion de funcion

Maqueta asociada a [NahuelGz1/Backend_Api#56](https://github.com/NahuelGz1/Backend_Api/issues/56).
La plantilla [seleccion_funcion.html](templates/cliente/seleccion_funcion.html)
hereda del layout publico y carga [compra.css](static/css/compra.css).
Adapta los colores, jerarquia y controles del
[frame de Figma 2028:1442](https://www.figma.com/design/0JZ8vvgSdcSphuL6PhLLJu/Mockup-proyecto?node-id=2028-1442),
sin incluir el mapa de butacas. El encabezado y pie compartidos se conservan.

### Contrato de renderizado

La vista debe proporcionar `funciones` (lista, incluso cuando este vacia) y
`error_funciones` (`None` o un mensaje seguro para el usuario, nunca una excepcion
de la API). Si hay error, se muestra el aviso en lugar de funciones anteriores.
Cada funcion contiene:

| Campo | Tipo / formato |
| --- | --- |
| `id` | Identificador unico de la funcion |
| `pelicula.titulo` | Texto |
| `fecha` | Fecha ISO `YYYY-MM-DD` |
| `horario` | Hora local del cine `HH:MM` |
| `sala.nombre` | Nombre completo, por ejemplo `Sala 1` |
| `disponible` | Booleano obtenido de la API interna |

Todos los textos se escapan con Jinja2. Las funciones sin disponibilidad no
ofrecen enlace de compra; una lista vacia muestra un aviso sin datos ficticios.

### Navegacion e integracion pendiente

Los enlaces usan `cliente.cartelera` y
`cliente.elegir_butacas(funcion_id=...)`. La seleccion navega mediante GET:
no crea reservas ni modifica disponibilidad. Los pasos posteriores se muestran
como indicadores, sin enlaces que permitan saltar la seleccion.

Este repositorio solo registra actualmente las rutas de administracion.
La integracion requiere implementar los Blueprints publicos y de autenticacion
que ya referencia el layout, ademas de la vista que obtenga las funciones desde
la API interna y renderice esta plantilla. La ruta de butacas debe validar el
identificador y consultar la disponibilidad en el servidor; ocultar un enlace
no es una validacion. La API confirma la disponibilidad al crear la reserva.
Esta maqueta no implementa reservas, pagos ni llamadas de red desde JavaScript.

## Mapa de asientos

[mapa_asientos.html](templates/cliente/mapa_asientos.html) implementa la siguiente
parte de [NahuelGz1/Backend_Api#56](https://github.com/NahuelGz1/Backend_Api/issues/56).
La plantilla anterior [elegir-butacas.html](templates/cliente/elegir-butacas.html)
hereda del mapa para mantener un unico punto de implementacion.

El plano reproduce la estructura del nodo `2043:563` del mismo frame de Figma:
pantalla superior, filas identificadas, butacas numeradas y leyenda. El ejemplo
del diseno tiene 8 filas de 10 butacas, pero la plantilla no fija la capacidad.
Las butacas libres son blancas; las ocupadas, grises y deshabilitadas; las
seleccionadas, bordo mediante `input:checked + label`. Un indicador de seleccion
y el tachado de las ocupadas complementan el color. No hay JavaScript de
seleccion, contadores desactualizados ni precios inventados.

### Datos del mapa

Ademas de `funcion` con el contrato anterior, la vista debe proporcionar:

| Variable | Contenido |
| --- | --- |
| `filas` | Lista ordenada de filas con `nombre` y una lista `butacas` |
| `butaca.id` | Identificador unico como cadena, apto para un atributo HTML `id` |
| `butaca.numero` | Numero visible dentro de la fila |
| `butaca.ocupada` | Booleano de disponibilidad obtenido de la API |
| `seleccionadas` | Lista de identificadores como cadenas; `[]` al iniciar |
| `csrf_token` | Token generado en servidor para el formulario |
| `error_mapa` | `None` o mensaje seguro; impide mostrar un mapa obsoleto |
| `error_seleccion` | `None` o mensaje de validacion; conserva las selecciones aun libres |

Una butaca ocupada nunca se marca, aunque aparezca en `seleccionadas`.
El plano vacio muestra un aviso y no ofrece formulario. Si todas las butacas
estan ocupadas, se muestra el plano y se deshabilita el boton de continuar.
Las salas anchas tienen desplazamiento horizontal dentro del plano, no en toda
la pagina; los checkboxes mantienen navegacion por teclado y foco visible.

### Contrato del POST pendiente de integrar

El formulario envia un POST nativo a
`cliente.elegir_butacas(funcion_id=funcion.id)`. La futura ruta Flask debe aceptar
GET y POST. En POST, leer `request.form.getlist("butacas")` y `csrf_token`.
Solo viajan los identificadores de las butacas marcadas y habilitadas; no se
envian precios, roles, disponibilidad ni totales confiados al navegador.

La ruta debe validar el token CSRF (el campo oculto por si solo no brinda
proteccion), exigir al menos una butaca, validar identificadores y pertenencia
a la funcion, y volver a consultar disponibilidad en la API. Debe mostrar los
errores con `error_seleccion` y preservar solo selecciones validas. No usar
`required` en cada checkbox: eso obligaria a seleccionar todas las butacas.
Luego de validar, avanzar a servicios/pago mediante una redireccion del servidor.
Los permisos, precios y la reserva definitiva siguen siendo responsabilidad de
la API interna. Esta entrega no agrega un endpoint de reservas simulado.

## Checkout: resumen y servicios opcionales

[checkout.html](templates/cliente/checkout.html) continua la tarea
[NahuelGz1/Backend_Api#56](https://github.com/NahuelGz1/Backend_Api/issues/56).
Adapta los paneles y el resumen de los frames de Figma
[Pagar PC](https://www.figma.com/design/0JZ8vvgSdcSphuL6PhLLJu/Mockup-proyecto?node-id=2024-2883)
y [Pagar Celular](https://www.figma.com/design/0JZ8vvgSdcSphuL6PhLLJu/Mockup-proyecto?node-id=2028-1617).
El resumen queda a la derecha en escritorio y debajo de los servicios en movil.
Se conserva el layout compartido. No se incluyen campos de tarjeta ni cobros.

### Contrato del checkout

La vista recibe `funcion` como en los pasos anteriores. Opcionalmente,
`funcion.pelicula.poster_url` puede indicar una imagen local o servida por el
frontend, validada por el servidor y sin claves de API; si no existe, se omite
el poster, sin usar una pelicula ficticia como reemplazo.

Debe proporcionar `resumen` con:

| Campo | Contenido |
| --- | --- |
| `butacas` | Lista validada de objetos con `fila` y `numero` |
| `subtotal_entradas` | Importe de entradas formateado con moneda |
| `servicios` | Lista de servicios ya incluidos: `nombre`, `cantidad`, `subtotal` |
| `subtotal_servicios` | Importe de servicios formateado con moneda |
| `total` | Total calculado por el servidor y formateado con moneda |

`servicios` (el catalogo, separado de `resumen.servicios`) es un diccionario con
las claves `combos`, `bebidas`, `estacionamiento` y `vip`. Cada clave contiene
una lista, incluso si esta vacia. Cada servicio tiene:

| Campo | Contenido |
| --- | --- |
| `id` | Cadena unica, apta para nombres de campos e identificadores HTML |
| `nombre` | Nombre visible |
| `precio_unitario` | Importe formateado con moneda, obtenido de la API |
| `cantidad` | Entero no negativo validado; cero al iniciar |
| `maximo` | Entero no negativo segun stock y reglas de la API |
| `disponible` | Booleano de disponibilidad |
| `error` | `None` o un mensaje seguro de validacion de este campo |

Combos y bebidas usan inputs numericos; estacionamiento y VIP usan selectores
con cantidades entre cero y el maximo indicado por la API. Se pueden combinar
varios productos de una misma categoria. Cero significa no agregar. Los
servicios no disponibles o con maximo cero se muestran deshabilitados y no se
envian. No se impone un limite inventado en el frontend.

La vista tambien recibe `csrf_token`, `error_checkout` y `error_formulario`.
Ambos errores son `None` o mensajes seguros: el primero impide mostrar datos
obsoletos y oculta el formulario; el segundo permite corregir la seleccion.
Una compra sin butacas tampoco ofrece formulario. Las categorias vacias tienen
un aviso y no impiden continuar solo con entradas.

### Recalculo y POST nativo

La ruta futura `cliente.checkout(funcion_id=...)` debe aceptar GET y POST.
El paso anterior debe redirigir a ella despues de validar las butacas. El POST
contiene `csrf_token`, campos `servicio_<id>` con cantidades enteras y
`accion=actualizar` o `accion=continuar`, segun el boton utilizado.
No se envian precios, total, pelicula ni asientos como valores confiables
del formulario: el servidor debe recuperar la seleccion validada del paso
anterior y verificar su pertenencia al usuario y a la funcion.

En cada POST, el servidor debe validar CSRF, accion, identificadores, cantidades,
limites y disponibilidad contra la API. Debe recalcular todo el resumen tanto
al actualizar como al continuar, conservando las cantidades validas y mostrando
errores explicitos cuando corresponda. Nunca debe cobrar el total mostrado sin
revalidarlo. `actualizar` vuelve a renderizar el checkout; `continuar` avanza al
paso de pago, sin ejecutar un cobro desde esta plantilla.

El resumen es una instantanea del ultimo calculo del servidor. Los controles no
lo modifican en el navegador; el aviso de la pantalla explica que se debe usar
**Actualizar resumen** tras cambiar cantidades. Las pruebas usan rutas y datos
de prueba, no una API ni una pasarela de pago simulada en produccion.

## Confirmacion de compra

[confirmacion.html](templates/cliente/confirmacion.html) adapta los frames
[Compra exitosa PC](https://www.figma.com/design/0JZ8vvgSdcSphuL6PhLLJu/Mockup-proyecto?node-id=2078-2306)
y [Compra exitosa Celular](https://www.figma.com/design/0JZ8vvgSdcSphuL6PhLLJu/Mockup-proyecto?node-id=2078-2676)
para la misma tarea [NahuelGz1/Backend_Api#56](https://github.com/NahuelGz1/Backend_Api/issues/56).
Incluye el resumen final, una tarjeta por entrada con su QR y el formulario de
cancelacion. No afirma que se enviaron correos ni ofrece descargas ficticias.
El encabezado y pie compartidos se conservan.

[compra-exitosa.html](templates/cliente/compra-exitosa.html) hereda de esta
plantilla. El desglose de entradas y servicios se comparte con el checkout en
[_resumen_compra.html](templates/cliente/_resumen_compra.html), sin recalcular
precios en Jinja2. La confirmacion lo presenta como **Total pagado**.

### Datos confirmados y entradas digitales

La vista recibe `funcion` y `resumen` con el contrato anterior, esta vez obtenidos
del pedido final confirmado, no del formulario del checkout. Tambien recibe
`reserva` (`None` si no pudo obtenerse), `csrf_token`, `error_confirmacion` y
`error_cancelacion`. Ambos errores son `None` o mensajes seguros para el usuario.

| Campo de `reserva` | Contenido |
| --- | --- |
| `id` | Identificador de la reserva |
| `codigo` | Referencia visible del pedido |
| `estado` | `confirmada` solo cuando la API confirma compra y pago aprobados |
| `entradas` | Lista de entradas individuales emitidas por la API |
| `cancelacion_permitida` | Booleano de autorizacion y plazo calculado por la API |
| `mensaje_cancelacion` | Explicacion de las condiciones/plazo o motivo de bloqueo, provista por el servidor |

Cada entrada contiene `fila`, `numero`, `codigo` y `qr_url`. La URL apunta a la
imagen QR generada por el servidor para esa entrada, servida por una ruta del
frontend autorizada para el propietario. No debe contener claves de API ni usar
generadores QR externos. El backend debe validar la URL, proteger el acceso a la
imagen y evitar que quede en caches compartidas. No guardar el QR completo en
la sesion Flask.

La pantalla nunca crea QR ni construye sus URLs a partir de identificadores.
Solo los muestra para una reserva `confirmada` sin error de consulta. Si falta
una imagen (`qr_url=None`) o la lista de entradas esta vacia, muestra un aviso
explicito, sin QR de muestra. Las reservas pendientes, rechazadas, desconocidas
o canceladas no muestran QR, mensaje de pago aprobado ni formulario de
cancelacion. El servidor debe validar la coherencia entre las entradas emitidas
y las butacas del resumen.

### Cancelacion mediante POST

El boton solo aparece si `reserva.cancelacion_permitida` es verdadero. Envia
POST a `cliente.cancelar_reserva(reserva_id=...)`, con `csrf_token` y
`accion=cancelar`. No se envian permisos, fechas limite, totales ni datos QR.
No se calcula un plazo fijo en HTML, CSS o JavaScript.

La ruta real sigue pendiente de integrar: debe aceptar solo POST, verificar
autenticacion, rol, propiedad de la reserva, CSRF y accion, y solicitar la
cancelacion a la API mediante el cliente server-side. La API debe revalidar el
plazo en ese momento; ocultar el boton no es control de acceso.

Tras la respuesta, el servidor debe volver a consultar el estado y redirigir a
la confirmacion. Solo un estado `cancelada` confirmado por la API permite
mostrar la cancelacion realizada y retirar las entradas. Si la operacion falla,
debe mostrar `error_cancelacion` y actualizar el permiso y su motivo. No
presuponer reembolsos, invalidacion del QR ni exito ante un error de red.