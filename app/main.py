"""PocketFriend - application shell and Streamlit entry point.

Run with:  python run.py      (or: streamlit run app/main.py)

This module owns the frame only: the sidebar, the navigation, the local AI and
library status, and the route table. Every screen lives in app/views and is
built from app/ui, so the business logic in app/database.py, app/rag.py,
app/planner.py, app/quiz.py and app/gemma.py is untouched.

Navigation is a list of real buttons rather than a radio group: the sidebar
reads like an application, and every item is reachable by keyboard and by
screen reader without any CSS trickery.
"""

from __future__ import annotations

import streamlit as st

from app import config
from app.ui import components as ui
from app.ui import runtime as rt
from app.ui import theme

st.set_page_config(
    page_title="PocketFriend",
    page_icon=theme.favicon(),
    layout="wide",
    initial_sidebar_state="expanded",
)

config.ensure_directories()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

ROUTES = {
    "home": "app.views.home",
    "ask": "app.views.ask",
    "plan": "app.views.plan",
    "quiz": "app.views.quiz",
    "documents": "app.views.documents",
    "settings": "app.views.settings",
}

APP_VERSION = "1.0"

# One icon per navigation route, from the app's own line-icon set in the theme.
NAV_ICONS = {
    "home": "home",
    "ask": "ask",
    "plan": "plan",
    "quiz": "quiz",
    "documents": "folder",
    "settings": "settings",
}

# On a phone the sidebar is a drawer that hides the page it is meant to navigate,
# so the same five workspace pages are drawn again as cards along the bottom.
# The bar is display:none on wider screens, where the sidebar does the job.
MOBILE_NAV = (
    ("home", "Home"),
    ("ask", "Ask"),
    ("plan", "Plan"),
    ("quiz", "Quiz"),
    ("documents", "Docs"),
)


def _view(route: str):
    """Import the view module for a route on demand, then return its render fn."""
    module = __import__(ROUTES[route], fromlist=["render"])
    return module.render


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def render_navigation(route: str) -> None:
    """One button per workspace page. The current page is marked, not selected."""
    for label, key, _mark in rt.NAV:
        if key == "settings":
            continue
        with st.container(key=f"pf-navitem-{key}"):
            if ui.button(
                label,
                key=f"nav_{key}",
                type="primary" if key == route else "secondary",
                icon=NAV_ICONS[key],
                width="stretch",
            ):
                rt.go_to(key)


def render_settings_link(route: str) -> None:
    """Settings sits below the library status, the way a utility page should."""
    with st.container(key="pf-navitem-settings"):
        if ui.button(
            "Settings",
            key="nav_settings",
            type="primary" if route == "settings" else "secondary",
            icon=NAV_ICONS["settings"],
            width="stretch",
        ):
            rt.go_to("settings")


def render_library_status() -> None:
    snapshot = rt.library()
    documents = snapshot["documents"]
    pages = sum(snapshot["pages"].values())

    ui.render(ui.navlabel("Library"))
    if documents:
        ui.render(
            ui.facts(
                [
                    ("Documents", str(len(documents))),
                    ("Pages", str(pages)),
                ]
            )
        )
    else:
        ui.render(
            ui.text_note("No PDFs yet. Add one to start asking questions.", tone="quiet")
        )


def render_ai_status() -> None:
    status = rt.ai_status()

    ui.render(ui.navlabel("Local AI"))
    if status.ready:
        ui.render(
            ui.status(
                "ok",
                "Ready",
                f"{theme.model_label(status.model)} on this computer",
            )
        )
    elif not status.ollama_running:
        ui.render(ui.status("danger", "Not running", "Start Ollama to ask questions"))
    else:
        ui.render(ui.status("warn", "Model missing", f"ollama pull {status.model}"))


def render_sidebar() -> str:
    """Draw the sidebar, then return the route to render.

    The route is read after the buttons exist, because pressing one changes it.
    """
    route = rt.current_page()

    with st.sidebar:
        ui.render(ui.brand())

        with st.container(key="pf-navlist-main"):
            render_navigation(route)

        # Flex-grow spacer pushes footer content down on tall screens
        with st.container(key="pf-sidebarfill-fill"):
            ui.spacer("sm")

        # ── Footer / status section ──────────────────────────────
        render_library_status()

        ui.render(ui.rule(tight=True))

        render_ai_status()

        ui.render(ui.rule(tight=True))

        render_settings_link(route)

        ui.render(ui.side_note(ui.esc("Private by default · no account, no cloud.")))
        st.caption(f"PocketFriend {APP_VERSION}")


    return rt.current_page()


def render_mobile_nav(route: str) -> None:
    """The sidebar's five pages, as cards, for small screens.

    Real buttons in a keyed container, exactly like the sidebar: the layout is
    CSS, so tapping a card is an ordinary Streamlit click and the page it opens
    is an ordinary rerun. Rendered after the page so it sits last in the DOM.
    """
    with st.container(key="pf-mobnav-main"):
        columns = st.columns(len(MOBILE_NAV), gap="small")
        for column, (key, label) in zip(columns, MOBILE_NAV):
            with column:
                with st.container(key=f"pf-mobitem-{key}"):
                    if ui.button(
                        label,
                        key=f"mobnav_{key}",
                        type="primary" if key == route else "secondary",
                        icon=NAV_ICONS[key],
                        width="stretch",
                    ):
                        rt.go_to(key)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    rt.warm_up()
    theme.inject()
    rt.apply_query_route()

    route = render_sidebar()
    if st.session_state.get("pf_autoload_demo"):
        st.session_state.pop("pf_autoload_demo", None)
        from app.views import documents as documents_view

        documents_view.load_sample_material()

    rt.render_notice()
    _view(route)()
    render_mobile_nav(route)


if __name__ == "__main__":
    main()
