"""Pydantic params models + SDL entity contracts for Blue Prism Connector.

All params models are module-scope (V17 federal invariant, same rule as
UiPath Connector / Automation Anywhere Connector / MuleSoft Connector's
schemas.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────


class ConnectBluePrismParams(BaseModel):
    auth_server_url: str = Field(
        "", description="Your Blue Prism Authentication Server URL, e.g. https://yourhub.example.com/authserver",
    )
    api_base_url: str = Field(
        "", description="Your Blue Prism Hub/API base URL, e.g. https://yourhub.example.com/api",
    )
    client_id: str = Field("", description="Authentication Server Service Account client ID.")
    client_secret: str = Field("", description="Authentication Server Service Account client secret.")
    label: str = Field("", description="Optional friendly name for this Blue Prism estate connection.")


class ProviderConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""
    api_base_url: str = ""


class ProviderConnectionList(sdl.Entity):
    id: str = "provider_connection_list"
    title: str = ""
    items: list[ProviderConnection] = Field(default_factory=list)


class DisconnectBluePrismParams(BaseModel):
    connection_id: str = Field(..., description="Connection id to disconnect, from list_connections.")


class DeleteResult(sdl.Entity):
    id: str = ""
    title: str = ""
    ok: bool = False


# ──────────────────────────────────────────────────────────────────────────
# Processes
# ──────────────────────────────────────────────────────────────────────────


class ListProcessesParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")


class Process(sdl.Entity):
    id: str = ""
    title: str = ""
    description: str = ""
    is_published: bool = False


class ProcessList(sdl.Entity):
    id: str = "process_list"
    title: str = ""
    items: list[Process] = Field(default_factory=list)


class GetProcessParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")
    process_id: str = Field(..., description="Process id, from list_processes.")


# ──────────────────────────────────────────────────────────────────────────
# Sessions (process runs)
# ──────────────────────────────────────────────────────────────────────────


class ListSessionsParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")
    process_id: str = Field("", description="Optional process id to filter sessions to.")


class Session(sdl.Entity):
    id: str = ""
    title: str = ""
    status: str | None = None
    process_name: str = ""
    resource_name: str = ""
    start_datetime: str = ""
    end_datetime: str = ""


class SessionList(sdl.Entity):
    id: str = "session_list"
    title: str = ""
    items: list[Session] = Field(default_factory=list)


class GetSessionParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")
    session_id: str = Field(..., description="Session id, from list_sessions.")


class StartSessionParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")
    process_id: str = Field(..., description="Process id to run, from list_processes.")
    resource_ids: list[str] | None = Field(None, description="Explicit runtime resource ids to run on. Omit to let Blue Prism pick.")
    inputs: dict | None = Field(None, description="Optional input parameters for the process.")


class StopSessionParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")
    session_id: str = Field(..., description="Session id to stop, from list_sessions.")
    action: str = Field("stop", description="'stop' for graceful stop, 'terminate' to force-kill immediately.")


class SessionActionResult(sdl.Entity):
    id: str = ""
    title: str = ""
    ok: bool = False
    detail: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Work Queues + queue items
# ──────────────────────────────────────────────────────────────────────────


class ListWorkQueuesParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")


class WorkQueue(sdl.Entity):
    id: str = ""
    title: str = ""
    key_field: str = ""
    max_attempts: int = 0
    pending_count: int = 0


class WorkQueueList(sdl.Entity):
    id: str = "work_queue_list"
    title: str = ""
    items: list[WorkQueue] = Field(default_factory=list)


class ListQueueItemsParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")
    queue_id: str = Field(..., description="Work queue id, from list_work_queues.")
    status: str = Field("", description="Optional status filter, e.g. 'Pending', 'Locked', 'Completed', 'Exception'.")


class QueueItem(sdl.Entity):
    id: str = ""
    title: str = ""
    queue_id: str = ""
    status: str | None = None
    attempt: int = 0
    key_value: str = ""


class QueueItemList(sdl.Entity):
    id: str = "queue_item_list"
    title: str = ""
    items: list[QueueItem] = Field(default_factory=list)


class AddQueueItemParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")
    queue_id: str = Field(..., description="Work queue id to add the item to, from list_work_queues.")
    key_value: str = Field(..., description="The queue item's key value (its unique business identifier).")
    data: dict | None = Field(None, description="Optional item data fields.")


class SetQueueItemStatusParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")
    item_id: str = Field(..., description="Queue item id, from list_queue_items.")
    status: str = Field(..., description="New status: 'Completed' or 'Exception'.")


# ──────────────────────────────────────────────────────────────────────────
# Runtime Resources
# ──────────────────────────────────────────────────────────────────────────


class ListResourcesParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")


class Resource(sdl.Entity):
    id: str = ""
    title: str = ""
    status: str | None = None
    pool_name: str = ""


class ResourceList(sdl.Entity):
    id: str = "resource_list"
    title: str = ""
    items: list[Resource] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Credentials (metadata only, never secrets)
# ──────────────────────────────────────────────────────────────────────────


class ListCredentialsParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")


class Credential(sdl.Entity):
    id: str = ""
    title: str = ""
    credential_type: str = ""
    expiry_date: str = ""


class CredentialList(sdl.Entity):
    id: str = "credential_list"
    title: str = ""
    items: list[Credential] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────
# Bulk operations
# ──────────────────────────────────────────────────────────────────────────


class BulkSessionResultItem(sdl.Entity):
    id: str = ""
    title: str = ""
    ok: bool = False
    detail: str = ""


class BulkSessionResult(sdl.Entity):
    id: str = "bulk_session_result"
    title: str = ""
    items: list[BulkSessionResultItem] = Field(default_factory=list)
    succeeded: int = 0
    failed: int = 0


class BulkSessionIdsParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")
    session_ids: list[str] = Field(..., description="Explicit session ids to act on.")
    action: str = Field("stop", description="'stop' for graceful stop, 'terminate' to force-kill immediately.")


# ──────────────────────────────────────────────────────────────────────────
# Estate audit (value-add)
# ──────────────────────────────────────────────────────────────────────────


class AuditEstateParams(BaseModel):
    connection_id: str = Field("", description="Which connected estate to use. Omit if only one is connected.")


class EstateAuditRow(sdl.Entity):
    id: str = ""
    title: str = ""
    resource_status: str = ""
    exception_queue_items: int = 0
    running_sessions: int = 0


class EstateAuditReport(sdl.Entity):
    id: str = "estate_audit_report"
    title: str = ""
    rows: list[EstateAuditRow] = Field(default_factory=list)
    total_resources: int = 0
    offline_count: int = 0
    total_exception_items: int = 0
