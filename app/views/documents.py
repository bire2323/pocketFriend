"""Documents: the study library.

A list, not a showcase. Each PDF is one compact row with its real page and
passage counts, a remove action that confirms in a dialog first, and a source
switch that decides what Ask and Quiz search. Indexing still runs through
`rag.index_document`; this module only presents it.
"""

from __future__ import annotations

import streamlit as st

from app import config, rag
from app.documents import delete_document, save_upload
from app.ui import components as ui
from app.ui import runtime as rt

SUBTITLE = "Your PDFs, indexed locally. Answers and quizzes are built only from these pages."

PENDING_KEY = "pf_confirm_delete"


def render_header() -> None:
    snapshot = rt.library()
    documents = snapshot["documents"]
    pages = sum(snapshot["pages"].values())
    chunks = sum(snapshot["chunks"].values())

    with st.container(key="pf-bar-documents"):
        head, actions = st.columns([4, 1.3], vertical_alignment="center")
        with head:
            ui.render(
                ui.topbar(
                    "Documents",
                    SUBTITLE,
                    eyebrow="Library",
                    meta=[
                        (f"{len(documents)} indexed", "accent" if documents else "quiet"),
                        (f"{pages} pages", "quiet"),
                        (f"{chunks} searchable passages", "quiet"),
                    ],
                )
            )
        with actions:
            if ui.button(
                "Ask a question",
                key="docs_ask_top",
                icon="ask",
                width="stretch",
                disabled=not rt.library()["documents"],
            ):
                rt.go_to("ask")


def index_uploads(files) -> int:
    """Index each uploaded file and report what happened, inline."""
    indexed = 0
    for upload in files:
        with rt.working(f"Reading {upload.name}…"):
            result = rt.guard(rag.index_document)(upload.getvalue(), upload.name)
        if result:
            indexed += 1
            detail = (
                f"{result['pages']} page{'' if result['pages'] == 1 else 's'} and "
                f"{result['chunks']} searchable passage"
                f"{'' if result['chunks'] == 1 else 's'} indexed."
            )
            warnings = " ".join(result.get("warnings") or [])
            if warnings:
                detail = f"{detail} {warnings}"
            ui.render(ui.note(ui.esc(detail), title=f"{result['filename']} is ready", tone="ok"))
        ui.spacer("sm")
    if indexed:
        rt.refresh_library()
    return indexed


def render_upload() -> None:
    """One upload control, framed as a drop zone but still a real widget."""
    with st.container(key="pf-upload-documents"):
        ui.render(
            ui.item_markup(
                "Add study material",
                note_text="PDF files · kept on this device · never uploaded",
                mark="upload",
                glyph_tone="accent",
            )
        )
        uploads = st.file_uploader(
            "Add study material",
            type=["pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            help="Text-based PDFs work best. Scanned images are not supported in this version.",
            key="doc_upload",
        )
    if uploads:
        index_uploads(uploads)


def remove_document(filename: str) -> None:
    """Delete a document from the index, the local folder, and any active scope."""
    rt.guard(rag.remove_document)(filename)
    path = config.DOCUMENTS_DIR / filename
    if path.exists():
        delete_document(path)
    if rt.scope() == filename:
        rt.set_scope(None)
    rt.refresh_library()
    rt.flash("success", f"{filename} was removed from your library.")


def _dismiss_removal() -> None:
    st.session_state.pop(PENDING_KEY, None)


@st.dialog("Remove this document?", width="small", on_dismiss=_dismiss_removal)
def confirm_removal() -> None:
    """Ask before deleting. Closing the dialog any other way also cancels."""
    filename = st.session_state.get(PENDING_KEY)
    if not filename:
        return
    ui.render(
        ui.text_note(
            f"{filename} will be deleted from this computer and from your search "
            "index. Anything it answered, and any study plan or quiz built from "
            "it, goes with it. This cannot be undone.",
            tone="danger",
        )
    )
    keep, remove = st.columns(2)
    with keep:
        if ui.button("Keep it", key="doc_keep", width="stretch"):
            st.session_state.pop(PENDING_KEY, None)
            st.rerun()
    with remove:
        if ui.button(
            "Remove permanently",
            key="doc_yes",
            type="primary",
            icon="trash",
            width="stretch",
        ):
            st.session_state.pop(PENDING_KEY, None)
            remove_document(filename)
            st.rerun()


def render_document_row(filename: str) -> None:
    """One document: name, counts, and its two actions."""
    snapshot = rt.library()
    pages = snapshot["pages"].get(filename, 0)
    chunks = snapshot["chunks"].get(filename, 0)
    active = rt.scope() == filename

    meta = [
        (f"{pages} page{'' if pages == 1 else 's'}", "quiet"),
        (f"{chunks} passage{'' if chunks == 1 else 's'}", "quiet"),
    ]
    if active:
        meta.append(("Source for questions", "accent"))

    # One row of three columns rather than a column inside a column: nested
    # tracks squeeze the buttons until their labels break letter by letter.
    with st.container(key=f"pf-item-doc-{filename}"):
        info, ask_column, remove_column = st.columns([6, 1.2, 1.5], vertical_alignment="center")
        with info:
            ui.render(ui.item_markup(filename, meta=meta, mark="file"))
        with ask_column:
            if ui.button(
                "Ask",
                key=f"doc_ask_{filename}",
                icon="ask",
                help=f"Ask questions about {filename}",
                width="stretch",
            ):
                rt.set_scope(filename)
                rt.go_to("ask")
        with remove_column:
            if ui.button(
                "Remove",
                key=f"doc_remove_{filename}",
                icon="trash",
                help=f"Remove {filename} from your library",
                width="stretch",
            ):
                st.session_state[PENDING_KEY] = filename
                st.rerun()


def render_library() -> None:
    snapshot = rt.library()
    documents = snapshot["documents"]

    ui.render(
        ui.section(
            "In your library",
            "Everything here is indexed and ready to search.",
            aside=f"{len(documents)} document{'' if len(documents) == 1 else 's'}",
            mark="file",
        )
    )

    if not documents:
        ui.render(
            ui.empty(
                "Your study library is empty",
                "Upload your first PDF and PocketFriend can answer questions about it, "
                "build a study plan and write a quiz.",
                hint="Text-based PDFs work best. Nothing leaves this computer.",
                mark="upload",
            )
        )
        left, right = st.columns(2)
        if ui.button(
            "Add a PDF",
            key="lib_empty_upload",
            type="primary",
            icon="upload",
            width="stretch",
        ):
            rt.flash("info", "Use the Add study material box above to choose a PDF.")
        if ui.button("Load sample material", key="lib_empty_demo", width="stretch"):
            load_sample_material()
            st.rerun()
        return

    for filename in documents:
        render_document_row(filename)


def render_scope() -> None:
    """Which documents questions and quizzes are allowed to use."""
    documents = rt.library()["documents"]
    if not documents:
        return

    current = rt.scope()
    ui.render(ui.section("Source for questions", mark="layers"))
    with st.container(key="pf-sheet-documents-scope"):
        ui.render(
            ui.text_note(
                f"Currently limited to {current}."
                if current
                else "Currently using every document in your library.",
                tone="quiet",
            )
        )
        rt.source_picker("docs")
        if current:
            left, right = st.columns(2)
            if ui.button("Ask about this", key="lib_ask_scope", icon="ask", width="stretch"):
                rt.go_to("ask")
            if ui.button("Quiz me on this", key="lib_quiz_scope", icon="quiz", width="stretch"):
                rt.go_to("quiz")


def load_sample_material() -> int:
    """Copy the sample PDFs into the local store and index them."""
    files = sorted(config.DEMO_DIR.glob("*.pdf"))
    if not files:
        rt.flash("error", "The sample PDFs are missing from this computer.")
        return 0

    loaded = 0
    slot = st.empty()
    for position, path in enumerate(files, start=1):
        with slot.container(key="pf-loadingbar-samples"):
            ui.render(
                ui.loading(f"Reading {path.stem.replace('_', ' ')} ({position} of {len(files)})…")
            )
        destination = save_upload(path.read_bytes(), path.name)
        result = rt.guard(rag.index_document)(str(destination), filename=path.name)
        if result:
            loaded += 1
    slot.empty()

    rt.refresh_library()
    if loaded:
        rt.flash(
            "success",
            f"Added {loaded} sample document{'' if loaded == 1 else 's'} to your library.",
        )
    else:
        rt.flash("error", "The sample documents could not be indexed.")
    return loaded


def render_sample_material() -> None:
    """The short PDFs written for this project, free to index."""
    files = sorted(config.DEMO_DIR.glob("*.pdf"))
    if not files:
        ui.render(
            ui.text_note(
                "The sample PDFs are missing. Rebuild them with "
                "`python data/demo/generate_demo_pdfs.py`.",
                tone="warn",
            )
        )
        return

    with st.container(key="pf-sheet-documents-samples"):
        ui.render(
            ui.item_markup(
                "Sample material",
                meta=[(path.stem.replace("_", " ").title(), "quiet") for path in files],
                note_text="Written for this project, so the demo contains no copyrighted material.",
                mark="layers",
            )
        )
        if ui.button(
            "Load sample documents",
            key="load_demo",
            icon="science",
            width="stretch",
        ):
            load_sample_material()
            st.rerun()


def render() -> None:
    rt.warm_up()
    render_header()
    render_upload()
    ui.spacer("lg")

    render_library()
    ui.spacer("lg")

    left, right = st.columns([1.5, 1], gap="large")
    with left:
        render_scope()
    with right:
        render_sample_material()

    # Opened after the page so the dialog sits above everything drawn here.
    if st.session_state.get(PENDING_KEY):
        confirm_removal()
