"""
Helper script to discover the identifiers of a SharePoint site and its
default document library (drive).  These identifiers are required to
configure the API defined in `main.py`.

This script uses the Microsoft Graph API and the OAuth2 client
credentials flow to authenticate.  It accepts the name of the site and
the tenant's SharePoint domain on the command line, then prints the
`SITE_ID` and `DRIVE_ID` values.  If multiple drives exist on the
site the first (often the default "Documents" library) is chosen.

Example usage::

    python get_site_drive_ids.py --site-name Ventas \
        --domain genommalab.sharepoint.com \
        --tenant-id <TENANT_ID> \
        --client-id <CLIENT_ID> \
        --client-secret <CLIENT_SECRET>

Note: The Graph API version used here is `v1.0`.  See
https://learn.microsoft.com/graph/api/site-get for more details.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

import requests


AUTH_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
SCOPE = "https://graph.microsoft.com/.default"


def acquire_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Obtain a bearer token via the client credentials flow.

    Raises a RuntimeError on failure rather than returning an HTTP
    response so that errors propagate to the caller cleanly.
    """
    token_url = AUTH_TEMPLATE.format(tenant_id=tenant_id)
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": SCOPE,
        "grant_type": "client_credentials",
    }
    resp = requests.post(token_url, data=data)
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Failed to obtain token: {exc.response.text if exc.response else exc}"
        ) from exc
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Token endpoint returned no access_token")
    return token


def get_site_id(domain: str, site_name: str, headers: dict) -> str:
    """Retrieve the unique identifier for a SharePoint site.

    Parameters
    ----------
    domain: str
        The tenant's SharePoint domain, e.g. `genommalab.sharepoint.com`.
    site_name: str
        The human‑readable name of the site (as appears in the URL after `/sites/`).
    headers: dict
        Authorization headers including the bearer token.
    """
    # Build the URL for the site resource.  The pattern is
    # {domain}:/sites/{site_name}.  See
    # https://learn.microsoft.com/graph/api/site-get for details.
    # Build the URL for the site resource using the hostname and relative
    # path.  According to the Microsoft Graph documentation, a site can
    # be addressed by its hostname and server‑relative path using the
    # syntax `/sites/{hostname}:/{relative-path}`【272179473099373†L187-L204】.  We do
    # not append additional query parameters here since some SharePoint
    # tenants reject `$select=id` on this request.
    url = f"https://graph.microsoft.com/v1.0/sites/{domain}:/{'sites/' + site_name}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    site_id = data.get("id")
    if not site_id:
        raise RuntimeError("Failed to obtain site id from response")
    return site_id


def get_default_drive_id(site_id: str, headers: dict) -> str:
    """Retrieve the identifier of the default drive (document library) for a site."""
    # List the drives for the given site.  The first drive is
    # conventionally the primary document library, often called "Documents".
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    drives = resp.json().get("value", [])
    if not drives:
        raise RuntimeError("The specified site has no drives")
    return drives[0]["id"]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Obtener los identificadores SITE_ID y DRIVE_ID para un sitio de SharePoint."
        )
    )
    parser.add_argument(
        "--site-name",
        required=True,
        help="Nombre del sitio (como aparece en la URL después de '/sites/').",
    )
    parser.add_argument(
        "--domain",
        required=True,
        help="Dominio de SharePoint (p.ej. 'contoso.sharepoint.com').",
    )
    parser.add_argument(
        "--tenant-id",
        required=True,
        help="Identificador del tenant de Azure Active Directory.",
    )
    parser.add_argument(
        "--client-id",
        required=True,
        help="Application (client) ID registrado en Azure.",
    )
    parser.add_argument(
        "--client-secret",
        required=True,
        help="Secreto de cliente para la aplicación.",
    )
    args = parser.parse_args(argv)

    try:
        token = acquire_token(args.tenant_id, args.client_id, args.client_secret)
    except RuntimeError as exc:
        print(f"Error acquiring token: {exc}", file=sys.stderr)
        return 1
    headers = {"Authorization": f"Bearer {token}"}
    try:
        site_id = get_site_id(args.domain, args.site_name, headers)
    except Exception as exc:
        print(f"Error obtaining site ID: {exc}", file=sys.stderr)
        return 1
    try:
        drive_id = get_default_drive_id(site_id, headers)
    except Exception as exc:
        print(f"Error obtaining drive ID: {exc}", file=sys.stderr)
        return 1
    print(f"SITE_ID={site_id}")
    print(f"DRIVE_ID={drive_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())