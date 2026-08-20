"""Blue Prism REST API client -- OAuth2 client-credentials auth against the
Authentication Server, thin wrappers around the Hub/Blue Prism API (processes/
sessions/work queues/resources/credentials).

WHY OAUTH2 CLIENT CREDENTIALS AGAINST A SEPARATE AUTHENTICATION SERVER --
see app.py module docstring for the full architectural reasoning (Blue
Prism Hub + Authentication Server v4.7+ requirement, fragmentation risk
flagged in Discovery).

Token is requested against the tenant's own Authentication Server
(`POST {auth_server_url}/connect/token` with grant_type=client_credentials
+ client_id + client_secret) and the resulting bearer token is sent as
`Authorization: Bearer <token>` on every subsequent call to the Hub/Blue
Prism API base URL.

WHY 401 vs 403 ARE HANDLED DIFFERENTLY, SAME PRINCIPLE AS UiPath/Automation
Anywhere/MuleSoft/n8n/Make.com/Power Automate CONNECTOR's clients.

A 401 means the client_id/client_secret pair is not accepted at all (wrong
credentials, or the Authentication Server itself rejected the grant). A 403
means the token was issued fine, but the caller's Service Account lacks the
Blue Prism role/permission for this specific operation (e.g. a specific
Process's or Work Queue's permission) -- a materially different, more
specific and more fixable cause (the fix is granting a role/permission in
Blue Prism, not re-entering credentials) that must not be reported as
"wrong credentials".
"""
from __future__ import annotations

TOKEN_REJECTED = "BP_TOKEN_REJECTED"
PERMISSION_DENIED = "BP_PERMISSION_DENIED"
NOT_FOUND = "BP_NOT_FOUND"
RATE_LIMITED = "BP_RATE_LIMITED"
BACKEND_5XX = "BP_BACKEND_ERROR"
VALIDATION_FAILED = "BP_VALIDATION_FAILED"
RESPONSE_UNEXPECTED = "BP_UNEXPECTED_RESPONSE"


class ClientFail(Exception):
    def __init__(self, payload: dict):
        self.payload = payload
        super().__init__(payload.get("error", "Blue Prism request failed."))


def _check_status(resp, ok_codes=(200, 201, 204)) -> None:
    if resp.status_code in ok_codes:
        return
    if resp.status_code == 401:
        raise ClientFail({"error": "Authentication Server rejected the client credentials.", "error_code": TOKEN_REJECTED})
    if resp.status_code == 403:
        raise ClientFail({"error": "The Service Account lacks permission for this operation in Blue Prism.", "error_code": PERMISSION_DENIED})
    if resp.status_code == 404:
        raise ClientFail({"error": "The requested Blue Prism resource was not found.", "error_code": NOT_FOUND})
    if resp.status_code == 429:
        raise ClientFail({"error": "Rate limited by the Blue Prism API. Try again shortly.", "error_code": RATE_LIMITED})
    if resp.status_code == 400:
        raise ClientFail({"error": f"Blue Prism rejected the request: {resp.text[:300]}", "error_code": VALIDATION_FAILED})
    if resp.status_code >= 500:
        raise ClientFail({"error": "Blue Prism's own backend returned an error.", "error_code": BACKEND_5XX})
    raise ClientFail({"error": f"Unexpected response ({resp.status_code}): {resp.text[:300]}", "error_code": RESPONSE_UNEXPECTED})


async def get_access_token(ctx, auth_server_url: str, client_id: str, client_secret: str) -> dict:
    import httpx
    url = auth_server_url.rstrip("/") + "/connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "BluePrismHub",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if resp.status_code != 200:
        return {"ok": False, "error": "Authentication Server rejected the client credentials.", "error_code": TOKEN_REJECTED}
    body = resp.json()
    return {"ok": True, "access_token": body.get("access_token", "")}


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


async def _get(ctx, token: str, api_base_url: str, path: str, params: dict | None = None):
    import httpx
    url = api_base_url.rstrip("/") + path
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers(token), params=params or {})
    _check_status(resp)
    return resp.json() if resp.content else {}


async def _post(ctx, token: str, api_base_url: str, path: str, json_body: dict | None = None):
    import httpx
    url = api_base_url.rstrip("/") + path
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=_headers(token), json=json_body or {})
    _check_status(resp)
    return resp.json() if resp.content else {}


async def _put(ctx, token: str, api_base_url: str, path: str, json_body: dict | None = None):
    import httpx
    url = api_base_url.rstrip("/") + path
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(url, headers=_headers(token), json=json_body or {})
    _check_status(resp)
    return resp.json() if resp.content else {}


# ── Processes ───────────────────────────────────────────────────────────


async def list_processes(ctx, token: str, api_base_url: str) -> list[dict]:
    body = await _get(ctx, token, api_base_url, "/processes")
    return body.get("processes", body if isinstance(body, list) else [])


async def get_process(ctx, token: str, api_base_url: str, process_id: str) -> dict:
    return await _get(ctx, token, api_base_url, f"/processes/{process_id}")


# ── Sessions ────────────────────────────────────────────────────────────


async def list_sessions(ctx, token: str, api_base_url: str, process_id: str = "") -> list[dict]:
    params = {"processId": process_id} if process_id else None
    body = await _get(ctx, token, api_base_url, "/sessions", params=params)
    return body.get("sessions", body if isinstance(body, list) else [])


async def get_session(ctx, token: str, api_base_url: str, session_id: str) -> dict:
    return await _get(ctx, token, api_base_url, f"/sessions/{session_id}")


async def start_session(ctx, token: str, api_base_url: str, process_id: str, resource_ids: list[str] | None, inputs: dict | None) -> dict:
    payload = {"processId": process_id}
    if resource_ids:
        payload["resourceIds"] = resource_ids
    if inputs:
        payload["inputs"] = inputs
    return await _post(ctx, token, api_base_url, "/sessions", json_body=payload)


async def stop_session(ctx, token: str, api_base_url: str, session_id: str, action: str = "stop") -> dict:
    endpoint = "terminate" if action == "terminate" else "stop"
    return await _post(ctx, token, api_base_url, f"/sessions/{session_id}/{endpoint}")


# ── Work Queues + Queue Items ──────────────────────────────────────────


async def list_work_queues(ctx, token: str, api_base_url: str) -> list[dict]:
    body = await _get(ctx, token, api_base_url, "/workqueues")
    return body.get("queues", body if isinstance(body, list) else [])


async def list_queue_items(ctx, token: str, api_base_url: str, queue_id: str, status: str = "") -> list[dict]:
    params = {"status": status} if status else None
    body = await _get(ctx, token, api_base_url, f"/workqueues/{queue_id}/items", params=params)
    return body.get("items", body if isinstance(body, list) else [])


async def add_queue_item(ctx, token: str, api_base_url: str, queue_id: str, key_value: str, data: dict | None) -> dict:
    payload = {"keyValue": key_value}
    if data:
        payload["data"] = data
    return await _post(ctx, token, api_base_url, f"/workqueues/{queue_id}/items", json_body=payload)


async def set_queue_item_status(ctx, token: str, api_base_url: str, item_id: str, status: str) -> dict:
    return await _put(ctx, token, api_base_url, f"/workqueueitems/{item_id}/status", json_body={"status": status})


# ── Runtime Resources ───────────────────────────────────────────────────


async def list_resources(ctx, token: str, api_base_url: str) -> list[dict]:
    body = await _get(ctx, token, api_base_url, "/resources")
    return body.get("resources", body if isinstance(body, list) else [])


# ── Credentials (metadata only) ────────────────────────────────────────


async def list_credentials(ctx, token: str, api_base_url: str) -> list[dict]:
    body = await _get(ctx, token, api_base_url, "/credentials")
    return body.get("credentials", body if isinstance(body, list) else [])
