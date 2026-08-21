"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), same reasoning as UiPath Connector /
Automation Anywhere Connector / MuleSoft Connector. Blue Prism's estate
(Process Server, Runtime Resources, App Server) lives inside the USER'S
OWN infrastructure -- Imperal cannot and should not broker access to
someone else's Blue Prism estate centrally.

WHY THIS CONNECTOR TARGETS BLUE PRISM'S REST API VIA HUB + AUTHENTICATION
SERVER, AND WHY THAT IS A DOCUMENTED FRAGMENTATION RISK (same caveat class
as MuleSoft's CloudHub-only-vs-RTF split, flagged in CONNECTOR_DISCOVERY.md
2026-08-20).

Blue Prism's REST API (Process, Queues, Sessions, Resources, Work Queue
Items) is NOT exposed by the core Blue Prism Server on its own -- it
requires Blue Prism Hub plus Blue Prism Authentication Server v4.7+ to be
installed and configured (confirmed during Discovery). A user running only
classic Blue Prism Enterprise/Server without Hub has NO REST surface this
connector can reach at all; the classic integration path is the older
BPServer.exe SOAP/COM automation API, which is out of scope here. This
connector therefore explicitly targets Hub-enabled estates and documents
that requirement up front (in the connect form's help panel) rather than
silently failing for users who lack Hub.

WHY OAUTH2 CLIENT CREDENTIALS AGAINST THE AUTHENTICATION SERVER, NOT A
GENERIC PLATFORM OAUTH ENTRY.

The Authentication Server issues bearer tokens via the standard OAuth2
client_credentials grant once a Service Account / API Client is registered
in Blue Prism Hub's Authentication Server admin screens. The connector
therefore asks for the Authentication Server URL (token endpoint),
the Hub/Blue Prism API base URL, and the client_id/client_secret pair --
four required fields, same shape as UiPath's/MuleSoft's multi-field forms
(none of them fit a single token like n8n/Make.com/Slack).

WHY `write_mode="both"`, SAME REASONING AS UiPath/Automation Anywhere/
MuleSoft/n8n/Make.com/Power Automate CONNECTOR.

Declaring `write_mode="user"` would mean only the platform's generic
Secrets screen could write these -- leaving a first-time user with no
in-app screen explaining what an Authentication Server Service Account
even is or how to register one. `"both"` keeps the generic Secrets screen
as a fallback while letting `connect_blue_prism` be the friendly guided
path.

WHY SCOPE IS PER-ACCOUNT, NOT APP-LEVEL, SAME AS UiPath/Automation
Anywhere/MuleSoft/n8n/Make.com/Power Automate CONNECTOR.

A user may have multiple Blue Prism estates (e.g. dev/test/prod Hub
instances) -- credentials are stored as a list keyed by connection id, not
a single secret.
"""
from __future__ import annotations

from imperal_sdk import Extension, ChatExtension

ext = Extension(
    "blue-prism-connector",
    version="0.1.0",
    display_name="Blue Prism",
    description=(
        "Connect your own Blue Prism estate (via Blue Prism Hub + "
        "Authentication Server v4.7+) to see and manage your processes, "
        "sessions, work queues, and runtime resources from Imperal -- list "
        "processes and start/stop sessions against them, manage work queue "
        "items, browse connected runtime resources, and read credential "
        "metadata. Uses your own Authentication Server Service Account "
        "(OAuth2 client credentials) -- nothing is hosted or proxied by "
        "Imperal beyond the request itself. Requires Blue Prism Hub + "
        "Authentication Server v4.7+; classic Blue Prism Server without Hub "
        "has no REST surface this connector can reach."
    ),
    icon="icon.svg",
    capabilities=[
        "blue-prism:read",
        "blue-prism:write",
    ],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="blue_prism",
    description="Manage a connected Blue Prism estate: processes, sessions, work queues, resources, credentials.",
)

ext.secret(
    "bp_connections",
    (
        "Your connected Blue Prism estates -- stored as a JSON array, one "
        "entry per estate, each with its own Authentication Server "
        "Service Account (client_id, client_secret) and "
        "auth_server_url/api_base_url pair. Managed through "
        "connect_blue_prism / disconnect_blue_prism -- you should not "
        "need to edit this directly."
    ),
    required=True,
)


@ext.health_check
async def health_check(ctx) -> dict:
    return {"ok": True}
