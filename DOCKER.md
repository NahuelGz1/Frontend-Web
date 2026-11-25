# Ejecutar Cine Paradiso con Docker

Esta configuración levanta el frontend, el backend y MySQL en contenedores.
La comunicación entre frontend y backend sigue realizándose en Python mediante
`requests`; el navegador no accede directamente al backend ni a MySQL.

## Requisitos

- Docker Desktop con Compose en Windows (con WSL 2 habilitado) o Linux; en Linux
  también se puede usar Docker Engine con el plugin Docker Compose.
- Los dos repositorios clonados como directorios hermanos:

  ```text
  Proyecto-Final/
  ├── Backend_Api/
  └── Frontend-Web/
  ```

- Docker debe tener acceso a esos directorios. En Docker Desktop habilitá el
  acceso a los archivos si es necesario.

## Primera ejecución

1. Abrí una terminal en `Frontend-Web` y copiá la configuración de ejemplo:

   ```bash
   # Linux, Git Bash o WSL
   cp .env.docker.example .env.docker
   ```

   En PowerShell:

   ```powershell
   Copy-Item .env.docker.example .env.docker
   ```

2. Editá `.env.docker`: reemplazá las dos contraseñas de MySQL y las claves
   `SECRET_KEY` y `JWT_SECRET_KEY` por valores diferentes y seguros. Las claves
   de la aplicación deben tener al menos 32 caracteres. Podés generar cada
   valor con Python: `python -c "import secrets; print(secrets.token_hex(32))"`.
   Usar valores hexadecimales evita problemas con caracteres especiales de
   Compose. No compartas ni subas `.env.docker` al repositorio.

3. Desde `Frontend-Web`, ejecutá:

   ```bash
   docker compose --env-file .env.docker up --build -d
   docker compose --env-file .env.docker ps
   ```

   La primera vez puede tardar varios minutos en descargar las imágenes,
   instalar dependencias e inicializar la base. Si algún servicio falla:

   ```bash
   docker compose --env-file .env.docker logs --tail=100
   ```

4. Abrí <http://localhost:3000>. El backend también está disponible desde la
   misma computadora en <http://localhost:5000/api/ping>. MySQL no publica un
   puerto en el anfitrión.

El puerto del frontend puede cambiarse con `FRONTEND_PORT` y el del backend
con `BACKEND_PORT` en `.env.docker`. Si cambiás el puerto del frontend,
actualizá también `FRONTEND_URL`.

## Datos y servicios externos

Para cargar el catálogo de demostración compartido y generar funciones,
reconstruí el backend y ejecutá desde `Frontend-Web`:

```bash
docker compose --env-file .env.docker up -d --build backend
docker compose --env-file .env.docker exec -T backend python -m scripts.cargar_peliculas_demo
```

El catálogo contiene 22 películas de ejemplo: 17 seleccionadas para programar
y cinco para próximos estrenos. Se agregan las que no existen, sin borrar datos
ni modificar las películas existentes, salvo completar un afiche faltante.
Se identifican por título y duración; si hay más de una coincidencia, difiere
la duración o la película está inactiva o eliminada, se informa y se omite.
Las cinco películas para estrenos solo aparecerán como tales si no tienen
funciones previas en esa base. Sus datos y las valoraciones no se copian desde
la base de otra persona. El catálogo no incluye sinopsis; con `TMDB_API_KEY`
configurada, la aplicación puede completarlas desde TMDB.

El comando intenta programar las películas seleccionadas, incluso si todavía
no tienen funciones en esa base, y las demás películas activas con funciones
previas. Busca turnos a las 14, 17, 20 y 23 horas de hoy y los dos días
siguientes, en horario argentino. Omite horarios pasados y conflictos,
incluyendo 15 minutos de limpieza, y no modifica las funciones existentes.
La disponibilidad depende de los horarios y salas de cada base: no garantiza
que todas las películas reciban una función. Puede repetirse sin duplicar
esos turnos. La carga del catálogo se guarda antes de programar; si falla la
programación, corregí el error y repetí el comando.

Para generar más turnos otro día sin volver a cargar el catálogo, usá
`docker compose --env-file .env.docker exec -T backend python -m scripts.generar_funciones_demo`.
Este comando solo programa películas con funciones previas y deja sin
funciones las demás. Ambos comandos son solo para desarrollo.

Para agregar hasta dos **funciones agotadas de prueba**, ejecutá después:

```bash
docker compose --env-file .env.docker exec -T backend python -m scripts.generar_agotadas_demo
```

El comando crea funciones nuevas en horarios libres y ocupa todas sus butacas
con compras y usuarios de demostración. No modifica funciones ni compras
existentes y conserva las películas sin funciones como próximos estrenos.
Mientras existan dos funciones de prueba futuras y activas no crea más;
no repone entradas que se hayan cancelado. Si faltan horarios o salas
disponibles, cancela toda la operación. Estas ventas ficticias afectan la
ocupación, los ingresos y otras estadísticas: usalo únicamente en una base de
desarrollo, nunca en producción.

- MySQL usa el volumen `mysql_data`: los datos sobreviven a reinicios,
  reconstrucciones y `docker compose down`. El volumen es independiente de
  cualquier MySQL instalado en la computadora.
- Solo cuando el volumen está vacío, MySQL ejecuta `init_db.sql`, `catalogo_servicios.sql` y `seed.sql`
  del backend. El seed actual incluye películas, funciones, la cuenta
  administradora inicial y una compra de prueba para validar QR. Esos datos son
  de desarrollo; **no uses esta configuración ni esa cuenta de prueba como
  instalación de producción**. Los cambios posteriores a los scripts no se
  cargan automáticamente sobre un volumen existente.
- Las películas importadas posteriormente desde TMDB, las valoraciones y las
  funciones particulares de una computadora no se comparten automáticamente
  por Git ni Docker. Cada integrante debe ejecutar el comando de catálogo para
  cargar la selección compartida en su propia base.
- Para **restablecer** los servicios en una base de desarrollo existente, hacé
  primero un respaldo y, sin otras operaciones de administración en curso,
  ejecutá desde `Frontend-Web`:

  ```bash
  docker compose --env-file .env.docker up -d db
  docker compose --env-file .env.docker exec -T db sh -c '(echo SET @restablecer_catalogo=1\;; cat /docker-entrypoint-initdb.d/02-servicios.sql) | MYSQL_PWD=$MYSQL_PASSWORD mysql --default-character-set=utf8mb4 --protocol=tcp -h 127.0.0.1 -u $MYSQL_USER $MYSQL_DATABASE'
  ```

  El primer comando actualiza el montaje del archivo sin borrar el volumen. El
  segundo restaura nombres, precios, descripciones, categorías y estado de los
  doce servicios, y elimina sus imágenes personalizadas para mostrar las del
  repositorio. Desactiva los demás servicios, incluidos duplicados, sin borrar
  sus registros ni el historial de compras. La coincidencia se hace por nombre
  según la intercalación de la base y, ante duplicados, se conserva activo el
  de menor ID. Un servicio renombrado no se puede reconocer por su nombre
  anterior: quedará inactivo y se creará uno nuevo. El restablecimiento no
  actualiza los importes históricos de las compras. Los cambios posteriores
  desde administración se conservan hasta volver a ejecutar el comando.
  Reconstruí el frontend con
  `docker compose --env-file .env.docker up -d --build frontend` para obtener
  las plantillas y las imágenes nuevas.
- El backend aplica al arrancar sus migraciones automáticas con el usuario de
  aplicación. El script de creación ya no borra una base existente; ejecutarlo
  manualmente sobre tablas existentes puede fallar en lugar de reemplazarlas.
- `AUTO_SEED` está desactivado; la compra de prueba mencionada proviene de
  `seed.sql`, no del fixture de arranque.
- TMDB requiere `TMDB_API_KEY`. Para correos, configurá `MAIL_*` y/o `SMTP_*`
  según el servicio utilizado. Dentro del contenedor, `localhost` se refiere
  al propio contenedor, no a la computadora anfitriona.
- Las sesiones del frontend se guardan en el contenedor. Al recrearlo, los
  usuarios tendrán que iniciar sesión nuevamente.
- Las contraseñas de MySQL se aplican al inicializar un volumen nuevo. Cambiar
  `.env.docker` después no cambia los usuarios ya creados en la base: hay que
  actualizar las contraseñas también en MySQL.

## Acceso desde otro dispositivo

El puerto del frontend escucha en las interfaces del anfitrión. Para acceder
desde un celular o computadora de la misma red, usá
`http://IP_DEL_ANFITRION:3000` (o el puerto configurado) y permití el puerto en
el firewall. Configurá `FRONTEND_URL` con esa misma dirección para que los
enlaces de los correos funcionen desde el dispositivo.

Para acceso público necesitás configurar un dominio, HTTPS y un proxy inverso.
Con HTTPS, configurá `SESSION_COOKIE_SECURE=true`. Esta configuración es para
desarrollo y demostración: no incluye proxy, certificados, copias de seguridad
ni una configuración segura de producción.

## Operaciones habituales

Ejecutá estos comandos desde `Frontend-Web`:

```bash
# Ver logs
docker compose --env-file .env.docker logs -f

# Reconstruir después de cambiar código o dependencias
docker compose --env-file .env.docker up --build -d

# Detener sin borrar la base
docker compose --env-file .env.docker down
```

No uses `docker compose down -v` salvo que quieras eliminar **todos los datos**
del volumen de MySQL. Para conservar datos importantes, hacé una copia de
seguridad antes de cualquier operación sobre el volumen.
