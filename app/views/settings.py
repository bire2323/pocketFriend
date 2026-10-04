"""Settings: what this installation is, and whether it is ready to work.

Read-only on purpose. Every value here is discovered from the running system or
read from `config`, so the screen never claims a value the backend does not use,
and offers one action: check again.
"""

from __future__ import annotations

import streamlit as st

from app import config
from app.ui import components as ui
from app.ui import runtime as rt
from app.ui import theme

SUBTITLE = "Everything PocketFriend needs runs on this computer."


def render_ai(status) -> None:
    if status.ready:
        tone, label = "ok", "Local AI ready"
        detail = f"{theme.model_label(status.model)} · Ollama on this computer"
    else:
        tone, label = "danger", status.headline
        detail = status.detail

    with st.container(key="pf-sheet-settings-ai"):
        ui.render(ui.section("Local AI", "Answers, plans and quizzes are written here.", mark="bolt"))
        ui.render(ui.status(tone, label, detail))
        if not status.ready:
            ui.render(ui.note(f"<pre>{ui.esc(status.user_message())}</pre>", tone="danger"))

        if status.local_models:
            in_use = status.model.split(":")[0]
            ui.spacer("sm")
            ui.render(
                ui.kv(
                    [
                        (
                            "In use" if name.split(":")[0] == in_use else "Installed",
                            name,
                        )
                        for name in status.local_models
                    ]
                )
            )

    if ui.button("Check again", key="settings_ai_recheck", icon="refresh"):
        rt.refresh_ai_status()
        st.rerun()


def render_library() -> None:
    snapshot = rt.library()
    documents = snapshot["documents"]
    pages = sum(snapshot["pages"].values())
    chunks = sum(snapshot["chunks"].values())
    scope = rt.scope()

    with st.container(key="pf-sheet-settings-library"):
        ui.render(
            ui.section("Your material", "Indexed locally, with no account.", mark="file")
        )
        ui.render(
            ui.kv(
                [
                    ("Documents", str(len(documents))),
                    ("Pages", str(pages)),
                    ("Searchable passages", str(chunks)),
                    ("Questions use", scope or "All documents"),
                ]
            )
        )
        ui.render(
            ui.text_note(
                f"Stored in {config.DOCUMENTS_DIR} on this computer. Removing a document "
                "deletes both the file and the index.",
                tone="quiet",
            )
        )


def render_storage() -> None:
    with st.container(key="pf-sheet-settings-setup"):
        ui.render(ui.section("Setup", "Read from the code, not editable here.", mark="settings"))
        ui.render(
            ui.kv(
                [
                    ("App", config.APP_TITLE),
                    ("Model", config.OLLAMA_MODEL),
                    ("Ollama host", config.OLLAMA_HOST),
                    ("Embeddings", config.EMBEDDING_MODEL),
                    (
                        "Retrieval",
                        f"top {config.TOP_K} passages, match above "
                        f"{config.RELEVANCE_THRESHOLD:.2f}",
                    ),
                    (
                        "Passages",
                        f"{config.CHUNK_SIZE} characters, {config.CHUNK_OVERLAP} overlap",
                    ),
                    ("Tasks database", str(config.DB_PATH)),
                ]
            )
        )
        ui.render(
            ui.text_note(
                "Changing any of these means editing app/config.py and restarting "
                "PocketFriend.",
                tone="quiet",
            )
        )


def render_privacy() -> None:
    with st.container(key="pf-sheet-settings-privacy"):
        ui.render(ui.section("Privacy", "What leaves this computer: nothing.", mark="lock"))
        ui.render(
            ui.steps(
                [
                    ("Your PDFs stay on disk", "Read from your own documents folder."),
                    (
                        "The index stays on disk",
                        "A local Chroma database, next to the files you uploaded.",
                    ),
                    (
                        "The AI runs here",
                        "Ollama writes the answers locally. No account, no tracking, "
                        "no telemetry.",
                    ),
                ]
            )
        )


def render() -> None:
    rt.warm_up()

    with st.container(key="pf-bar-settings"):
        head, actions = st.columns([4, 1.2], vertical_alignment="center")
        with head:
            ui.render(ui.topbar("Settings", SUBTITLE, eyebrow="This computer"))
        with actions:
            if ui.button("Back to home", key="settings_home", icon="home", width="stretch"):
                rt.go_to("home")

    left, right = st.columns([1, 1], gap="large")
    with left:
        render_ai(rt.ai_status())
        ui.spacer("md")
        render_library()
    with right:
        render_storage()
        ui.spacer("md")
        render_privacy()
