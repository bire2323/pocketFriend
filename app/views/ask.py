"""Ask: the research workspace.

Three zones, in the order an answer should be read:

* **Sources** - which documents are in play, and how they were ranked;
* **Conversation** - the question, the answer, and the composer at the end;
* **Evidence** - the retrieved passages behind the latest answer.

Retrieval and generation are unchanged: this screen presents `rag.answer_question`
and passes the chosen source through to it.
"""

from __future__ import annotations

import streamlit as st

from app import rag
from app.ui import components as ui
from app.ui import runtime as rt

SUBTITLE = "Answers are written only from your own pages, with the page numbers attached."

SUGGESTIONS = [
    "What are the key ideas I should know?",
    "Explain the hardest part simply",
    "What should I review before the exam?",
    "Give me the definitions I need to remember",
]


def history_for_retrieval(limit: int = 2) -> str:
    """A short transcript of recent turns, so follow-ups keep their context."""
    turns = (st.session_state.get("pf_chat") or [])[-limit:]
    lines = []
    for turn in turns:
        lines.append(f"Student asked: {turn['question']}")
        answer = " ".join((turn.get("text") or "").split())[:220]
        if answer:
            lines.append(f"PocketFriend answered: {answer}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Left zone: sources
# ---------------------------------------------------------------------------


def render_sources_zone() -> None:
    ui.render(ui.zonehead("Sources", "layers"))
    rt.source_picker("ask")
    ui.spacer("md")

    snapshot = rt.library()
    chunks = sum(snapshot["chunks"].values())
    ui.render(
        ui.kv(
            [
                ("Indexed", f"{len(snapshot['documents'])} PDFs"),
                ("Searchable", f"{chunks} passages"),
            ]
        )
    )
    ui.render(
        ui.text_note(
            "Pick one document to search only that file.",
            tone="quiet",
        )
    )


# ---------------------------------------------------------------------------
# Centre zone: the conversation
# ---------------------------------------------------------------------------


def render_turn(turn: dict, index: int) -> None:
    ui.render(ui.question_bubble(turn["question"]))
    with st.container(key=f"pf-answerbody-{index}"):
        ui.render(ui.answer_head())
        if turn.get("text"):
            st.markdown(turn["text"])
        if turn.get("note"):
            ui.spacer("sm")
            ui.render(
                ui.note(
                    ui.esc(turn["note"]),
                    title=(
                        "Nothing close in your documents"
                        if not turn.get("sources")
                        else "A note from PocketFriend"
                    ),
                    tone="warn",
                )
            )
        sources = turn.get("sources") or []
        if sources:
            ui.render(ui.answer_foot(sources))


def render_conversation() -> list:
    turns = st.session_state.get("pf_chat") or []

    if not turns:
        ui.render(ui.zonehead("Conversation", "ask"))
        ui.render(
            ui.empty(
                "Ask about anything in your material",
                "PocketFriend searches your pages, then answers in its own words - and shows "
                "you exactly which pages it used.",
                mark="ask",
            )
        )
        ui.render(ui.section("Try one of these", mark="spark"))
        columns = st.columns(2)
        for column, suggestion in zip(columns, SUGGESTIONS):
            with column:
                with st.container(key=f"pf-prompt-ask-{SUGGESTIONS.index(suggestion)}"):
                    if st.button(suggestion, key=f"ask_suggest_{SUGGESTIONS.index(suggestion)}"):
                        st.session_state["pf_ask_suggest"] = suggestion
        return turns

    head, clear = st.columns([4, 1], vertical_alignment="center")
    with head:
        ui.render(
            ui.zonehead(
                f"Conversation · {len(turns)} question{'' if len(turns) == 1 else 's'}", "ask"
            )
        )
    with clear:
        if ui.button("Clear", key="ask_clear", icon="trash", width="stretch"):
            st.session_state["pf_chat"] = []
            st.rerun()

    for index, turn in enumerate(turns):
        render_turn(turn, index)
        if index < len(turns) - 1:
            ui.render(ui.rule())
    return turns


def render_composer(busy: bool) -> tuple[bool, str]:
    """The question box, pinned to the end of the conversation.

    `busy` greys the box out for the whole of a turn, so a question cannot be
    typed or sent a second time while the model is still working on the first.
    """
    clicked = False
    with st.container(key="pf-composer-ask"):
        question = st.text_area(
            "Your question",
            key="pf_question",
            placeholder="Ask a question about your material",
            height=96,
            label_visibility="collapsed",
            disabled=busy,
        )
        hint, action = st.columns([4, 1], vertical_alignment="bottom")
        with hint:
            st.caption("Answers come from your documents only.")
        with action:
            clicked = ui.button(
                "Ask",
                key="ask_submit",
                type="primary",
                icon="send",
                width="stretch",
                disabled=busy,
            )
    return clicked, (question or "").strip()


def ask(question: str) -> None:
    """Run one turn of the conversation, then start a fresh render."""
    st.session_state["pf_asking"] = True
    try:
        turns = st.session_state.setdefault("pf_chat", [])
        with rt.working("Thinking about your question…"):
            answer = rt.guard(rag.answer_question)(
                question,
                history=history_for_retrieval(),
                filename=rt.scope(),
            )

        if answer is not None:
            # A note that arrives with a grounded answer is about the model, not
            # the answer, so it is a message; a note on an ungrounded answer
            # belongs to the turn, next to the refusal it explains.
            if answer.note and answer.grounded:
                rt.flash("warn", answer.note)
            turns.append(
                {
                    "question": question,
                    "text": answer.text,
                    "sources": answer.sources,
                    "note": answer.note if not answer.grounded else "",
                }
            )
    finally:
        st.session_state["pf_asking"] = False
        st.session_state["pf_clear_question"] = True
    st.rerun()


# ---------------------------------------------------------------------------
# Right zone: evidence
# ---------------------------------------------------------------------------


def render_evidence_zone() -> None:
    ui.render(ui.zonehead("Evidence", "quote"))
    turns = st.session_state.get("pf_chat") or []
    sources = turns[-1].get("sources") if turns else []

    if not sources:
        ui.render(
            ui.empty(
                "No passages yet",
                "The pages PocketFriend used for the latest answer appear here.",
                mark="quote",
            )
        )
        return

    ui.render(ui.evidence(sources))
    best = max(float(source.score) for source in sources)
    ui.render(
        ui.text_note(
            f"Closest match {best:.2f}. Below 0.35 is treated as no match.",
            tone="quiet",
        )
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


def render() -> None:
    rt.warm_up()

    snapshot = rt.library()
    documents = snapshot["documents"]
    chosen = rt.scope()

    meta = [(f"{len(documents)} PDFs indexed", "accent")]
    if chosen:
        meta.append((f"Searching one document: {chosen}", "warn"))

    with st.container(key="pf-bar-ask"):
        head, actions = st.columns([4, 1.3], vertical_alignment="center")
        with head:
            ui.render(ui.topbar("Ask your documents", SUBTITLE, meta=meta))
        with actions:
            if ui.button(
                "Clear chat",
                key="ask_clear_top",
                icon="trash",
                width="stretch",
            ):
                st.session_state["pf_chat"] = []
                st.session_state["pf_question"] = ""
                st.rerun()

    if not rt.require_documents("answer questions", mark="ask"):
        return
    rt.ai_block()

    # a question handed over from Home, or from a suggestion chip
    draft = st.session_state.pop("pf_ask_draft", None)
    suggestion = st.session_state.pop("pf_ask_suggest", None)
    if draft is not None:
        st.session_state["pf_question"] = draft
    if suggestion:
        st.session_state["pf_question"] = suggestion

    left, centre, right = st.columns([1.05, 2.5, 1.25], gap="medium")

    with left:
        with st.container(key="pf-zone-wide-ask-sources"):
            with st.container(key="pf-scroll-ask-sources"):
                render_sources_zone()

    with centre:
        with st.container(key="pf-zone-wide-ask-conversation"):
            with st.container(key="pf-scroll-ask-conversation"):
                render_conversation()

            if st.session_state.pop("pf_clear_question", False):
                st.session_state["pf_question"] = ""

            busy = bool(st.session_state.get("pf_asking"))
            clicked, typed = render_composer(busy)
            asked = typed if (clicked or busy or suggestion) else ""
            if clicked and not asked:
                ui.render(ui.text_note("Type a question first, then press Ask.", tone="quiet"))
            if asked and not busy:
                # One pass to grey the composer out, the next one to do the work,
                # so the box really is disabled while the answer is generated.
                st.session_state["pf_asking"] = True
                st.rerun()
            if asked and busy:
                ask(asked)

    with right:
        with st.container(key="pf-zone-wide-ask-evidence"):
            with st.container(key="pf-scroll-ask-evidence"):
                render_evidence_zone()
