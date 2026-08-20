"""Chat functions for Blue Prism Connector: connection management,
Processes, Sessions (process runs), Work Queues/queue items, Runtime
Resources, Credential metadata, and bulk operations + estate audit
(value-add). Built on bp_client.py / schemas.py, following the same shape
as UiPath Connector's / Automation Anywhere Connector's handlers.py.
"""
from __future__ import annotations

import uuid

from imperal_sdk import ActionResult

import bp_client as bc
from app import ext, chat
from schemas import (
    NoParams,
    ConnectBluePrismParams, ProviderConnection, ProviderConnectionList,
    DisconnectBluePrismParams, DeleteResult,
    ListProcessesParams, Process, ProcessList,
    GetProcessParams,
    ListSessionsParams, Session, SessionList,
    GetSessionParams,
    StartSessionParams, StopSessionParams, SessionActionResult,
    ListWorkQueuesParams, WorkQueue, WorkQueueList,
    ListQueueItemsParams, QueueItem, QueueItemList,
    AddQueueItemParams, SetQueueItemStatusParams,
    ListResourcesParams, Resource, ResourceList,
    ListCredentialsParams, Credential, CredentialList,
    BulkSessionResultItem, BulkSessionResult, BulkSessionIdsParams,
    AuditEstateParams, EstateAuditRow, EstateAuditReport,
)

_SECRET_NAME = "bp_connections"


# ──────────────────────────────────────────────────────────────────────────
# Connection management
# ──────────────────────────────────────────────────────────────────────────


async def _load_connections(ctx) -> list[dict]:
    import json
    raw = await ctx.secrets.get(_SECRET_NAME)
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


async def _save_connections(ctx, connections: list[dict]) -> None:
    import json
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


def _to_provider_connection(c: dict) -> ProviderConnection:
    detail = f"{c.get('api_base_url', '')}"
    return ProviderConnection(
        id=c.get("id", ""),
        title=c.get("label") or c.get("api_base_url", "Blue Prism estate"),
        connected=True,
        detail=detail,
        api_base_url=c.get("api_base_url", ""),
    )


async def _get_token_and_conn(ctx, connection_id: str):
    connections = await _load_connections(ctx)
    if not connections:
        return ActionResult.error("No Blue Prism estate connected yet. Use connect_blue_prism first.", code="BP_NOT_CONNECTED")
    conn = None
    if connection_id:
        conn = next((c for c in connections if c.get("id") == connection_id), None)
        if conn is None:
            return ActionResult.error(f"No connection found with id {connection_id}.", code="BP_CONNECTION_NOT_FOUND")
    else:
        conn = connections[0]
    tok = await bc.get_access_token(ctx, conn["auth_server_url"], conn["client_id"], conn["client_secret"])
    if not tok.get("ok"):
        return ActionResult.error(tok.get("error", "Failed to authenticate with Blue Prism."), code=tok.get("error_code", "BP_ERROR"))
    return conn, tok["access_token"]


@chat.function(
    "connect_blue_prism",
    "Connect your Blue Prism estate (via Blue Prism Hub + Authentication "
    "Server v4.7+) by saving your Service Account's client_id/client_secret "
    "plus the Authentication Server URL and Hub/API base URL, after "
    "checking the credentials actually work. Requires Blue Prism Hub + "
    "Authentication Server v4.7+ -- classic Blue Prism Server without Hub "
    "has no REST surface this connector can reach.",
    action_type="write",
    chain_callable=True,
    data_model=ProviderConnection,
    event="blue-prism-connector.connect_blue_prism",
    effects=["blue_prism.provider.connected"],
)
async def connect_blue_prism(ctx, params: ConnectBluePrismParams) -> ActionResult:
    """Connect a Blue Prism estate."""
    tok = await bc.get_access_token(ctx, params.auth_server_url, params.client_id, params.client_secret)
    if not tok.get("ok"):
        return ActionResult.error(tok.get("error", "Failed to authenticate with Blue Prism."), code=tok.get("error_code", "BP_ERROR"))
    connections = await _load_connections(ctx)
    conn_id = str(uuid.uuid4())
    entry = {
        "id": conn_id,
        "auth_server_url": params.auth_server_url,
        "api_base_url": params.api_base_url,
        "client_id": params.client_id,
        "client_secret": params.client_secret,
        "label": params.label,
    }
    connections.append(entry)
    await _save_connections(ctx, connections)
    return ActionResult.ok(_to_provider_connection(entry), message="Blue Prism estate connected.")


@chat.function(
    "list_connections",
    "List the connected Blue Prism estates.",
    action_type="read",
    chain_callable=True,
    data_model=ProviderConnectionList,
    event="blue-prism-connector.list_connections",
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List connected Blue Prism estates."""
    connections = await _load_connections(ctx)
    items = [_to_provider_connection(c) for c in connections]
    return ActionResult.ok(ProviderConnectionList(title="Connected Blue Prism estates", items=items))


@chat.function(
    "disconnect_blue_prism",
    "Disconnect one Blue Prism estate. Nothing in Blue Prism itself is "
    "changed; only the saved credentials here are deleted.",
    action_type="write",
    chain_callable=True,
    data_model=DeleteResult,
    event="blue-prism-connector.disconnect_blue_prism",
    effects=["blue_prism.provider.disconnected"],
)
async def disconnect_blue_prism(ctx, params: DisconnectBluePrismParams) -> ActionResult:
    """Disconnect a Blue Prism estate."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error(f"No connection found with id {params.connection_id}.", code="BP_CONNECTION_NOT_FOUND")
    await _save_connections(ctx, remaining)
    return ActionResult.ok(DeleteResult(id=params.connection_id, title="Disconnected", ok=True), message="Blue Prism estate disconnected.")


# ──────────────────────────────────────────────────────────────────────────
# Processes
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_processes",
    "List processes available in the connected Blue Prism estate.",
    action_type="read",
    chain_callable=True,
    data_model=ProcessList,
    event="blue-prism-connector.list_processes",
)
async def list_processes(ctx, params: ListProcessesParams) -> ActionResult:
    """List Blue Prism processes."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        raw = await bc.list_processes(ctx, token, conn["api_base_url"])
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to list processes."), code=e.payload.get("error_code", "BP_ERROR"))
    items = [
        Process(id=str(p.get("id", "")), title=p.get("name", ""), description=p.get("description", "") or "",
                is_published=bool(p.get("isPublished", False)))
        for p in raw
    ]
    return ActionResult.ok(ProcessList(title="Processes", items=items))


@chat.function(
    "get_process",
    "Read one Blue Prism process in full.",
    action_type="read",
    chain_callable=True,
    data_model=Process,
    event="blue-prism-connector.get_process",
)
async def get_process(ctx, params: GetProcessParams) -> ActionResult:
    """Read one Blue Prism process."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        p = await bc.get_process(ctx, token, conn["api_base_url"], params.process_id)
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to read process."), code=e.payload.get("error_code", "BP_ERROR"))
    return ActionResult.ok(Process(id=str(p.get("id", "")), title=p.get("name", ""), description=p.get("description", "") or "",
                                    is_published=bool(p.get("isPublished", False))))


# ──────────────────────────────────────────────────────────────────────────
# Sessions (process runs)
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_sessions",
    "List recent sessions (process runs) in the connected Blue Prism "
    "estate, most recent first, optionally filtered by process.",
    action_type="read",
    chain_callable=True,
    data_model=SessionList,
    event="blue-prism-connector.list_sessions",
)
async def list_sessions(ctx, params: ListSessionsParams) -> ActionResult:
    """List Blue Prism sessions."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        raw = await bc.list_sessions(ctx, token, conn["api_base_url"], process_id=params.process_id)
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to list sessions."), code=e.payload.get("error_code", "BP_ERROR"))
    items = [
        Session(id=str(s.get("id", "")), title=s.get("processName", "") or str(s.get("id", "")),
                status=s.get("status"), process_name=s.get("processName", "") or "",
                resource_name=s.get("resourceName", "") or "",
                start_datetime=s.get("startDateTime", "") or "", end_datetime=s.get("endDateTime", "") or "")
        for s in raw
    ]
    return ActionResult.ok(SessionList(title="Sessions", items=items))


@chat.function(
    "get_session",
    "Read one session in full -- status, timing, resource, and any error "
    "info.",
    action_type="read",
    chain_callable=True,
    data_model=Session,
    event="blue-prism-connector.get_session",
)
async def get_session(ctx, params: GetSessionParams) -> ActionResult:
    """Read one Blue Prism session."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        s = await bc.get_session(ctx, token, conn["api_base_url"], params.session_id)
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to read session."), code=e.payload.get("error_code", "BP_ERROR"))
    return ActionResult.ok(Session(
        id=str(s.get("id", "")), title=s.get("processName", "") or str(s.get("id", "")),
        status=s.get("status"), process_name=s.get("processName", "") or "",
        resource_name=s.get("resourceName", "") or "",
        start_datetime=s.get("startDateTime", "") or "", end_datetime=s.get("endDateTime", "") or "",
    ))


@chat.function(
    "start_session",
    "Start a session: run a process now, either on explicit runtime "
    "resources or by letting Blue Prism pick, with optional input "
    "parameters.",
    action_type="write",
    chain_callable=True,
    data_model=SessionActionResult,
    event="blue-prism-connector.start_session",
    effects=["blue_prism.session.started"],
)
async def start_session(ctx, params: StartSessionParams) -> ActionResult:
    """Start a Blue Prism session."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        result = await bc.start_session(
            ctx, token, conn["api_base_url"], process_id=params.process_id,
            resource_ids=params.resource_ids, inputs=params.inputs,
        )
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to start session."), code=e.payload.get("error_code", "BP_ERROR"))
    session_id = str(result.get("sessionId", ""))
    return ActionResult.ok(
        SessionActionResult(id=session_id, title="Session started", ok=True, detail="started"),
        message=f"Session {session_id} started.",
    )


@chat.function(
    "stop_session",
    "Stop a running session: 'stop' for graceful stop, 'terminate' to "
    "force-kill immediately.",
    action_type="write",
    chain_callable=True,
    data_model=SessionActionResult,
    event="blue-prism-connector.stop_session",
    effects=["blue_prism.session.stopped"],
)
async def stop_session(ctx, params: StopSessionParams) -> ActionResult:
    """Stop a Blue Prism session."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        await bc.stop_session(ctx, token, conn["api_base_url"], params.session_id, action=params.action)
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to stop session."), code=e.payload.get("error_code", "BP_ERROR"))
    return ActionResult.ok(
        SessionActionResult(id=params.session_id, title=f"Session {params.action} requested", ok=True, detail=params.action),
        message=f"Requested {params.action} for session {params.session_id}.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Work Queues + queue items
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_work_queues",
    "List Work Queues configured in the connected Blue Prism estate -- the "
    "queue/queue-item pattern used for high-volume unattended work.",
    action_type="read",
    chain_callable=True,
    data_model=WorkQueueList,
    event="blue-prism-connector.list_work_queues",
)
async def list_work_queues(ctx, params: ListWorkQueuesParams) -> ActionResult:
    """List Work Queues."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        raw = await bc.list_work_queues(ctx, token, conn["api_base_url"])
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to list work queues."), code=e.payload.get("error_code", "BP_ERROR"))
    items = [
        WorkQueue(id=str(q.get("id", "")), title=q.get("name", ""), key_field=q.get("keyField", "") or "",
                  max_attempts=q.get("maxAttempts", 0) or 0, pending_count=q.get("pendingCount", 0) or 0)
        for q in raw
    ]
    return ActionResult.ok(WorkQueueList(title="Work queues", items=items))


@chat.function(
    "list_queue_items",
    "List items in a Work Queue, optionally filtered by status ('Pending', "
    "'Locked', 'Completed', 'Exception').",
    action_type="read",
    chain_callable=True,
    data_model=QueueItemList,
    event="blue-prism-connector.list_queue_items",
)
async def list_queue_items(ctx, params: ListQueueItemsParams) -> ActionResult:
    """List items in a Work Queue."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        raw = await bc.list_queue_items(ctx, token, conn["api_base_url"], params.queue_id, status=params.status)
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to list queue items."), code=e.payload.get("error_code", "BP_ERROR"))
    items = [
        QueueItem(id=str(i.get("id", "")), title=i.get("keyValue", "") or str(i.get("id", "")), queue_id=params.queue_id,
                  status=i.get("status"), attempt=i.get("attempt", 0) or 0, key_value=i.get("keyValue", "") or "")
        for i in raw
    ]
    return ActionResult.ok(QueueItemList(title=f"Queue items -- {params.queue_id}", items=items))


@chat.function(
    "add_queue_item",
    "Add a new work item to a Work Queue -- the payload a process will "
    "pick up and process.",
    action_type="write",
    chain_callable=True,
    data_model=QueueItem,
    event="blue-prism-connector.add_queue_item",
    effects=["blue_prism.queue_item.created"],
)
async def add_queue_item(ctx, params: AddQueueItemParams) -> ActionResult:
    """Add a new item to a Work Queue."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        result = await bc.add_queue_item(ctx, token, conn["api_base_url"], params.queue_id, key_value=params.key_value, data=params.data)
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to add queue item."), code=e.payload.get("error_code", "BP_ERROR"))
    item_id = str(result.get("id", ""))
    return ActionResult.ok(
        QueueItem(id=item_id, title=params.key_value, queue_id=params.queue_id, status=result.get("status", "Pending"), attempt=0, key_value=params.key_value),
        message=f"Added item to work queue {params.queue_id}.",
    )


@chat.function(
    "set_queue_item_status",
    "Manually set a queue item's outcome to 'Completed' or 'Exception'.",
    action_type="write",
    chain_callable=True,
    data_model=QueueItem,
    event="blue-prism-connector.set_queue_item_status",
    effects=["blue_prism.queue_item.status_changed"],
)
async def set_queue_item_status(ctx, params: SetQueueItemStatusParams) -> ActionResult:
    """Set a queue item's status."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        await bc.set_queue_item_status(ctx, token, conn["api_base_url"], params.item_id, status=params.status)
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to update queue item status."), code=e.payload.get("error_code", "BP_ERROR"))
    return ActionResult.ok(
        QueueItem(id=params.item_id, title=params.item_id, queue_id="", status=params.status, attempt=0, key_value=""),
        message=f"Queue item {params.item_id} set to {params.status}.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Runtime Resources
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_resources",
    "List registered Runtime Resources in the connected Blue Prism estate "
    "-- their name, status, and resource pool.",
    action_type="read",
    chain_callable=True,
    data_model=ResourceList,
    event="blue-prism-connector.list_resources",
)
async def list_resources(ctx, params: ListResourcesParams) -> ActionResult:
    """List Runtime Resources."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        raw = await bc.list_resources(ctx, token, conn["api_base_url"])
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to list resources."), code=e.payload.get("error_code", "BP_ERROR"))
    items = [
        Resource(id=str(r.get("id", "")), title=r.get("name", ""), status=r.get("status"), pool_name=r.get("poolName", "") or "")
        for r in raw
    ]
    return ActionResult.ok(ResourceList(title="Runtime resources", items=items))


# ──────────────────────────────────────────────────────────────────────────
# Credentials (metadata only)
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "list_credentials",
    "List Credential Vault entries in the connected Blue Prism estate -- "
    "name and type only, never the secret value.",
    action_type="read",
    chain_callable=True,
    data_model=CredentialList,
    event="blue-prism-connector.list_credentials",
)
async def list_credentials(ctx, params: ListCredentialsParams) -> ActionResult:
    """List Credential Vault entries (metadata only)."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        raw = await bc.list_credentials(ctx, token, conn["api_base_url"])
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to list credentials."), code=e.payload.get("error_code", "BP_ERROR"))
    items = [
        Credential(id=str(c.get("id", "")), title=c.get("name", ""), credential_type=c.get("credentialType", "") or "",
                   expiry_date=c.get("expiryDate", "") or "")
        for c in raw
    ]
    return ActionResult.ok(CredentialList(title="Credentials", items=items))


# ──────────────────────────────────────────────────────────────────────────
# Bulk operations
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "bulk_stop_sessions",
    "Stop several running Sessions in one call, by explicit session ids. "
    "Continues past per-item failures and reports each outcome.",
    action_type="write",
    chain_callable=True,
    data_model=BulkSessionResult,
    event="blue-prism-connector.bulk_stop_sessions",
    effects=["blue_prism.session.stopped"],
)
async def bulk_stop_sessions(ctx, params: BulkSessionIdsParams) -> ActionResult:
    """Stop several sessions in one call."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    results: list[BulkSessionResultItem] = []
    succeeded = 0
    failed = 0
    for sid in params.session_ids:
        try:
            await bc.stop_session(ctx, token, conn["api_base_url"], sid, action=params.action)
            results.append(BulkSessionResultItem(id=sid, title=sid, ok=True, detail=params.action))
            succeeded += 1
        except bc.ClientFail as e:
            results.append(BulkSessionResultItem(id=sid, title=sid, ok=False, detail=e.payload.get("error", "failed")))
            failed += 1
    return ActionResult.ok(
        BulkSessionResult(title="Bulk stop sessions", items=results, succeeded=succeeded, failed=failed),
        message=f"{succeeded} succeeded, {failed} failed.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Estate audit (value-add)
# ──────────────────────────────────────────────────────────────────────────


@chat.function(
    "audit_estate",
    "Build one aggregated health report across every Runtime Resource in "
    "the connected Blue Prism estate: resource status, exception queue "
    "item counts, and running session counts.",
    action_type="read",
    chain_callable=True,
    data_model=EstateAuditReport,
    event="blue-prism-connector.audit_estate",
)
async def audit_estate(ctx, params: AuditEstateParams) -> ActionResult:
    """Build an aggregated health report for the connected estate."""
    resolved = await _get_token_and_conn(ctx, params.connection_id)
    if isinstance(resolved, ActionResult):
        return resolved
    conn, token = resolved
    try:
        resources = await bc.list_resources(ctx, token, conn["api_base_url"])
        queues = await bc.list_work_queues(ctx, token, conn["api_base_url"])
        sessions = await bc.list_sessions(ctx, token, conn["api_base_url"])
    except bc.ClientFail as e:
        return ActionResult.error(e.payload.get("error", "Failed to audit estate."), code=e.payload.get("error_code", "BP_ERROR"))

    running_by_resource: dict[str, int] = {}
    for s in sessions:
        if (s.get("status") or "").lower() == "running":
            rname = s.get("resourceName", "") or ""
            running_by_resource[rname] = running_by_resource.get(rname, 0) + 1

    total_exception_items = 0
    for q in queues:
        total_exception_items += q.get("exceptionCount", 0) or 0

    rows: list[EstateAuditRow] = []
    offline_count = 0
    for r in resources:
        status = r.get("status", "") or ""
        if status.lower() in ("offline", "disconnected", "unavailable"):
            offline_count += 1
        rname = r.get("name", "")
        rows.append(EstateAuditRow(
            id=str(r.get("id", "")), title=rname, resource_status=status,
            exception_queue_items=total_exception_items if not rows else 0,
            running_sessions=running_by_resource.get(rname, 0),
        ))

    return ActionResult.ok(
        EstateAuditReport(
            title="Blue Prism estate audit", rows=rows, total_resources=len(rows),
            offline_count=offline_count, total_exception_items=total_exception_items,
        ),
        message=f"Audited {len(rows)} resources -- {offline_count} offline, {total_exception_items} exception queue items.",
    )
