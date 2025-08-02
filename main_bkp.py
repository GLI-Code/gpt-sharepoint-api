"""
FastAPI application that exposes a single endpoint to retrieve the
contents of a file hosted in a SharePoint document library.  The
application uses the OAuth2 client‑credentials flow to authenticate
against Microsoft Graph.

Environment variables
---------------------
The following environment variables must be defined for the service to
function correctly:

```
TENANT_ID      Azure Active Directory tenant identifier
CLIENT_ID      Application (client) identifier
CLIENT_SECRET  Client secret associated with the application
SITE_ID        The SharePoint site identifier
DRIVE_ID       Identifier of the drive (document library) within the site
```

At runtime these variables can be supplied via a `.env` file (see
`.env.template`) or directly in the execution environment.  When the
application starts it validates that each of the variables is present
and raises an exception otherwise.

Usage
-----
Run the application with Uvicorn either directly or through Docker:

```
uvicorn main:app --host 0.0.0.0 --port 9080
```

Once running, open the interactive documentation at
`http://localhost:9080/docs` to test the endpoint interactively.  A
sample `curl` invocation is also provided in the README.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from a .env file if present.
load_dotenv()

def get_env_variable(name: str) -> str:
    """Fetch a required environment variable or raise an error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

# Fetch configuration
TENANT_ID = get_env_variable("TENANT_ID")
CLIENT_ID = get_env_variable("CLIENT_ID")
CLIENT_SECRET = get_env_variable("CLIENT_SECRET")
SITE_ID = get_env_variable("SITE_ID")
DRIVE_ID = get_env_variable("DRIVE_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPE = "https://graph.microsoft.com/.default"

async def acquire_access_token() -> str:
    """Obtain a bearer access token using the client‑credentials flow."""
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
        "grant_type": "client_credentials",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(AUTHORITY, data=data)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to obtain access token: {exc}"
        )
    token_data = response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service returned no access token",
        )
    return access_token

async def download_file_by_path(folder: str, file_name: str, access_token: str) -> str:
    """Download file from SharePoint by path (e.g., /folder/file.ext)."""
    headers = {"Authorization": f"Bearer {access_token}"}
    path = f"/{folder.strip()}/{file_name}" if folder else f"/{file_name}"
    encoded_path = path.replace(" ", "%20")
    url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:{encoded_path}:/content"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Archivo '{file_name}' no encontrado en '{folder}'")
        raise HTTPException(status_code=500, detail=f"Error al acceder a Graph: {exc}")

    try:
        return resp.text
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="El archivo no contiene datos de texto legibles.")

class FileRequest(BaseModel):
    """Schema for the request body accepted by the /get_file endpoint."""
    fileName: str = Field(..., description="Nombre del archivo a recuperar de SharePoint")
    folder: Optional[str] = Field("", description="Nombre de la carpeta (opcional)")

app = FastAPI(
    title="SharePoint File Retrieval API",
    description=(
        "API que expone un único endpoint para recuperar archivos de un "
        "sitio de SharePoint usando Microsoft Graph y autenticación OAuth2."
    ),
    version="1.1.0",
)

@app.post(
    "/get_file",
    response_class=PlainTextResponse,
    responses={
        200: {"content": {"text/plain": {}}, "description": "Contenido del archivo como texto plano"},
        404: {"description": "Archivo no encontrado"},
        400: {"description": "Archivo no es de texto"},
        502: {"description": "Error de comunicación con Microsoft Graph"},
    },
    summary="Recuperar archivo de SharePoint",
    tags=["files"],
)
async def get_file(request: FileRequest) -> str:
    """Endpoint para obtener el contenido de un archivo de SharePoint.

    Se espera un cuerpo JSON con `fileName` y opcionalmente `folder`.
    """
    access_token = await acquire_access_token()
    return await download_file_by_path(request.folder, request.fileName, access_token)