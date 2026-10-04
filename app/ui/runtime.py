"""Shared UI runtime: cached data access, error handling and navigation.

The rule this module enforces is simple: pages never talk to the vector store,
the database or Ollama directly. They ask here, get real data back, and any
failure becomes a friendly message with the technical detail tucked away behind
an expander.
"""

from __future__ import annotations

import contextlib
import traceback
from typing import Any, Callable, Optional

import streamlit as st

from app import config, database, gemma, planner, quiz as quiz_mod, rag
from app.documents import DocumentError
from app.rag import EmbeddingError, RetrievalError

from . import components as ui

PAGE_KEY = "pf_page"
NOTICE_KEY = "pf_notice"
ROUTE_PARAM = "page"

# The sidebar navigation: (label, route key, icon). The shell renders one button
# per row, so navigation is a list of buttons rather than a radio group.
NAV = [
    ("Home", "home", "home"),
    ("Ask", "ask", "ask"),
    ("Study Plan", "plan", "plan"),
    ("Quiz", "quiz", "quiz"),
    ("Documents", "documents", "docs"),
    ("Settings", "settings", "settings"),
]

# Pages the pre-redesign build had, so old links still land somewhere useful.
LEGACY_ROUTES = {
    "dashboard": "home",
    "planner": "plan",
    "tasks": "plan",
    "today": "plan",
}

_ROUTES = {route for _, route, _ in NAV}

# ---------------------------------------------------------------------------
# Start-up
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def warm_up() -> None:
    """Prepare local folders and the database once per server process."""
    config.ensure_directories()
    with database.get_connection():
        pass


# ---------------------------------------------------------------------------
# Local AI
# ---------------------------------------------------------------------------


@st.cache_data(ttl=20, show_spinner=False)
def ai_status() -> gemma.AIStatus:
    """Poll Ollama, briefly cached so reruns do not hammer it."""
    return gemma.check_ollama(config.OLLAMA_MODEL)


def refresh_ai_status() -> None:
    ai_status.clear()


# ---------------------------------------------------------------------------
# Document library
# ---------------------------------------------------------------------------


@st.cache_data(ttl=15, show_spinner=False)
def library() -> dict:
    """One read of the index: documents, pages and chunk totals.

    Cached briefly so a page that needs several numbers performs a single
    vector-store query instead of one per number.
    """
    try:
        return rag.library_snapshot()
    except RetrievalError:
        return {"documents": [], "pages": {}, "chunks": {}}


def refresh_library() -> None:
    library.clear()


def document_count() -> int:
    return len(library()["documents"])


def document_pages() -> int:
    return sum(library()["pages"].values())


def scope() -> Optional[str]:
    """Filename the student has limited questions to, or None for all."""
    chosen = st.session_state.get("pf_scope")
    if chosen and chosen not in library()["documents"]:
        st.session_state["pf_scope"] = None
        return None
    return chosen


def set_scope(filename: Optional[str]) -> None:
    st.session_state["pf_scope"] = filename


def scope_selector(key: str, label: str = "Ask about") -> Optional[str]:
    """A compact dropdown for places where a full source list would crowd the page."""
    documents = library()["documents"]
    options = ["All documents"] + documents
    current = scope() or "All documents"
    index = options.index(current) if current in options else 0
    chosen = st.selectbox(label, options, index=index, key=key)
    set_scope(None if chosen == "All documents" else chosen)
    return scope()


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------


def normalize_page(page: str) -> str:
    """Map an old or unknown page key onto one this build can render."""
    page = LEGACY_ROUTES.get(page, page)
    return page if page in _ROUTES else "home"


def go_to(page: str) -> None:
    """Switch page and rerun. Safe to call from any widget callback."""
    route = normalize_page(page)
    st.session_state[PAGE_KEY] = route
    try:
        st.query_params[ROUTE_PARAM] = route
    except Exception:  # URL is a convenience, not a requirement
        pass
    st.rerun()


def current_page(default: str = "home") -> str:
    return normalize_page(st.session_state.get(PAGE_KEY, default))


def apply_query_route() -> None:
    """Honour `?page=ask` in the URL, so a page can be linked to directly.

    `st.query_params` is the API that works across Streamlit versions;
    `st.context.query_params` is only present in newer ones, so it is only
    consulted as a fallback.
    """
    try:
        requested = st.query_params.get(ROUTE_PARAM)
    except Exception:  # no query params in this context
        requested = getattr(st.context, "query_params", {}).get(ROUTE_PARAM)
    if requested in _ROUTES:
        st.session_state[PAGE_KEY] = requested


def source_picker(key: str = "src") -> Optional[str]:
    """The left-hand source list: every document, plus an "all documents" row.

    Selection is the existing single-file scope, so Ask, Quiz and the planner
    all keep answering from the same place.
    """
    snapshot = library()
    documents = snapshot["documents"]
    pages = snapshot["pages"]
    current = scope()

    chosen = None
    with st.container(key=f"pf-srcall-{key}"):
        if st.button(
            "All documents",
            key=f"{key}_all",
            type="primary" if current is None else "secondary",
            use_container_width=True,
        ):
            set_scope(None)
            st.rerun()

    for index, filename in enumerate(documents):
        count = pages.get(filename, 0)
        label = f"{filename} · {count} page{'' if count == 1 else 's'}"
        with st.container(key=f"pf-srcitem-{key}-{index}"):
            if st.button(
                label,
                key=f"{key}_{index}",
                type="primary" if current == filename else "secondary",
                use_container_width=True,
                help=f"Limit questions to {filename}",
            ):
                chosen = filename

    if chosen:
        set_scope(chosen)
        st.rerun()
    return scope()


# ---------------------------------------------------------------------------
# Notices (messages that must survive the rerun that created them)
# ---------------------------------------------------------------------------


def flash(tone: str, message: str) -> None:
    """Queue a message for the next render."""
    st.session_state[NOTICE_KEY] = {"tone": tone, "message": message}


def take_notice() -> Optional[dict]:
    notice = st.session_state.pop(NOTICE_KEY, None)
    return notice


def render_notice() -> None:
    """Show and clear the queued message."""
    notice = take_notice()
    if not notice:
        return
    tone = notice.get("tone", "info")
    titles = {
        "success": "Done",
        "error": "Something went wrong",
        "warn": "Heads up",
        "info": None,
    }
    if titles.get(tone):
        ui.render(
            ui.note(ui.esc(notice["message"]), title=titles[tone], tone=tone)
        )
    else:
        ui.render(ui.text_note(notice["message"], tone="quiet"))
    ui.spacer("sm")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def error_panel(title: str, message: str, technical: str = "") -> None:
    """A friendly failure with the raw cause one click away.

    `message` is written for a student; `technical` keeps the original text for
    whoever is debugging, without putting it in front of them.
    """
    body = ui.esc(message)
    if technical and technical.strip() and technical.strip() != message.strip():
        ui.render(ui.note(body, title=title, tone="danger"))
        with st.expander("Technical details"):
            st.code(technical.strip()[:2000], language="text")
    else:
        ui.render(ui.note(body, title=title, tone="danger"))


def guard(action: Callable) -> Callable:
    """Run a backend callable, turning any failure into a friendly message.

    Nothing raises past this point: the user never sees a traceback on screen.
    """

    def wrapper(*args, **kwargs):
        try:
            return action(*args, **kwargs)
        except (gemma.OllamaUnavailableError, gemma.ModelNotFoundError) as exc:
            error_panel("The local AI isn't answering", str(exc))
        except (EmbeddingError, RetrievalError) as exc:
            error_panel("The local index isn't responding", str(exc))
        except DocumentError as exc:
            error_panel("That file couldn't be read", str(exc))
        except (quiz_mod.QuizError, planner.PlannerError) as exc:
            error_panel("That didn't work", str(exc))
        except ValueError as exc:
            error_panel("Check that field", str(exc))
        except database.DatabaseError as exc:
            error_panel("Local storage isn't responding", str(exc))
        except Exception as exc:  # last resort: still never a raw traceback
            error_panel(
                "Something unexpected went wrong",
                "PocketFriend hit a problem it did not expect. Your documents and "
                "tasks are still saved locally, so it is safe to try again.",
                technical=f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}",
            )
        return None

    return wrapper


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def working(message: str):
    """A quiet progress line, worded for the student.

    `message` says what is happening, never which library is doing the work:
    "Thinking…" rather than "Calling Ollama".
    """
    slot = st.empty()
    with slot.container(key="pf-loadingbar"):
        ui.render(ui.loading(message))
    try:
        yield
    finally:
        slot.empty()


# ---------------------------------------------------------------------------
# Local AI availability
# ---------------------------------------------------------------------------


def ai_block() -> None:
    """Explain a local AI problem in plain language, without hiding anything."""
    status = ai_status()
    if status.ready:
        return
    if not status.ollama_running:
        ui.render(
            ui.note(
                "PocketFriend can't reach the local AI right now. Start Ollama and "
                "reload this page.",
                title="Local AI unavailable",
                tone="warn",
            )
        )
        with st.expander("How to fix it"):
            st.markdown(
                "1. Open the Ollama app, or run `ollama serve` in a terminal.\n"
                f"2. Check that PocketFriend can reach `{config.OLLAMA_HOST}`.\n"
                "3. Reload the page."
            )
    else:
        ui.render(
            ui.note(
                f"Ollama is running, but `{status.model}` is not installed on this "
                f"computer. Run `ollama pull {status.model}` in a terminal.",
                title="Model not found locally",
                tone="warn",
            )
        )
    ui.render(
        ui.text_note(
            "Everything else keeps working without the model: documents stay "
            "indexed, tasks are stored, and study plans are calculated in Python.",
            tone="quiet",
        )
    )


def status_facts() -> list[tuple]:
    """Real numbers for the sidebar, never invented."""
    snapshot = library()
    tasks = database.count_tasks()
    return [
        ("Documents", str(len(snapshot["documents"]))),
        ("Open tasks", str(tasks)),
    ]


def require_documents(action: str, mark: str = "file") -> bool:
    """Empty state for the pages that cannot work without indexed material."""
    if document_count() > 0:
        return True
    ui.render(
        ui.empty(
            "Your study library is empty",
            f"PocketFriend needs at least one PDF before it can {action}. "
            "Upload your first document to get started.",
            hint="Everything stays on this computer.",
            mark=mark,
        )
    )
    ui.spacer("sm")
    left, right = st.columns(2)
    if ui.button(
        "Add a PDF", key="req_upload", type="primary", icon="upload", width="stretch"
    ):
        go_to("documents")
    if ui.button("Ask a question", key="req_ask", width="stretch"):
        go_to("ask")
    return False