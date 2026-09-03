"""Panel UI -- connections list/connect form + Processes list.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as UiPath
Connector's / Automation Anywhere Connector's / MuleSoft Connector's
panels.py).

Every section (connections, connect form, processes) is a plain ui.Stack,
content stacked vertically and left-aligned, sections separated by
ui.Divider() -- no Card border/background/shadow anywhere in this slot.
Disconnect lives only in the "App settings" screen (panels_settings.py).
The one secondary "App settings" button is always the LAST element at the
bottom of the sidebar.

WHY A FULL FORM, NOT A TOKEN LIKE n8n/Make.com/Slack.

Blue Prism's Authentication Server OAuth2 client-credentials auth needs
auth_server_url + api_base_url + client_id + client_secret -- see app.py's
module docstring for the full reasoning (Hub + Authentication Server
v4.7+ requirement, fragmentation risk vs classic Blue Prism Server-only
estates). The form therefore asks for those four required fields plus an
optional label, with a help panel (opened via
ui.Call("__panel__bp_connect_help")) explaining where to find each one and
flagging the Hub requirement up front -- the same shape as UiPath
Connector's / Automation Anywhere Connector's forms. No intro heading/
description text lives in the sidebar itself -- that walkthrough lives
ONLY in the help panel's content, per UI_INTERFACE_STANDARD.md's "no
sidebar instructions duplicating the modal" rule.

CENTER SLOT -- per ~/UI_INTERFACE_STANDARD.md, an app with no dedicated
center content needs a base (non-overlay) center panel with the canonical
"Nothing to show here" text, registered with center_overlay=True so the
session-init batch actually picks it up (same lesson learned and recorded
for UiPath/Automation Anywhere/MuleSoft/Make.com/n8n/Power Automate
Connector).
"""
from __future__ import annotations

from imperal_sdk import ui

import bp_client as bc
from app import ext
import handlers as h


def _settings_button() -> ui.UINode:
    """The one required secondary entry point into the settings screen --
    always the last element at the bottom of the sidebar."""
    return ui.Button(
        "App settings", variant="secondary", size="sm", icon="settings", on_click=ui.Call("__panel__bp_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(c.get("title") or c.get("detail", ""), variant="body"),
        ui.Text(c.get("detail", ""), variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Stack(direction="v", gap=0, children=[])
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, align="stretch", children=children)


def _process_row(p) -> ui.UINode:
    return ui.Stack(direction="v", gap=0, align="start", children=[
        ui.Text(p.title, variant="body"),
        ui.Text(p.description or "", variant="caption"),
    ])


def _processes_section(processes: list) -> ui.UINode:
    if not processes:
        return ui.Text("No processes found in this estate yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, p in enumerate(processes):
        if i > 0:
            children.append(ui.Divider())
        children.append(_process_row(p))
    return ui.Stack(direction="v", gap=2, align="stretch", children=children)


def _connect_section() -> ui.UINode:
    """Plain content, no Card wrapper. Stretched full-width per
    UI_INTERFACE_STANDARD.md. No intro heading/description text here -- the
    Authentication Server walkthrough lives ONLY in bp_connect_help's
    panel (button below opens it); repeating it here would duplicate that
    instruction."""
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm",
                  icon="HelpCircle",
                  on_click=ui.Call("__panel__bp_connect_help")),
        ui.Form(
            action="connect_blue_prism",
            submit_label="Verify and connect",
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Authentication Server URL", variant="caption"),
                    ui.Input(param_name="auth_server_url",
                              placeholder="https://yourhub.example.com/authserver"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Hub/Blue Prism API base URL", variant="caption"),
                    ui.Input(param_name="api_base_url",
                              placeholder="https://yourhub.example.com/api"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Service Account client ID", variant="caption"),
                    ui.Input(param_name="client_id",
                              placeholder="Authentication Server client ID"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Service Account client secret", variant="caption"),
                    ui.Password(param_name="client_secret",
                                 placeholder="Authentication Server client secret"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Label (optional)", variant="caption"),
                    ui.Input(param_name="label", placeholder="e.g. Production estate"),
                ]),
            ],
        ),
    ])


@ext.panel("bp_connect_help", slot="center", title="Connecting Blue Prism", center_overlay=True)
async def bp_connect_help(ctx, **kwargs) -> ui.UINode:
    return ui.Dialog(
        title="Connecting your Blue Prism estate",
        children=[
            ui.Stack(direction="v", gap=3, align="stretch", children=[
                ui.Text(
                    "Requires Blue Prism Hub + Authentication Server v4.7+. "
                    "Classic Blue Prism Server-only estates (no Hub) have no "
                    "REST API surface this connector can reach.",
                    variant="body",
                ),
                ui.Text(
                    "1. In Blue Prism Hub, open Authentication Server admin "
                    "and register a Service Account (API Client) with the "
                    "scopes you need (processes, sessions, work queues, "
                    "resources).",
                    variant="body",
                ),
                ui.Text(
                    "2. Copy the Authentication Server's token endpoint base "
                    "URL (Authentication Server URL above).",
                    variant="body",
                ),
                ui.Text(
                    "3. Copy your Hub/Blue Prism API base URL (where the "
                    "REST API is actually served).",
                    variant="body",
                ),
                ui.Text(
                    "4. Copy the Service Account's client ID and client "
                    "secret into the form.",
                    variant="body",
                ),
            ]),
        ],
    )


@ext.panel("bp_center", slot="center", title="Blue Prism", icon="🔗", center_overlay=True)
async def bp_center_panel(ctx, **kwargs) -> ui.UINode:
    """Post-connect main screen: an estate audit (resources/exceptions)
    plus recent sessions -- gives a real operational picture instead of
    the previous empty placeholder."""
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Empty(message="Connect a Blue Prism estate from the sidebar to see it here.", icon="🔗")

    from schemas import AuditEstateParams, ListSessionsParams
    conn_id = connections[0].get("id", "")
    body: list[ui.UINode] = [ui.Text("Estate audit", variant="subtitle")]
    audit_result = await h.audit_estate(ctx, AuditEstateParams(connection_id=conn_id))
    if audit_result.success and audit_result.data:
        r = audit_result.data
        body.append(ui.Stats(children=[
            ui.Stat(label="Resources", value=str(r.total_resources)),
            ui.Stat(label="Offline", value=str(r.offline_count)),
            ui.Stat(label="Exception items", value=str(r.total_exception_items)),
        ]))
        for row in r.rows[:15]:
            color = "red" if row.exception_queue_items > 0 else ("yellow" if row.running_sessions > 0 else "green")
            body.append(ui.Stack(direction="h", gap=2, align="center", children=[
                ui.Badge(label=row.resource_status or "UNKNOWN", color=color),
                ui.Text(row.title, variant="body"),
                ui.Text(f"running: {row.running_sessions} · exceptions: {row.exception_queue_items}", variant="caption"),
            ]))
    else:
        body.append(ui.Text("Could not load the estate audit.", variant="caption"))

    body.append(ui.Divider())
    body.append(ui.Text("Recent sessions", variant="subtitle"))
    sessions_result = await h.list_sessions(ctx, ListSessionsParams(connection_id=conn_id))
    if sessions_result.success and sessions_result.data and sessions_result.data.items:
        for s in sessions_result.data.items[:15]:
            color = {"Failed": "red", "Running": "yellow", "Completed": "green"}.get(s.status or "", "gray")
            body.append(ui.Stack(direction="h", gap=2, align="center", children=[
                ui.Badge(label=s.status or "UNKNOWN", color=color),
                ui.Text(s.title or s.process_name, variant="body"),
                ui.Text(s.resource_name, variant="caption"),
            ]))
    else:
        body.append(ui.Text("No recent sessions.", variant="caption"))

    return ui.Stack(direction="v", gap=3, align="stretch", children=body)


@ext.panel("bp_connect", slot="left", title="Blue Prism", icon="🔗",
           default_width=320, min_width=260, max_width=420)
async def bp_connect_panel(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    connected = bool(connections)

    header = ui.Header(text="Blue Prism", level=2,
                        subtitle="Manage your Blue Prism estate's processes, sessions and queues from Imperal")

    if not connected:
        return ui.Stack(direction="v", gap=4, align="stretch", children=[
            header,
            _connect_section(),
            ui.Divider(),
            _settings_button(),
        ])

    processes: list = []
    first = connections[0]
    try:
        tok = await bc.get_access_token(ctx, first["auth_server_url"], first["client_id"], first["client_secret"])
        if tok.get("ok"):
            raw = await bc.list_processes(ctx, tok["access_token"], first["api_base_url"])
            from schemas import Process
            processes = [
                Process(id=str(p.get("id", "")), title=p.get("name", ""),
                        description=p.get("description", "") or "")
                for p in raw
            ]
    except bc.ClientFail:
        processes = []

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        header,
        ui.Text("Connected estates", variant="subtitle"),
        _connections_section(connections),
        ui.Divider(),
        _connect_section(),
        ui.Divider(),
        ui.Text(f"Processes -- {first.get('label') or first.get('api_base_url', '')}", variant="subtitle"),
        _processes_section(processes),
        ui.Divider(),
        ui.Button("View estate dashboard", variant="primary", size="sm", icon="LayoutDashboard", on_click=ui.Call("__panel__bp_center")),
        ui.Divider(),
        _settings_button(),
    ])
