from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib import error, parse, request

from nicegui import run, ui
from nicegui.elements.button import Button

from personal_context_mcp.models.enums import MemoryType
from personal_context_mcp.services.dependencies import get_auth_service

DEFAULT_API_BASE_URL = os.getenv("DASHBOARD_API_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_API_TIMEOUT_SECONDS = 5


def _normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def _validate_api_base_url(value: str) -> str:
    normalized = _normalize_base_url(value.strip())
    parsed = parse.urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Enter a complete URL such as http://127.0.0.1:8000.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError(
            "Enter only the API root URL, for example http://127.0.0.1:8000. "
            "Do not add /profile or another endpoint."
        )
    return parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _format_timestamp(value: str | datetime | None) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M UTC")
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return str(value)


def _request_json(
    method: str,
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> Any:
    url = f"{_normalize_base_url(base_url)}{path}"
    if query:
        params: list[tuple[str, str]] = []
        for key, value in query.items():
            if value is None:
                continue
            if isinstance(value, list):
                params.extend((key, str(item)) for item in value)
            else:
                params.append((key, str(value)))
        if params:
            url = f"{url}?{parse.urlencode(params)}"

    body = None
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    api_request = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(api_request, timeout=DEFAULT_API_TIMEOUT_SECONDS) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{exc.code} {exc.reason}: {detail}") from exc
    except TimeoutError as exc:
        raise RuntimeError(
            f"API request timed out after {DEFAULT_API_TIMEOUT_SECONDS} seconds: {url}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach API at {url}: {exc.reason}") from exc


class Dashboard:
    def __init__(self) -> None:
        self.base_url = ""
        self.api_key = ""
        self.connected = False
        self.memories: list[dict[str, Any]] = []
        self.profile: dict[str, Any] = {}
        self.work_style: dict[str, Any] = {}
        self.users: list[dict[str, Any]] | None = None
        self.generated_key = ""
        self.memories_loaded = False
        self.memories_loading = False
        self.work_style_loaded = False
        self.work_style_loading = False

    @staticmethod
    async def _run_with_loader(
        button: Button,
        idle_text: str,
        loading_text: str,
        action: Callable[[], Awaitable[Any]],
    ) -> Any:
        button.disable()
        button.props("loading")
        button.set_text(loading_text)
        try:
            return await action()
        finally:
            try:
                button.props(remove="loading")
                button.set_text(idle_text)
                button.enable()
            except RuntimeError:
                # A successful action may refresh the section containing this button.
                pass

    def build(self) -> None:
        ui.colors(
            primary="#4f46e5",
            secondary="#64748b",
            accent="#0ea5e9",
            positive="#16a34a",
            negative="#dc2626",
        )
        ui.add_css(
            """
            :root {
                --pc-bg: #f8fafc;
                --pc-surface: #ffffff;
                --pc-border: #e2e8f0;
                --pc-text: #0f172a;
                --pc-muted: #64748b;
                --pc-primary: #4f46e5;
                --pc-primary-soft: #eef2ff;
            }
            body {
                background: var(--pc-bg);
                color: var(--pc-text);
                font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
            }
            .q-layout, .q-page-container { background: var(--pc-bg); }
            .pc-header {
                height: 64px;
                background: rgba(255, 255, 255, .96);
                color: var(--pc-text);
                border-bottom: 1px solid var(--pc-border);
                box-shadow: none;
                backdrop-filter: blur(12px);
            }
            .pc-brand-mark {
                width: 36px;
                height: 36px;
                border-radius: 11px;
                background: linear-gradient(135deg, #4f46e5, #7c3aed);
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 800;
                letter-spacing: -.04em;
            }
            .pc-page {
                width: 100%;
                max-width: 1440px;
                margin: 0 auto;
                padding: 28px 32px 48px;
                gap: 20px;
            }
            .pc-card {
                background: var(--pc-surface);
                border: 1px solid var(--pc-border);
                border-radius: 16px;
                box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
                padding: 20px;
            }
            .pc-card:hover {
                box-shadow: 0 8px 24px rgba(15, 23, 42, .06);
            }
            .pc-panel {
                background: var(--pc-surface);
                border: 1px solid var(--pc-border);
                border-radius: 18px;
                overflow: hidden;
            }
            .pc-stat {
                min-height: 104px;
                padding: 18px 20px;
                background: var(--pc-surface);
                border: 1px solid var(--pc-border);
                border-radius: 14px;
            }
            .pc-muted { color: var(--pc-muted); }
            .pc-kicker {
                color: var(--pc-primary);
                font-size: 12px;
                font-weight: 700;
                letter-spacing: .08em;
                text-transform: uppercase;
            }
            .pc-empty {
                width: 100%;
                min-height: 210px;
                border: 1px dashed #cbd5e1;
                border-radius: 16px;
                background: #fff;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
                padding: 32px;
            }
            .pc-user-row {
                padding: 16px 18px;
                border: 1px solid var(--pc-border);
                border-radius: 14px;
                background: #fff;
            }
            .pc-badge {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 700;
            }
            .pc-badge-success { color: #166534; background: #dcfce7; }
            .pc-badge-muted { color: #475569; background: #f1f5f9; }
            .pc-badge-primary { color: #4338ca; background: #eef2ff; }
            .pc-drawer {
                background: #0f172a;
                color: #e2e8f0;
                border-right: 0;
            }
            .pc-drawer .q-drawer__content { padding: 18px; }
            .pc-drawer .q-field__control {
                min-height: 44px;
                background: #fff;
                border-radius: 10px;
            }
            .pc-drawer .q-field__native,
            .pc-drawer .q-field__input { color: #0f172a !important; }
            .pc-drawer .q-field__label { color: #64748b !important; }
            .pc-drawer .q-field__append { color: #475569 !important; }
            .pc-tabs {
                min-height: 54px;
                background: #fff;
                border: 1px solid var(--pc-border);
                border-radius: 14px;
                padding: 5px;
            }
            .pc-tabs .q-tab {
                min-height: 42px;
                border-radius: 10px;
                color: #64748b;
                font-weight: 700;
                letter-spacing: 0;
            }
            .pc-tabs .q-tab--active {
                color: #4338ca;
                background: var(--pc-primary-soft);
            }
            .pc-tabs .q-tab__indicator { display: none; }
            .pc-panels, .pc-panels .q-panel, .pc-panels .q-tab-panel {
                background: transparent;
            }
            .pc-panels .q-tab-panel { padding: 20px 0 0; }
            .q-field--outlined .q-field__control {
                border-radius: 10px;
                background: #fff;
            }
            .q-field--dense .q-field__control,
            .q-field--dense .q-field__marginal { min-height: 42px; height: 42px; }
            .q-textarea.q-field--dense .q-field__control { height: auto; }
            .q-btn {
                min-height: 40px;
                border-radius: 10px;
                font-weight: 700;
                letter-spacing: 0;
                box-shadow: none;
            }
            .q-expansion-item {
                border: 1px solid var(--pc-border);
                border-radius: 14px;
                background: #fff;
                overflow: hidden;
            }
            .q-expansion-item__container > .q-item { min-height: 54px; }
            @media (max-width: 900px) {
                .pc-page { padding: 20px 16px 36px; }
                .pc-desktop-only { display: none; }
            }
            """
        )

        with ui.header().classes("pc-header items-center px-5"):
            with ui.row().classes("items-center gap-3"):
                ui.html('<div class="pc-brand-mark">PC</div>')
                with ui.column().classes("gap-0"):
                    ui.label("Personal Context").classes("text-base font-bold leading-tight")
                    ui.label("MCP Dashboard").classes("text-xs pc-muted leading-tight")
            ui.space()
            with ui.row().classes("items-center gap-2 pc-desktop-only"):
                ui.icon("bolt", color="primary").classes("text-lg")
                ui.label("Fast local console").classes("text-sm pc-muted")

        with (
            ui.left_drawer(value=True)
            .classes("pc-drawer")
            .props("width=292 breakpoint=780 bordered")
        ):
            self.render_connection()

        with ui.column().classes("pc-page"):
            with ui.row().classes("w-full items-end justify-between gap-4"):
                with ui.column().classes("gap-1"):
                    ui.label("Workspace").classes("pc-kicker")
                    ui.label("Personal Context MCP").classes("text-3xl font-bold tracking-tight")
                    ui.label("Manage agent memory, preferences, outcomes, and access.").classes(
                        "pc-muted text-sm"
                    )
                self.render_header_status()

            self.render_summary_cards()

            with ui.tabs(on_change=self._handle_tab_change).classes("pc-tabs w-full") as tabs:
                memory_tab = ui.tab("memories", "Memories", icon="psychology")
                profile_tab = ui.tab("profile", "Profile & Style", icon="tune")
                users_tab = ui.tab("users", "Users", icon="group")

            with ui.tab_panels(tabs, value=memory_tab).classes("pc-panels w-full"):
                with ui.tab_panel(memory_tab):
                    self.render_memories_tab()
                with ui.tab_panel(profile_tab):
                    self.render_profile_tab()
                with ui.tab_panel(users_tab):
                    self.render_users_tab()

        self._build_key_dialog()

    @ui.refreshable
    def render_header_status(self) -> None:
        if self.connected:
            with ui.row().classes("items-center gap-2"):
                ui.html('<span class="pc-badge pc-badge-success">Connected</span>')
                ui.label(self.base_url).classes("pc-muted text-xs")
        else:
            ui.html('<span class="pc-badge pc-badge-muted">Not connected</span>')

    @ui.refreshable
    def render_summary_cards(self) -> None:
        memory_count = str(len(self.memories)) if self.memories_loaded else "Not loaded"
        user_count = len(self.users) if self.users is not None else 0
        cards = [
            ("Memories", memory_count, "psychology", "#4f46e5"),
            ("Profile", "Ready" if self.profile else "Empty", "person", "#0ea5e9"),
            (
                "Work style",
                "Ready" if self.work_style_loaded else "Not loaded",
                "tune",
                "#8b5cf6",
            ),
            ("API users", str(user_count), "group", "#16a34a"),
        ]
        with ui.row().classes("w-full gap-4 flex-wrap"):
            for label, value, icon, color in cards:
                with ui.row().classes("pc-stat grow min-w-[210px] items-center gap-4"):
                    with (
                        ui.element("div")
                        .classes("w-11 h-11 rounded-xl flex items-center justify-center")
                        .style(f"background: {color}14; color: {color}")
                    ):
                        ui.icon(icon).classes("text-2xl")
                    with ui.column().classes("gap-0"):
                        ui.label(label).classes("pc-muted text-xs font-semibold")
                        ui.label(value).classes("text-xl font-bold")

    @ui.refreshable
    def render_connection(self) -> None:
        with ui.row().classes("items-center gap-3 mb-4"):
            with ui.element("div").classes(
                "w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center"
            ):
                ui.icon("hub").classes("text-indigo-300 text-xl")
            with ui.column().classes("gap-0"):
                ui.label("API Connection").classes("text-base font-bold text-white")
                ui.label("Secure dashboard access").classes("text-xs text-slate-400")

        if self.connected:
            with ui.card().classes(
                "w-full bg-slate-800 border border-slate-700 rounded-xl p-4 shadow-none"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check_circle").classes("text-green-400")
                    ui.label("Connected").classes("font-bold text-green-300")
                ui.label(self.base_url).classes("text-xs text-slate-400 break-all")
            disconnect_button = ui.button(
                "Disconnect",
                icon="link_off",
            ).props("outline color=grey-4").classes("w-full mt-3")
            disconnect_button.on_click(
                lambda: self._run_with_loader(
                    disconnect_button,
                    "Disconnect",
                    "Disconnecting...",
                    self.disconnect,
                )
            )
            return

        ui.label("Server details").classes(
            "text-xs font-bold uppercase tracking-wider text-slate-400 mb-1"
        )
        url_input = (
            ui.input("API base URL", value=DEFAULT_API_BASE_URL)
            .props("outlined dense")
            .classes("w-full")
        )
        key_input = (
            ui.input(
                "API key",
                password=True,
                password_toggle_button=True,
            )
            .props("outlined dense")
            .classes("w-full")
        )
        ui.label("Use only the API root URL, without /profile or another endpoint.").classes(
            "text-xs text-slate-400 leading-relaxed"
        )
        connect_button = ui.button(
            "Connect",
            icon="link",
        ).classes("w-full mt-2")
        connect_button.on_click(
            lambda: self._run_with_loader(
                connect_button,
                "Connect",
                "Connecting...",
                lambda: self.connect(
                    str(url_input.value),
                    str(key_input.value or ""),
                ),
            )
        )

    async def connect(self, entered_url: str, entered_key: str) -> None:
        try:
            base_url = _validate_api_base_url(entered_url)
            api_key = entered_key.strip()
            health, profile = await run.io_bound(
                self._validate_connection,
                base_url,
                api_key,
            )
        except (RuntimeError, ValueError) as exc:
            ui.notify(f"Connection failed: {exc}", type="negative", timeout=8000)
            return

        self.base_url = base_url
        self.api_key = api_key
        self.profile = profile or {}
        self.work_style = {}
        self.memories = []
        self.memories_loaded = False
        self.work_style_loaded = False
        self.connected = True
        ui.notify(f"Connected. API status: {health.get('status', 'unknown')}", type="positive")
        self._refresh_api_views()

    @staticmethod
    def _validate_connection(
        base_url: str,
        api_key: str,
    ) -> tuple[dict[str, Any], Any]:
        health = _request_json("GET", base_url, "/health")
        profile = _request_json("GET", base_url, "/profile", api_key=api_key or None)
        return health, profile

    async def disconnect(self) -> None:
        await asyncio.sleep(0.2)
        self.base_url = ""
        self.api_key = ""
        self.connected = False
        self.memories = []
        self.profile = {}
        self.work_style = {}
        self.memories_loaded = False
        self.memories_loading = False
        self.work_style_loaded = False
        self.work_style_loading = False
        self._refresh_api_views()

    async def _handle_tab_change(self, event: Any) -> None:
        if not self.connected:
            return
        if event.value == "memories":
            await self._load_memories_once()
        elif event.value == "profile":
            await self._load_work_style_once()

    async def _load_memories_once(self) -> None:
        if self.memories_loaded or self.memories_loading:
            return
        self.memories_loading = True
        self.render_memories_tab.refresh()
        try:
            await self.refresh_memories()
        finally:
            self.memories_loading = False
            self.render_memories_tab.refresh()

    async def _load_work_style_once(self) -> None:
        if self.work_style_loaded or self.work_style_loading:
            return
        self.work_style_loading = True
        self.render_profile_tab.refresh()
        try:
            self.work_style = (
                await run.io_bound(
                    _request_json,
                    "GET",
                    self.base_url,
                    "/work-style",
                    None,
                    None,
                    self.api_key or None,
                )
                or {}
            )
            self.work_style_loaded = True
            self.render_summary_cards.refresh()
        except RuntimeError as exc:
            ui.notify(str(exc), type="negative")
        finally:
            self.work_style_loading = False
            self.render_profile_tab.refresh()

    def _refresh_api_views(self) -> None:
        self.render_connection.refresh()
        self.render_header_status.refresh()
        self.render_summary_cards.refresh()
        self.render_memories_tab.refresh()
        self.render_profile_tab.refresh()

    @staticmethod
    def _render_empty_state(icon: str, title: str, description: str) -> None:
        with ui.column().classes("pc-empty gap-2"):
            ui.icon(icon).classes("text-4xl text-slate-300")
            ui.label(title).classes("text-base font-bold")
            ui.label(description).classes("pc-muted text-sm max-w-md")

    @staticmethod
    def _render_section_header(
        eyebrow: str,
        title: str,
        description: str,
    ) -> None:
        with ui.column().classes("gap-1"):
            ui.label(eyebrow).classes("pc-kicker")
            ui.label(title).classes("text-2xl font-bold tracking-tight")
            ui.label(description).classes("pc-muted text-sm")

    @ui.refreshable
    def render_memories_tab(self) -> None:
        if not self.connected:
            self._render_empty_state(
                "cloud_off",
                "Connect your API",
                "Add the API root URL and key in the sidebar to load and manage memories.",
            )
            return
        if self.memories_loading:
            with ui.column().classes("pc-empty gap-3"):
                ui.spinner("dots", size="42px", color="primary")
                ui.label("Loading memories...").classes("text-base font-bold")
                ui.label("Retrieving recent context from the API.").classes("pc-muted text-sm")
            return
        if not self.memories_loaded:
            with ui.column().classes("pc-empty gap-3"):
                ui.icon("psychology").classes("text-4xl text-slate-300")
                ui.label("Memories are not loaded").classes("text-base font-bold")
                ui.label(
                    "Open this tab after connecting or load the data manually."
                ).classes("pc-muted text-sm")
                load_button = ui.button("Load memories", icon="download")
                load_button.on_click(
                    lambda: self._run_with_loader(
                        load_button,
                        "Load memories",
                        "Loading...",
                        self._load_memories_once,
                    )
                )
            return

        with ui.row().classes("w-full items-start gap-5 flex-wrap"):
            with ui.column().classes("grow min-w-[480px] gap-4"):
                with ui.row().classes("w-full items-center"):
                    self._render_section_header(
                        "Knowledge base",
                        "Recent Memories",
                        "The latest context stored for this API user.",
                    )
                    ui.space()
                    refresh_button = ui.button(
                        "Refresh",
                        icon="refresh",
                    ).props("outline")
                    refresh_button.on_click(
                        lambda: self._run_with_loader(
                            refresh_button,
                            "Refresh",
                            "Refreshing...",
                            self.refresh_memories,
                        )
                    )

                if not self.memories:
                    self._render_empty_state(
                        "psychology",
                        "No memories yet",
                        "Create the first memory using the form on the right.",
                    )
                for memory in self.memories:
                    with ui.card().classes("pc-card w-full"):
                        with ui.row().classes("w-full items-start"):
                            with ui.column().classes("grow gap-1"):
                                ui.label(memory.get("title", "Untitled")).classes(
                                    "text-base font-bold"
                                )
                                ui.label(_format_timestamp(memory.get("created_at"))).classes(
                                    "pc-muted text-xs"
                                )
                            ui.html(
                                '<span class="pc-badge pc-badge-primary">'
                                f"{memory.get('memory_type', 'note')}</span>"
                            )
                        ui.label(memory.get("content", "")).classes("whitespace-pre-wrap")
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("star").classes("text-amber-500 text-sm")
                            ui.label(f"Importance {memory.get('importance', 1)}").classes(
                                "pc-muted text-xs"
                            )
                            tags = ", ".join(memory.get("tags", [])) or "No tags"
                            ui.label(tags).classes("pc-muted text-xs")

                self._render_context_card()

            with ui.column().classes("w-[390px] max-w-full gap-4"):
                self._render_memory_form()
                self._render_task_outcome_form()

    async def refresh_memories(self) -> None:
        try:
            self.memories = await run.io_bound(
                _request_json,
                "GET",
                self.base_url,
                "/memories/recent",
                None,
                {"limit": 10},
                self.api_key or None,
            )
        except RuntimeError as exc:
            ui.notify(str(exc), type="negative")
            return
        self.memories_loaded = True
        self.render_summary_cards.refresh()
        self.render_memories_tab.refresh()

    def _render_context_card(self) -> None:
        with ui.card().classes("pc-card w-full"):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-10 h-10 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center"
                ):
                    ui.icon("travel_explore").classes("text-xl")
                with ui.column().classes("gap-0"):
                    ui.label("Relevant Context").classes("text-base font-bold")
                    ui.label("Preview the context an agent receives.").classes("pc-muted text-xs")
            query = (
                ui.textarea("What should the agent know?")
                .props("outlined dense rows=3")
                .classes("w-full")
            )
            ui.label("Result limit").classes("pc-muted text-xs font-semibold")
            limit = ui.slider(min=1, max=25, value=5).props("label-always")
            result = ui.column().classes("w-full")

            async def fetch_context() -> None:
                try:
                    context = await run.io_bound(
                        _request_json,
                        "POST",
                        self.base_url,
                        "/context",
                        {"query": query.value or "", "limit": int(limit.value)},
                        None,
                        self.api_key or None,
                    )
                except RuntimeError as exc:
                    ui.notify(str(exc), type="negative")
                    return
                result.clear()
                with result:
                    ui.label("Summary").classes("font-bold")
                    ui.label(context.get("context_summary", "")).classes("whitespace-pre-wrap")
                    with ui.expansion("Raw response", icon="data_object").classes("w-full"):
                        ui.code(json.dumps(context, indent=2))

            fetch_button = ui.button(
                "Fetch Context",
                icon="search",
            ).classes("w-full")
            fetch_button.on_click(
                lambda: self._run_with_loader(
                    fetch_button,
                    "Fetch Context",
                    "Fetching...",
                    fetch_context,
                )
            )

    def _render_memory_form(self) -> None:
        with ui.card().classes("pc-card w-full"):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 "
                    "flex items-center justify-center"
                ):
                    ui.icon("add_notes").classes("text-xl")
                with ui.column().classes("gap-0"):
                    ui.label("Add Memory").classes("text-base font-bold")
                    ui.label("Store reusable context for future tasks.").classes("pc-muted text-xs")
            title = ui.input("Title").props("outlined dense").classes("w-full")
            content = ui.textarea("Content").props("outlined dense rows=4").classes("w-full")
            memory_type = (
                ui.select(
                    [item.value for item in MemoryType],
                    value=MemoryType.NOTE.value,
                    label="Type",
                )
                .props("outlined dense")
                .classes("w-full")
            )
            tags = ui.input("Tags (comma-separated)").props("outlined dense").classes("w-full")
            source = ui.input("Source").props("outlined dense").classes("w-full")
            ui.label("Importance").classes("pc-muted text-xs font-semibold")
            importance = ui.slider(min=1, max=5, value=1).props("label-always")

            async def save() -> None:
                payload = {
                    "title": title.value or "",
                    "content": content.value or "",
                    "memory_type": memory_type.value,
                    "tags": _split_csv(tags.value or ""),
                    "source": source.value or None,
                    "importance": int(importance.value),
                }
                try:
                    await run.io_bound(
                        _request_json,
                        "POST",
                        self.base_url,
                        "/memories",
                        payload,
                        None,
                        self.api_key or None,
                    )
                except RuntimeError as exc:
                    ui.notify(str(exc), type="negative")
                    return
                ui.notify("Memory saved.", type="positive")
                await self.refresh_memories()

            save_button = ui.button("Save Memory", icon="save").classes("w-full")
            save_button.on_click(
                lambda: self._run_with_loader(
                    save_button,
                    "Save Memory",
                    "Saving...",
                    save,
                )
            )

    def _render_task_outcome_form(self) -> None:
        with ui.card().classes("pc-card w-full"):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-10 h-10 rounded-xl bg-violet-50 text-violet-600 "
                    "flex items-center justify-center"
                ):
                    ui.icon("task_alt").classes("text-xl")
                with ui.column().classes("gap-0"):
                    ui.label("Task Outcome").classes("text-base font-bold")
                    ui.label("Capture what worked and what changed.").classes("pc-muted text-xs")
            task_summary = (
                ui.textarea("Task summary").props("outlined dense rows=3").classes("w-full")
            )
            final_solution = (
                ui.textarea("Final solution").props("outlined dense rows=3").classes("w-full")
            )
            decisions = (
                ui.input("Decisions (comma-separated)").props("outlined dense").classes("w-full")
            )
            mistakes = (
                ui.input("Mistakes (comma-separated)").props("outlined dense").classes("w-full")
            )
            corrections = (
                ui.input("Corrections (comma-separated)").props("outlined dense").classes("w-full")
            )
            learned = (
                ui.input("Learned preferences (comma-separated)")
                .props("outlined dense")
                .classes("w-full")
            )
            source = ui.input("Source").props("outlined dense").classes("w-full")

            async def save() -> None:
                payload = {
                    "task_summary": task_summary.value or "",
                    "final_solution": final_solution.value or None,
                    "decisions": _split_csv(decisions.value or ""),
                    "mistakes": _split_csv(mistakes.value or ""),
                    "corrections": _split_csv(corrections.value or ""),
                    "learned_preferences": _split_csv(learned.value or ""),
                    "source": source.value or None,
                }
                try:
                    await run.io_bound(
                        _request_json,
                        "POST",
                        self.base_url,
                        "/task-outcomes",
                        payload,
                        None,
                        self.api_key or None,
                    )
                except RuntimeError as exc:
                    ui.notify(str(exc), type="negative")
                    return
                ui.notify("Task outcome saved.", type="positive")

            save_button = ui.button("Save Outcome", icon="save").classes("w-full")
            save_button.on_click(
                lambda: self._run_with_loader(
                    save_button,
                    "Save Outcome",
                    "Saving...",
                    save,
                )
            )

    @ui.refreshable
    def render_profile_tab(self) -> None:
        if not self.connected:
            self._render_empty_state(
                "manage_accounts",
                "Profile unavailable",
                "Connect to the API to edit the user profile and working preferences.",
            )
            return

        self._render_section_header(
            "Personalization",
            "Profile & Work Style",
            "Control how agents understand the user and collaborate on tasks.",
        )
        with ui.row().classes("w-full items-start gap-5 flex-wrap"):
            self._render_profile_form()
            if self.work_style_loading:
                with ui.column().classes("pc-card grow min-w-[420px] items-center gap-3 py-16"):
                    ui.spinner("dots", size="42px", color="primary")
                    ui.label("Loading work style...").classes("font-bold")
            elif not self.work_style_loaded:
                with ui.column().classes("pc-card grow min-w-[420px] items-center gap-3 py-16"):
                    ui.icon("tune").classes("text-4xl text-slate-300")
                    ui.label("Work style is not loaded").classes("font-bold")
                    load_button = ui.button("Load work style", icon="download")
                    load_button.on_click(
                        lambda: self._run_with_loader(
                            load_button,
                            "Load work style",
                            "Loading...",
                            self._load_work_style_once,
                        )
                    )
            else:
                self._render_work_style_form()

    def _render_profile_form(self) -> None:
        profile = self.profile
        with ui.card().classes("pc-card grow min-w-[420px]"):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center"
                ):
                    ui.icon("person").classes("text-xl")
                with ui.column().classes("gap-0"):
                    ui.label("Profile").classes("text-base font-bold")
                    ui.label("Identity, skills, and communication preferences.").classes(
                        "pc-muted text-xs"
                    )
            fields = {
                "name": ui.input("Name", value=profile.get("name") or "")
                .props("outlined dense")
                .classes("w-full"),
                "role": ui.input("Role", value=profile.get("role") or "")
                .props("outlined dense")
                .classes("w-full"),
                "primary_skills": ui.input(
                    "Primary skills",
                    value=", ".join(profile.get("primary_skills", [])),
                )
                .props("outlined dense")
                .classes("w-full"),
                "preferred_languages": ui.input(
                    "Languages",
                    value=", ".join(profile.get("preferred_languages", [])),
                )
                .props("outlined dense")
                .classes("w-full"),
                "preferred_frameworks": ui.input(
                    "Frameworks",
                    value=", ".join(profile.get("preferred_frameworks", [])),
                )
                .props("outlined dense")
                .classes("w-full"),
                "preferred_explanation_style": ui.input(
                    "Explanation style",
                    value=profile.get("preferred_explanation_style") or "",
                )
                .props("outlined dense")
                .classes("w-full"),
                "preferred_code_style": ui.input(
                    "Code style",
                    value=profile.get("preferred_code_style") or "",
                )
                .props("outlined dense")
                .classes("w-full"),
                "preferred_architecture_style": ui.input(
                    "Architecture style",
                    value=profile.get("preferred_architecture_style") or "",
                )
                .props("outlined dense")
                .classes("w-full"),
                "communication_preferences": ui.textarea(
                    "Communication",
                    value=profile.get("communication_preferences") or "",
                )
                .props("outlined dense rows=3")
                .classes("w-full"),
            }
            active = ui.switch("Active", value=profile.get("is_active", True))

            async def save() -> None:
                payload = {
                    "name": fields["name"].value or None,
                    "role": fields["role"].value or None,
                    "primary_skills": _split_csv(fields["primary_skills"].value or ""),
                    "preferred_languages": _split_csv(fields["preferred_languages"].value or ""),
                    "preferred_frameworks": _split_csv(fields["preferred_frameworks"].value or ""),
                    "preferred_explanation_style": (
                        fields["preferred_explanation_style"].value or None
                    ),
                    "preferred_code_style": fields["preferred_code_style"].value or None,
                    "preferred_architecture_style": (
                        fields["preferred_architecture_style"].value or None
                    ),
                    "communication_preferences": (
                        fields["communication_preferences"].value or None
                    ),
                    "is_active": active.value,
                }
                await self._save_profile_section("/profile", payload, "Profile saved.")

            save_button = ui.button("Save Profile", icon="save").classes("w-full")
            save_button.on_click(
                lambda: self._run_with_loader(
                    save_button,
                    "Save Profile",
                    "Saving...",
                    save,
                )
            )

    def _render_work_style_form(self) -> None:
        work_style = self.work_style
        with ui.card().classes("pc-card grow min-w-[420px]"):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-10 h-10 rounded-xl bg-violet-50 text-violet-600 "
                    "flex items-center justify-center"
                ):
                    ui.icon("tune").classes("text-xl")
                with ui.column().classes("gap-0"):
                    ui.label("Work Style").classes("text-base font-bold")
                    ui.label("Preferred workflow and collaboration patterns.").classes(
                        "pc-muted text-xs"
                    )
            task_approach = (
                ui.textarea("Task approach", value=work_style.get("task_approach") or "")
                .props("outlined dense rows=3")
                .classes("w-full")
            )
            explanation = (
                ui.input(
                    "Explanation preference",
                    value=work_style.get("explanation_preference") or "",
                )
                .props("outlined dense")
                .classes("w-full")
            )
            workflow = (
                ui.input(
                    "Workflow patterns",
                    value=", ".join(work_style.get("workflow_patterns", [])),
                )
                .props("outlined dense")
                .classes("w-full")
            )
            production = (
                ui.input(
                    "Production example preference",
                    value=work_style.get("production_example_preference") or "",
                )
                .props("outlined dense")
                .classes("w-full")
            )
            preferences = (
                ui.input(
                    "Common preferences",
                    value=", ".join(work_style.get("common_preferences", [])),
                )
                .props("outlined dense")
                .classes("w-full")
            )
            mistakes = (
                ui.input(
                    "Mistakes to avoid",
                    value=", ".join(work_style.get("common_mistakes_to_avoid", [])),
                )
                .props("outlined dense")
                .classes("w-full")
            )
            active = ui.switch("Active", value=work_style.get("is_active", True))

            async def save() -> None:
                payload = {
                    "task_approach": task_approach.value or None,
                    "explanation_preference": explanation.value or None,
                    "workflow_patterns": _split_csv(workflow.value or ""),
                    "production_example_preference": production.value or None,
                    "common_preferences": _split_csv(preferences.value or ""),
                    "common_mistakes_to_avoid": _split_csv(mistakes.value or ""),
                    "is_active": active.value,
                }
                await self._save_profile_section("/work-style", payload, "Work style saved.")

            save_button = ui.button("Save Work Style", icon="save").classes("w-full")
            save_button.on_click(
                lambda: self._run_with_loader(
                    save_button,
                    "Save Work Style",
                    "Saving...",
                    save,
                )
            )

    async def _save_profile_section(
        self,
        path: str,
        payload: dict[str, Any],
        success_message: str,
    ) -> None:
        try:
            saved = await run.io_bound(
                _request_json,
                "PUT",
                self.base_url,
                path,
                payload,
                None,
                self.api_key or None,
            )
        except RuntimeError as exc:
            ui.notify(str(exc), type="negative")
            return
        if path == "/profile":
            self.profile = saved
        else:
            self.work_style = saved
        ui.notify(success_message, type="positive")

    @ui.refreshable
    def render_users_tab(self) -> None:
        with ui.row().classes("w-full items-end gap-4"):
            self._render_section_header(
                "Access control",
                "User Management",
                "Create API credentials and manage account access.",
            )
            ui.space()
            refresh_button = ui.button(
                "Refresh users",
                icon="refresh",
            ).props("outline")
            refresh_button.on_click(
                lambda: self._run_with_loader(
                    refresh_button,
                    "Refresh users",
                    "Refreshing...",
                    self.refresh_users,
                )
            )

        self._render_create_user()

        if self.users is None:
            self._render_empty_state(
                "group",
                "Users not loaded",
                "Select Refresh users to retrieve API accounts from the database.",
            )
            return

        if not self.users:
            self._render_empty_state(
                "person_add",
                "No API users",
                "Create the first user above. A secret key will be generated once.",
            )
            return

        with ui.column().classes("pc-panel w-full gap-0"):
            with ui.row().classes(
                "w-full items-center px-5 py-3 bg-slate-50 border-b border-slate-200"
            ):
                ui.label("Account").classes("grow text-xs font-bold pc-muted uppercase")
                ui.label("Key & activity").classes(
                    "w-[360px] text-xs font-bold pc-muted uppercase pc-desktop-only"
                )
                ui.label("Actions").classes(
                    "w-[310px] text-right text-xs font-bold pc-muted uppercase"
                )
            for row in self.users:
                self._render_user_row(row)

    async def refresh_users(self) -> None:
        try:
            self.users = await run.io_bound(self._load_users)
        except Exception as exc:
            ui.notify(f"Could not load users: {exc}", type="negative")
            return
        self.render_summary_cards.refresh()
        self.render_users_tab.refresh()

    @staticmethod
    def _load_users() -> list[dict[str, Any]]:
        return get_auth_service().list_users_with_sessions()

    def _render_create_user(self) -> None:
        with (
            ui.expansion(
                "Create a new API user",
                icon="person_add",
            )
            .classes("w-full my-4")
            .props("header-class='text-weight-bold'")
        ):
            with ui.column().classes("p-2 gap-4"):
                ui.label("The raw secret key is displayed only once after creation.").classes(
                    "pc-muted text-sm"
                )
                with ui.row().classes("w-full items-start gap-4 flex-wrap"):
                    email = (
                        ui.input("Email address")
                        .props("outlined dense")
                        .classes("grow min-w-[280px]")
                    )
                    with ui.column().classes("min-w-[220px] gap-1"):
                        use_expiry = ui.switch("Set expiry date")
                        expiry = (
                            ui.input(
                                "Expires on",
                                value=(date.today() + timedelta(days=365)).isoformat(),
                            )
                            .props("type=date outlined dense")
                            .classes("w-full")
                        )
                        expiry.set_visibility(False)
                        use_expiry.on_value_change(
                            lambda event: expiry.set_visibility(bool(event.value))
                        )

            async def create_user() -> None:
                normalized_email = str(email.value or "").strip().lower()
                if not normalized_email or "@" not in normalized_email:
                    ui.notify("Enter a valid email address.", type="negative")
                    return
                try:
                    expires_at = None
                    if use_expiry.value:
                        expires_at = datetime.combine(
                            date.fromisoformat(str(expiry.value)),
                            datetime.min.time(),
                            tzinfo=UTC,
                        )
                    raw_key = await run.io_bound(
                        self._create_user,
                        normalized_email,
                        expires_at,
                    )
                except Exception as exc:
                    ui.notify(f"Could not create user: {exc}", type="negative")
                    return
                await self.refresh_users()
                self._open_key_dialog(normalized_email, raw_key)

            create_button = ui.button(
                "Create user & generate key",
                icon="key",
            ).classes("self-start")
            create_button.on_click(
                lambda: self._run_with_loader(
                    create_button,
                    "Create user & generate key",
                    "Creating user...",
                    create_user,
                )
            )

    @staticmethod
    def _create_user(email: str, expires_at: datetime | None) -> str:
        auth_service = get_auth_service()
        if auth_service.user_repo.get_by_email(email):
            raise ValueError(f"A user with email {email} already exists.")
        _, raw_key = auth_service.create_user(email, expires_at=expires_at)
        return raw_key

    def _render_user_row(self, row: dict[str, Any]) -> None:
        with ui.row().classes(
            "w-full items-center px-5 py-4 gap-4 border-b border-slate-100 last:border-b-0"
        ):
            with ui.column().classes("grow gap-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(row["email"]).classes("text-sm font-bold")
                    if row["is_active"]:
                        ui.html('<span class="pc-badge pc-badge-success">Active</span>')
                    else:
                        ui.html('<span class="pc-badge pc-badge-muted">Inactive</span>')
                ui.label(f"Created {_format_timestamp(row['created_at'])}").classes(
                    "pc-muted text-xs"
                )
            with ui.column().classes("w-[360px] gap-1 pc-desktop-only"):
                ui.label(f"Key prefix: {row['key_prefix']}...").classes("font-mono text-xs")
                ui.label(
                    f"Expires {_format_timestamp(row['expires_at'])} · "
                    f"Last seen {_format_timestamp(row['last_seen_at'])} · "
                    f"IP {row.get('ip_address') or '-'}"
                ).classes("pc-muted text-xs")
            with ui.row().classes("w-[310px] justify-end gap-2"):
                label = "Deactivate" if row["is_active"] else "Activate"
                icon = "block" if row["is_active"] else "check_circle"
                active_button = ui.button(
                    label,
                    icon=icon,
                ).props("flat dense color=secondary")
                active_action = self._user_action(
                    row["id"],
                    lambda service,
                    user,
                    active=not row["is_active"]: service.set_active(
                        user,
                        active=active,
                    ),
                )
                active_button.on_click(
                    lambda button=active_button,
                    idle_text=label,
                    action=active_action: self._run_with_loader(
                        button,
                        idle_text,
                        "Updating...",
                        action,
                    )
                )
                key_button = ui.button(
                    "New key",
                    icon="key",
                ).props("flat dense")
                key_action = self._regenerate_user_key(
                    row["id"],
                    row["email"],
                )
                key_button.on_click(
                    lambda button=key_button,
                    action=key_action: self._run_with_loader(
                        button,
                        "New key",
                        "Generating...",
                        action,
                    )
                )
                ui.button(
                    icon="delete_outline",
                    color="negative",
                    on_click=self._delete_user(row["id"]),
                ).props("flat dense round").tooltip("Delete user")

    def _user_action(
        self,
        user_id: str,
        action: Callable[[Any, Any], Any],
    ) -> Callable[[], Any]:
        async def handler() -> None:
            def execute() -> None:
                service = get_auth_service()
                user = service.user_repo.get_by_id(user_id)
                if user is None:
                    raise ValueError("User no longer exists.")
                action(service, user)

            try:
                await run.io_bound(execute)
            except Exception as exc:
                ui.notify(str(exc), type="negative")
                return
            await self.refresh_users()

        return handler

    def _regenerate_user_key(self, user_id: str, email: str) -> Callable[[], Any]:
        async def handler() -> None:
            def regenerate() -> str:
                service = get_auth_service()
                user = service.user_repo.get_by_id(user_id)
                if user is None:
                    raise ValueError("User no longer exists.")
                _, raw_key = service.regenerate_key(user)
                return raw_key

            try:
                raw_key = await run.io_bound(regenerate)
            except Exception as exc:
                ui.notify(str(exc), type="negative")
                return
            await self.refresh_users()
            self._open_key_dialog(email, raw_key)

        return handler

    def _delete_user(self, user_id: str) -> Callable[[], Any]:
        async def handler() -> None:
            with ui.dialog() as dialog, ui.card():
                ui.label("Delete this user? This cannot be undone.")
                with ui.row():
                    ui.button("Cancel", on_click=dialog.close)

                    async def confirm() -> None:
                        action = self._user_action(
                            user_id,
                            lambda service, user: service.delete_user(user),
                        )
                        await action()
                        dialog.close()

                    delete_button = ui.button("Delete", color="negative")
                    delete_button.on_click(
                        lambda: self._run_with_loader(
                            delete_button,
                            "Delete",
                            "Deleting...",
                            confirm,
                        )
                    )
            dialog.open()

        return handler

    def _build_key_dialog(self) -> None:
        with ui.dialog().props("persistent") as self.key_dialog, ui.card().classes(
            "pc-card min-w-[520px] max-w-full"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-11 h-11 rounded-xl bg-indigo-50 text-indigo-600 "
                    "flex items-center justify-center"
                ):
                    ui.icon("key").classes("text-2xl")
                with ui.column().classes("gap-0"):
                    ui.label("API key generated").classes("text-lg font-bold")
                    self.key_email_label = ui.label("").classes("pc-muted text-sm")
            ui.label("Copy this key now. It will not be shown again.").classes("pc-muted text-sm")
            self.key_code = ui.code("").classes("w-full rounded-xl")
            with ui.row().classes("w-full gap-3"):

                async def copy_key() -> None:
                    await asyncio.sleep(0.1)
                    ui.clipboard.write(self.generated_key)
                    ui.notify("API key copied to clipboard.", type="positive")

                copy_button = ui.button("Copy key", icon="content_copy").classes("grow")
                copy_button.on_click(
                    lambda: Dashboard._run_with_loader(
                        copy_button,
                        "Copy key",
                        "Copying...",
                        copy_key,
                    )
                )
                ui.button(
                    "Done",
                    icon="check",
                    on_click=self.key_dialog.close,
                ).props("outline").classes("grow")

    def _open_key_dialog(self, email: str, raw_key: str) -> None:
        self.generated_key = raw_key
        self.key_email_label.set_text(email)
        self.key_code.set_content(raw_key)
        self.key_dialog.open()


@ui.page("/")
def dashboard_page() -> None:
    Dashboard().build()


def main() -> None:
    ui.run(
        title="Personal Context Dashboard",
        host=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", os.getenv("DASHBOARD_PORT", "8501"))),
        reload=False,
        show=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
