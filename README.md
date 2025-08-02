# SharePoint File Retrieval API

Este proyecto implementa una API REST sencilla que permite recuperar
archivos almacenados en una biblioteca de documentos de SharePoint
mediante Microsoft Graph y el flujo de autenticación OAuth2
`client_credentials`.  El servicio está construido con
[FastAPI](https://fastapi.tiangolo.com/) y se empaqueta en un contenedor
Docker listo para ejecutarse localmente o desplegarse en la nube.

## Tabla de contenidos

- [Características](#características)
- [Requisitos](#requisitos)
- [Configuración](#configuración)
- [Uso del script de descubrimiento](#uso-del-script-de-descubrimiento)
- [Ejecución con Docker](#ejecución-con-docker)
- [Probar el endpoint](#probar-el-endpoint)
- [Documentación interactiva](#documentación-interactiva)
- [Despliegue en AWS (opcional)](#despliegue-en-aws-opcional)

## Características

* **Endpoint único**: `POST /get_file` que recibe un JSON con el nombre
  del archivo y devuelve su contenido como texto plano.
* **Autenticación segura**: utiliza el flujo de client credentials de
  Azure AD para obtener tokens de acceso a Microsoft Graph.
* **Búsqueda y descarga**: localiza el archivo por su nombre en la
  biblioteca de documentos configurada y descarga su contenido.
* **Empaquetado en contenedor**: incluye `Dockerfile` y
  `docker-compose.yml` para simplificar la ejecución y el despliegue.

## Requisitos

* Python 3.12 (solo necesario si quieres ejecutar el código sin Docker).
* Una aplicación registrada en Azure AD con permisos de aplicación para
  Microsoft Graph (por ejemplo, `Sites.Read.All` y `Files.Read.All`).
* Identificador de tenant (`TENANT_ID`), identificador de cliente
  (`CLIENT_ID`) y secreto de cliente (`CLIENT_SECRET`).
* El identificador del sitio (`SITE_ID`) y de la biblioteca de
  documentos (`DRIVE_ID`).  Estos valores se pueden obtener con el
  script incluido, como se detalla en la siguiente sección.

## Configuración

1. **Clonar el repositorio** (si aún no lo has hecho) y acceder al
   directorio `sharepoint_api`.

2. **Crear el archivo de entorno**.  Copia `.env.template` a un
   archivo llamado `.env` y rellena los valores de acuerdo con tu
   configuración de Azure y SharePoint:

   ```bash
   cp .env.template .env
   # Edita .env con tu editor favorito y proporciona TENANT_ID,
   # CLIENT_ID, CLIENT_SECRET, SITE_ID y DRIVE_ID
   ```

   > ⚠️ **Nunca** subas tus credenciales reales a un control de
   > versiones público.  El archivo `.env.template` sirve como
   > referencia y no contiene secretos.

## Uso del script de descubrimiento

Si no conoces el `SITE_ID` y `DRIVE_ID` de tu sitio de SharePoint,
puedes descubrirlos ejecutando el script `get_site_drive_ids.py`.  Este
script requiere tu `TENANT_ID`, `CLIENT_ID` y `CLIENT_SECRET`, así como
el nombre del sitio y el dominio de SharePoint.  **Nota**: el script
utiliza la biblioteca `requests`, por lo que antes de ejecutarlo fuera
del contenedor debes instalar las dependencias con
`pip install -r requirements.txt`.

```bash
python get_site_drive_ids.py \
    --site-name Ventas \
    --domain genommalab.sharepoint.com \
    --tenant-id <TU_TENANT_ID> \
    --client-id <TU_CLIENT_ID> \
    --client-secret <TU_CLIENT_SECRET>

# Salida esperada:
SITE_ID=01234567-89ab-cdef-0123-456789abcdef
DRIVE_ID=98765432-1abc-def0-9876-54321fedcba
```

Copia estos valores en tu archivo `.env`.

## Ejecución con Docker

El proyecto incluye un `docker-compose.yml` que simplifica la
construcción y ejecución del servicio.  Asegúrate de haber completado
el archivo `.env` antes de iniciar los contenedores.

```bash
cd sharepoint_api
docker-compose up --build
```

Esto compilará la imagen, instalará las dependencias y expondrá la API
en `http://localhost:9080`.  Si todo es correcto verás en la salida
algo similar a:

```
INFO:     Uvicorn running on http://0.0.0.0:9080 (Press CTRL+C to quit)
```

## Probar el endpoint

Para solicitar un archivo por su nombre puedes usar `curl` o cualquier
cliente HTTP.  El siguiente ejemplo solicita un archivo llamado
`ventas_2024.csv` y almacena la respuesta en un archivo local:

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"fileName": "ventas_2024.csv"}' \
     http://localhost:9080/get_file \
     -o ventas_2024.csv

# Si el archivo no existe, la API devolverá un error 404 con un
# mensaje descriptivo:
# {"detail":"Archivo 'ventas_2024.csv' no encontrado en el sitio de SharePoint"}
```

Recuerda que el endpoint devuelve siempre contenido **de texto**.  Si
solicitas un archivo binario (por ejemplo, una imagen), la API
responderá con un error 400 indicando que el archivo no contiene datos
legibles como texto.

## Documentación interactiva

FastAPI expone automáticamente documentación OpenAPI y una interfaz
Swagger interactiva.  Una vez que el contenedor esté en ejecución
puedes abrir en tu navegador:

* Swagger UI: <http://localhost:9080/docs>
* Documentación ReDoc: <http://localhost:9080/redoc>

A través de estas páginas puedes probar el endpoint, ver los modelos de
entrada y salida y explorar la API de forma interactiva.

## Despliegue en AWS (opcional)

Para desplegar esta API en Amazon Web Services (AWS) puedes subir la
imagen generada a Amazon Elastic Container Registry (ECR) y ejecutarla
en un clúster de ECS detrás de un Application Load Balancer (ALB).
Aunque la configuración específica depende de tu infraestructura,
aquí se muestran los pasos generales:

1. **Construir la imagen** y autenticarte en ECR:

   ```bash
   # Suponiendo que ya tienes un repositorio en ECR
   aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
   docker build -t sharepoint-api .
   docker tag sharepoint-api:latest <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/sharepoint-api:latest
   docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/sharepoint-api:latest
   ```

2. **Crear un servicio ECS** que utilice la imagen de ECR.  Configura
   las variables de entorno (`TENANT_ID`, `CLIENT_ID`, etc.) en la
   definición de la tarea o a través de Secrets Manager si lo prefieres.

3. **Configurar un Application Load Balancer** para exponer la API
   públicamente.  Asegúrate de que el listener del ALB apunte al puerto
   9080 del contenedor.

Revisa la [documentación oficial de AWS](https://docs.aws.amazon.com/ecs/) para obtener información detallada sobre la creación de repositorios ECR, tareas ECS y balanceadores de carga.

---

Esperamos que esta API te permita integrar de forma sencilla archivos
de SharePoint en tus flujos de trabajo basados en GPT y otras
aplicaciones.  Para cualquier mejora o corrección no dudes en abrir
una solicitud de cambio.