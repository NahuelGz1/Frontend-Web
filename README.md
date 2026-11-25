# Cine Paradiso — Frontend Web

Interfaz web de **Cine Paradiso**, desarrollada con **Python, Flask, plantillas HTML (Jinja2), CSS y JavaScript**. Permite a los clientes consultar la cartelera y los próximos estrenos, seleccionar funciones y butacas, comprar entradas y servicios adicionales, asociar servicios a compras existentes, descargar entradas y facturas en PDF, consultar su perfil y puntuar películas. Incluye vistas administrativas para gestionar películas, salas, funciones, servicios y permisos de usuarios, consultar estadísticas, exportar reportes y validar códigos QR. También dispone de un panel para empleados destinado a la validación de entradas y servicios.

> Este repositorio contiene la **aplicación web (frontend)**. La API REST y el acceso a MySQL están en el repositorio [Backend_Api](https://github.com/NahuelGz1/Backend_Api). La comunicación con la API se realiza desde el servidor Flask mediante `requests`; el navegador no necesita conectarse directamente a MySQL.

## Tecnologías

- **Python 3 y Flask 3.1.2:** servidor web, rutas y plantillas.
- **Jinja2, HTML, CSS y JavaScript:** presentación e interacciones.
- **Requests:** peticiones HTTP a `Backend_Api`.
- **Flask-Session y Cachelib:** sesiones del lado del servidor.
- **python-dotenv:** carga de variables de entorno desde `.env`.
- **Gunicorn:** ejecución mediante WSGI en contenedores.
- **WeasyPrint 70.0:** generación de entradas con códigos QR y facturas en formato PDF.

Las dependencias se enumeran en [`requirements.txt`](requirements.txt). El [`Dockerfile`](Dockerfile) utiliza Python 3.12.

## Requisitos previos

- Python 3 (se recomienda **3.12**, utilizado por el `Dockerfile`) y `venv`.
- Git.
- El proyecto **Backend_Api** instalado, configurado y ejecutándose, por defecto en `http://127.0.0.1:5000`.
- MySQL configurado **en el backend**: el frontend no se conecta directamente a la base de datos.
- Bibliotecas nativas de Pango y HarfBuzz necesarias para la generación de PDF mediante WeasyPrint. El Dockerfile instala estas dependencias automáticamente cuando se      utiliza Docker.

## Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/NahuelGz1/Frontend-Web.git
cd Frontend-Web
```

Si ya tenés el proyecto clonado, no hace falta volver a clonarlo.

### 2. Crear y activar el entorno virtual

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Instalá las dependencias en cualquiera de los dos sistemas:

```bash
python -m pip install -r requirements.txt
```

> El repositorio también dispone de `init.sh`, que prepara un entorno llamado `venv`, instala las dependencias y crea `.env` si no existe. Los pasos manuales anteriores usan `.venv` como alternativa. No hace falta crear ambos.

### 3. Configurar las variables de entorno

Creá el archivo `.env` a partir de [`.env.example`](.env.example).

**Linux / macOS:**

```bash
cp .env.example .env
```

**Windows (PowerShell):**

```powershell
Copy-Item .env.example .env
```

Verificá especialmente estos valores:

```dotenv
PORT=3000
API_BASE_URL=http://127.0.0.1:5000/api
SECRET_KEY=reemplazar_con_una_clave_aleatoria_de_al_menos_32_caracteres
SESSION_COOKIE_SECURE=false
```

| Variable | Descripción |
| --- | --- |
| `PORT` | Puerto del frontend; por defecto `3000`. |
| `API_BASE_URL` | URL base del backend, normalmente `http://127.0.0.1:5000/api`. |
| `SECRET_KEY` | Clave de Flask utilizada para proteger la sesión; **debe tener al menos 32 caracteres**. |
| `SESSION_COOKIE_SECURE` | En desarrollo local por HTTP suele ser `false`; en un despliegue HTTPS debe ser `true`. |
| `SUPER_ADMIN_EMAIL` | Correo configurado para identificar al administrador principal. |
| `MAIL_SERVER` | Servidor SMTP indicado en el archivo de ejemplo. |
| `MAIL_PORT` | Puerto del servidor SMTP; por defecto `587`. |
| `MAIL_USE_TLS` | Configuración del uso de TLS para el correo electrónico. |
| `MAIL_USERNAME` | Cuenta de correo configurada para los envíos. |
| `MAIL_PASSWORD` | Contraseña o credencial de aplicación de la cuenta de correo. |

Las variables de correo están incluidas en `.env.example`. El envío de las notificaciones del sistema y los correos de reseñas se gestiona desde Backend_Api.

Podés generar una clave segura con:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Nunca subas el archivo `.env` ni claves, tokens o contraseñas al repositorio.**

### 4. Iniciar los servidores

Primero iniciá el **backend**, siguiendo las instrucciones del repositorio [Backend_Api](https://github.com/NahuelGz1/Backend_Api). Verificá su disponibilidad:

- [Estado del backend](http://127.0.0.1:5000/api/ping)

En otra terminal, desde la raíz de `Frontend-Web`, con el entorno virtual activado, ejecutá:

```bash
python app.py
```

Abrí **http://127.0.0.1:3000** en el navegador.

Los puertos y direcciones anteriores corresponden a la configuración local predeterminada; pueden cambiar según `.env`.

## Funcionalidades principales

### Clientes

- Inicio, cartelera, detalle de películas, película destacada y próximos estrenos.
- Registro, inicio y cierre de sesión; recuperación y cambio de contraseña.
- Selección de funciones y butacas disponibles.
- Compra de entradas y servicios adicionales.
- Asociación de servicios adicionales a entradas previamente adquiridas.
- Comprobación del cupo de estacionamiento por función (máximo 20 plazas).
- Consulta y actualización de los datos del perfil.
- Consulta del historial de compras y cancelación según las reglas del sistema.
- Descarga de entradas con códigos QR y facturas en formato PDF.
- Valoración de películas mediante puntuaciones de 1 a 5 estrellas, desde el perfil o mediante enlaces recibidos por correo electrónico.
- Consulta de términos y condiciones y política de privacidad.

### Administración

- Consulta de estadísticas y métricas administrativas.
- Exportación de reportes de ventas en formato PDF.
- Gestión de películas, incluida su edición y búsqueda externa mediante TMDB.
- Selección de una película destacada para la página de inicio.
- Gestión de salas, configuración de capacidad y estados de mantenimiento.
- Programación, modificación y cancelación administrativa de funciones.
- Gestión del catálogo de servicios adicionales, sus precios y disponibilidad.
- Gestión de cuentas de administradores y empleados, restringida al administrador principal.
- Consulta y validación de códigos QR.

### Empleados

- Acceso a un panel destinado a la consulta y validación de códigos QR.
- Canje de entradas y servicios adicionales, incluidos estacionamiento y acceso VIP.

> Las operaciones están restringidas según el rol del usuario. La lógica de negocio y las validaciones finales corresponden al backend.

## Estructura principal

```text
Frontend-Web/
├── app.py
├── routes/
│   ├── admin_views.py
│   ├── auth_views.py
│   ├── auth_security.py
│   └── cliente_views.py
├── services/
│   ├── api_client.py
│   └── pdf_service.py
├── templates/
│   ├── admin/
│   ├── auth/
│   ├── cliente/
│   ├── components/
│   └── layouts/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── instance/
├── requirements.txt
├── .env.example
├── .env.docker.example
├── Dockerfile
├── compose.yaml
├── DOCKER.md
├── init.sh
└── README.md
```

La aplicación se crea en `create_app()` de `app.py`. Las vistas se registran mediante *blueprints* y utilizan `services/api_client.py` para comunicarse con la API.

## Ejemplos de páginas

Con el frontend iniciado localmente:

### Clientes y autenticación

| Ruta | Descripción |
| --- | --- |
| `/` | Página principal y película destacada. |
| `/cartelera` | Catálogo de películas en cartelera. |
| `/estrenos` | Próximos estrenos. |
| `/pelicula/{pelicula_id}` | Detalle de una película y sus funciones. |
| `/elegir-butacas/{funcion_id}` | Selección de butacas para una función. |
| `/registrarse` | Registro de clientes. |
| `/iniciar-sesion` | Inicio de sesión. |
| `/cerrar-sesion` | Cierre de sesión. |
| `/recuperar-contrasena` | Recuperación de contraseña. |
| `/restablecer-contrasena` | Restablecimiento de contraseña. |
| `/cambiar-contrasena` | Cambio de contraseña. |
| `/mi-perfil` | Perfil del usuario autenticado. |
| `/servicios` | Selección de servicios adicionales. |
| `/pagar` | Pantalla de pago. |
| `/compra-exitosa/{compra_id}` | Confirmación de compra. |
| `/compras/{compra_id}/entradas` | Acceso a las entradas de una compra. |
| `/compras/{compra_id}/factura` | Acceso a la factura de una compra. |
| `/cancelar-compra/{compra_id}` | Cancelación de una compra. |
| `/puntuar-desde-mail` | Valoración de películas mediante un enlace recibido por correo. |
| `/terminos-y-condiciones` | Términos y condiciones. |
| `/privacidad` | Política de privacidad. |

### Administración y empleados

| Ruta | Descripción |
| --- | --- |
| `/admin/estadisticas` | Panel de métricas administrativas. |
| `/admin/estadisticas/exportar-pdf` | Exportación de reportes en PDF. |
| `/admin/peliculas` | Gestión de películas. |
| `/admin/salas` | Gestión y mantenimiento de salas. |
| `/admin/funciones` | Gestión de funciones. |
| `/admin/servicios` | Gestión de servicios adicionales. |
| `/admin/habilitar-admins` | Gestión de administradores y empleados. |
| `/admin/validar-qr` | Consulta y validación de códigos QR. |

Las rutas que contienen identificadores requieren valores válidos.
Las páginas de compra pueden depender de datos guardados en la sesión,
por lo que conviene recorrerlas desde la cartelera.

El acceso a las páginas protegidas depende de la autenticación
y de los permisos del usuario.

### Organización de los estilos CSS

Los estilos se encuentran organizados en archivos específicos dentro de `static/css/`, con el objetivo de mejorar la legibilidad, el mantenimiento y la reutilización del código.

- `base.css`: estilos base y variables globales.
- `header.css`: encabezado y navegación.
- `cine-paradiso.css`: estilos generales y componentes compartidos.
- `admin-global.css`: estilos del panel administrativo.
- `auth.css`: pantallas de autenticación.
- `inicio.css`: página de inicio.
- `cartelera.css`: cartelera y próximos estrenos.
- `detalle-pelicula.css`: detalle de películas.
- `funciones.css`: selección de funciones.
- `butacas.css`: selección de butacas.
- `servicios.css` y `servicios-opcionales.css`: servicios adicionales.
- `pago.css`: pantalla de pago.
- `compra-exitosa.css`: confirmación de compra.
- `cancelacion.css`: cancelación de compras.
- `perfil.css`: perfil del usuario.
- `legal.css`: términos y condiciones y política de privacidad.

La modularización de los estilos también incluye mejoras responsive para adaptar la interfaz a computadoras y dispositivos móviles.

## Ejecutar con Docker Compose (opcional)

El repositorio incluye [`DOCKER.md`](DOCKER.md), con instrucciones para levantar **frontend, backend y MySQL** mediante Docker Compose. La disposición esperada de los repositorios es:

```text
Proyecto-Final/
├── Backend_Api/
└── Frontend-Web/
```

Seguí [`DOCKER.md`](DOCKER.md) para configurar `.env.docker`, construir los contenedores y administrar sus datos. **No elimines los volúmenes de MySQL** si querés conservar la base de datos.

## Problemas frecuentes

| Situación | Qué comprobar |
| --- | --- |
| El sitio no inicia y menciona `SECRET_KEY` | Que `.env` exista y contenga una clave de al menos 32 caracteres. |
| La página carga, pero no aparecen películas o funciones | Que `Backend_Api` esté ejecutándose y `API_BASE_URL` apunte a su `/api`. |
| Error de conexión con la API | Comprobar `http://127.0.0.1:5000/api/ping` y revisar los registros de ambos servidores. |
| La sesión no se mantiene | Revisar la configuración de cookies, el entorno HTTP/HTTPS y el almacenamiento de sesiones. |
| Un formulario requiere autenticación | Iniciar sesión con una cuenta válida y comprobar sus permisos. |

## Documentación relacionada

- [Backend_Api — API REST y configuración de MySQL](https://github.com/NahuelGz1/Backend_Api).
- [DOCKER.md — Ejecución del proyecto con Docker](DOCKER.md).
- [Issue #83 — Documentación técnica del proyecto](https://github.com/NahuelGz1/Backend_Api/issues/83).
- - [Manual de API (OpenAPI 3.0)](https://github.com/NahuelGz1/Backend_Api/blob/develop/docs/Manual_API_Cine_paradiso.yaml), mantenido en el repositorio Backend_Api.

---

**Cine Paradiso** — Proyecto académico. Esta guía describe el entorno de desarrollo y no sustituye la configuración de seguridad necesaria para un despliegue en producción.
