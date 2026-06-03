from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib import error, parse, request

import streamlit as st

from personal_context_mcp.models.enums import MemoryType

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
FORM_KEYS = {
    "profile": "Edit Profile",
    "work_style": "Edit Work Style",
    "memory": "Add Memory",
    "task_outcome": "Add Task Outcome",
}


def _normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _request_json(
    method: str,
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
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
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    api_request = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(api_request) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{exc.code} {exc.reason}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach API at {url}: {exc.reason}") from exc


def _format_timestamp(value: str | None) -> str:
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def _set_active_form(form_key: str | None) -> None:
    st.session_state["active_form"] = form_key


def _render_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --pc-bg: #f3f3f3;
            --pc-surface: #ffffff;
            --pc-surface-strong: #f7f7f7;
            --pc-border: #d4d4d4;
            --pc-border-strong: #111111;
            --pc-text: #111111;
            --pc-muted: #525252;
            --pc-accent: #111111;
            --pc-accent-soft: #eaeaea;
            --pc-shadow: rgba(0, 0, 0, 0.08);
        }
        .stApp {
            background:
                radial-gradient(circle at top left, #ffffff 0%, transparent 28%),
                linear-gradient(180deg, #fafafa 0%, var(--pc-bg) 100%);
            color: var(--pc-text);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f0f0f 0%, #1f1f1f 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        [data-testid="stSidebar"] * {
            color: #ffffff;
        }
        [data-testid="stSidebar"] .stTextInput input {
            background: rgba(255, 255, 255, 0.08);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        [data-testid="stSidebar"] .stAlert {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.14);
        }
        h1, h2, h3 {
            color: var(--pc-text);
        }
        [data-testid="stVerticalBlock"] [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--pc-surface);
            border: 1px solid var(--pc-border);
            border-radius: 18px;
            box-shadow: 0 14px 32px var(--pc-shadow);
        }
        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox [data-baseweb="select"] > div,
        .stMultiSelect [data-baseweb="select"] > div {
            background: var(--pc-surface);
            color: var(--pc-text);
            border: 1px solid var(--pc-border);
        }
        .stTextInput input:focus,
        .stTextArea textarea:focus {
            border-color: var(--pc-border-strong);
            box-shadow: 0 0 0 1px var(--pc-border-strong);
        }
        .stButton > button,
        .stFormSubmitButton > button {
            background: linear-gradient(180deg, #1f1f1f 0%, var(--pc-accent) 100%);
            color: #ffffff;
            border: 1px solid #000000;
            border-radius: 12px;
            box-shadow: 0 10px 22px rgba(0, 0, 0, 0.16);
        }
        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            background: linear-gradient(180deg, #2d2d2d 0%, #000000 100%);
            border-color: #000000;
        }
        .stCaption,
        [data-testid="stMarkdownContainer"] p {
            color: var(--pc-muted);
        }
        [class*="st-key-close-"] button {
            width: 2.4rem;
            min-width: 2.4rem;
            height: 2.4rem;
            padding: 0;
            border-radius: 999px;
            border: 1px solid var(--pc-border);
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
            background: var(--pc-surface-strong);
            color: var(--pc-text);
            box-shadow: 0 1px 2px var(--pc-shadow);
        }
        [class*="st-key-close-"] button:hover {
            border-color: var(--pc-border-strong);
            color: #000000;
            background: #ebebeb;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_form_actions() -> None:
    st.subheader("Actions")
    for form_key, label in FORM_KEYS.items():
        if st.button(label, key=f"open-{form_key}", use_container_width=True):
            _set_active_form(form_key)


def _render_form_shell(form_key: str, title: str) -> bool:
    if st.session_state.get("active_form") != form_key:
        return False

    with st.container(border=True):
        head, tail = st.columns([8, 1], vertical_alignment="center")
        with head:
            st.markdown(f"### {title}")
        with tail:
            if st.button(
                "×",
                key=f"close-{form_key}",
                help="Close form",
                type="secondary",
            ):
                _set_active_form(None)
                st.rerun()
    return True


def _render_memory_feed(base_url: str) -> None:
    st.subheader("Recent Memories")
    refresh = st.button("Refresh Feed", use_container_width=True)
    if refresh:
        st.cache_data.clear()

    @st.cache_data(ttl=40, show_spinner=False)
    def _load_recent_memories(api_base_url: str) -> list[dict[str, Any]]:
        return _request_json("GET", api_base_url, "/memories/recent", query={"limit": 10})

    try:
        memories = _load_recent_memories(base_url)
    except RuntimeError as exc:
        st.error(str(exc))
        return

    if not memories:
        st.info("No memories yet.")
        return

    for memory in memories:
        tags = ", ".join(memory.get("tags", [])) or "none"
        title = memory.get("title", "Untitled")
        meta = (
            f"{memory.get('memory_type', 'note')} | "
            f"importance {memory.get('importance', 1)} | "
            f"{_format_timestamp(memory.get('created_at'))}"
        )
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(meta)
            st.write(memory.get("content", ""))
            st.caption(f"Tags: {tags}")


def _render_profile_form(base_url: str) -> None:
    if not _render_form_shell("profile", "Profile"):
        return

    try:
        profile = _request_json("GET", base_url, "/profile") or {}
    except RuntimeError as exc:
        st.error(str(exc))
        profile = {}

    with st.form("profile-form"):
        name = st.text_input("Name", value=profile.get("name", ""))
        role = st.text_input("Role", value=profile.get("role", ""))
        primary_skills = st.text_input(
            "Primary skills",
            value=", ".join(profile.get("primary_skills", [])),
            help="Comma-separated",
        )
        preferred_languages = st.text_input(
            "Languages",
            value=", ".join(profile.get("preferred_languages", [])),
            help="Comma-separated",
        )
        preferred_frameworks = st.text_input(
            "Frameworks",
            value=", ".join(profile.get("preferred_frameworks", [])),
            help="Comma-separated",
        )
        preferred_explanation_style = st.text_input(
            "Explanation style",
            value=profile.get("preferred_explanation_style", ""),
        )
        preferred_code_style = st.text_input(
            "Code style",
            value=profile.get("preferred_code_style", ""),
        )
        preferred_architecture_style = st.text_input(
            "Architecture style",
            value=profile.get("preferred_architecture_style", ""),
        )
        communication_preferences = st.text_area(
            "Communication",
            value=profile.get("communication_preferences", ""),
        )
        is_active = st.checkbox("Active", value=profile.get("is_active", True))
        if st.form_submit_button("Save Profile", use_container_width=True):
            payload = {
                "name": name or None,
                "role": role or None,
                "primary_skills": _split_csv(primary_skills),
                "preferred_languages": _split_csv(preferred_languages),
                "preferred_frameworks": _split_csv(preferred_frameworks),
                "preferred_explanation_style": preferred_explanation_style or None,
                "preferred_code_style": preferred_code_style or None,
                "preferred_architecture_style": preferred_architecture_style or None,
                "communication_preferences": communication_preferences or None,
                "is_active": is_active,
            }
            try:
                _request_json("PUT", base_url, "/profile", payload=payload)
            except RuntimeError as exc:
                st.error(str(exc))
            else:
                st.success("Profile saved.")
                _set_active_form(None)
                st.rerun()


def _render_work_style_form(base_url: str) -> None:
    if not _render_form_shell("work_style", "Work Style"):
        return

    try:
        work_style = _request_json("GET", base_url, "/work-style") or {}
    except RuntimeError as exc:
        st.error(str(exc))
        work_style = {}

    with st.form("work-style-form"):
        task_approach = st.text_area(
            "Task approach",
            value=work_style.get("task_approach", ""),
        )
        explanation_preference = st.text_input(
            "Explanation preference",
            value=work_style.get("explanation_preference", ""),
        )
        workflow_patterns = st.text_input(
            "Workflow patterns",
            value=", ".join(work_style.get("workflow_patterns", [])),
            help="Comma-separated",
        )
        production_example_preference = st.text_input(
            "Production example preference",
            value=work_style.get("production_example_preference", ""),
        )
        common_preferences = st.text_input(
            "Common preferences",
            value=", ".join(work_style.get("common_preferences", [])),
            help="Comma-separated",
        )
        common_mistakes_to_avoid = st.text_input(
            "Common mistakes to avoid",
            value=", ".join(work_style.get("common_mistakes_to_avoid", [])),
            help="Comma-separated",
        )
        is_active = st.checkbox("Active", value=work_style.get("is_active", True))
        if st.form_submit_button("Save Work Style", use_container_width=True):
            payload = {
                "task_approach": task_approach or None,
                "explanation_preference": explanation_preference or None,
                "workflow_patterns": _split_csv(workflow_patterns),
                "production_example_preference": production_example_preference or None,
                "common_preferences": _split_csv(common_preferences),
                "common_mistakes_to_avoid": _split_csv(common_mistakes_to_avoid),
                "is_active": is_active,
            }
            try:
                _request_json("PUT", base_url, "/work-style", payload=payload)
            except RuntimeError as exc:
                st.error(str(exc))
            else:
                st.success("Work style saved.")
                _set_active_form(None)
                st.rerun()


def _render_memory_form(base_url: str) -> None:
    if not _render_form_shell("memory", "Save Memory"):
        return

    with st.form("memory-form"):
        title = st.text_input("Title")
        content = st.text_area("Content")
        memory_type = st.selectbox("Type", [member.value for member in MemoryType], index=6)
        tags = st.text_input("Tags", help="Comma-separated")
        source = st.text_input("Source")
        importance = st.slider("Importance", min_value=1, max_value=5, value=1)
        if st.form_submit_button("Save Memory", use_container_width=True):
            payload = {
                "title": title,
                "content": content,
                "memory_type": memory_type,
                "tags": _split_csv(tags),
                "source": source or None,
                "importance": importance,
            }
            try:
                _request_json("POST", base_url, "/memories", payload=payload)
                st.cache_data.clear()
            except RuntimeError as exc:
                st.error(str(exc))
            else:
                st.success("Memory saved.")
                _set_active_form(None)
                st.rerun()


def _render_task_outcome_form(base_url: str) -> None:
    if not _render_form_shell("task_outcome", "Task Outcome"):
        return

    with st.form("outcome-form"):
        task_summary = st.text_area("Task summary")
        final_solution = st.text_area("Final solution")
        decisions = st.text_input("Decisions", help="Comma-separated")
        mistakes = st.text_input("Mistakes", help="Comma-separated")
        corrections = st.text_input("Corrections", help="Comma-separated")
        learned_preferences = st.text_input("Learned preferences", help="Comma-separated")
        source = st.text_input("Source")
        if st.form_submit_button("Save Outcome", use_container_width=True):
            payload = {
                "task_summary": task_summary,
                "final_solution": final_solution or None,
                "decisions": _split_csv(decisions),
                "mistakes": _split_csv(mistakes),
                "corrections": _split_csv(corrections),
                "learned_preferences": _split_csv(learned_preferences),
                "source": source or None,
            }
            try:
                _request_json("POST", base_url, "/task-outcomes", payload=payload)
            except RuntimeError as exc:
                st.error(str(exc))
            else:
                st.success("Task outcome saved.")
                _set_active_form(None)
                st.rerun()


def _render_context_lookup(base_url: str) -> None:
    st.subheader("Relevant Context")
    with st.form("context-form"):
        query = st.text_area("Query")
        limit = st.slider("Limit", min_value=1, max_value=25, value=5)
        submitted = st.form_submit_button("Fetch Context", use_container_width=True)

    if not submitted:
        return

    try:
        context = _request_json("POST", base_url, "/context", payload={"query": query, "limit": limit})
    except RuntimeError as exc:
        st.error(str(exc))
        return

    st.markdown("**Summary**")
    st.write(context.get("context_summary", ""))

    with st.expander("Raw response", expanded=False):
        st.json(context)


def main() -> None:
    st.set_page_config(page_title="Personal Context Dashboard", page_icon="PC", layout="wide")
    st.title("Personal Context Dashboard")
    st.caption("Streamlit UI for the Personal Context MCP API.")
    st.session_state.setdefault("active_form", None)
    _render_styles()

    with st.sidebar:
        st.header("Connection")
        base_url = st.text_input("API base URL", value=DEFAULT_API_BASE_URL)
        st.caption("Start the FastAPI server first, then point Streamlit at that base URL.")

        try:
            health = _request_json("GET", base_url, "/health")
        except RuntimeError as exc:
            st.error(str(exc))
        else:
            st.success(f"API status: {health.get('status', 'unknown')}")

    left, right = st.columns([1.45, 1], gap="large")

    with left:
        _render_memory_feed(base_url)
        _render_context_lookup(base_url)

    with right:
        _render_form_actions()
        _render_profile_form(base_url)
        _render_work_style_form(base_url)
        _render_memory_form(base_url)
        _render_task_outcome_form(base_url)


if __name__ == "__main__":
    main()
