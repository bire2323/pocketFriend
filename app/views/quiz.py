"""Quiz: one question at a time, answered from the student's own documents.

A focused session rather than a form: pick a topic, answer, then submit. Nothing
says whether an answer was right until the student submits, so each choice is a
real decision rather than a guess with the answer already on screen. Questions
can be left alone and skipped; the review marks them as unanswered.

Generation and grading are unchanged - this screen drives `quiz.build_quiz` and
`quiz.score_quiz`.
"""

from __future__ import annotations

import streamlit as st

from app import quiz as quiz_backend
from app import rag
from app.ui import components as ui
from app.ui import runtime as rt

SUBTITLE = "Short questions written from your own pages, with the page behind each answer."

DIFFICULTIES = ["Easy", "Medium", "Hard"]
COUNTS = [3, 5, 8, 10]

QUIZ_KEY = "pf_quiz"


def new_quiz_uid(topic: str) -> str:
    """A tag for one quiz, used in its widget keys.

    Streamlit keeps a radio's value under its key, so two quizzes that share a
    key would share an answer. A counter plus a readable slug makes each quiz's
    keys unique and keeps them recognisable in the widget tree.
    """
    slug = "-".join("".join(c if c.isalnum() else "-" for c in topic.lower()).split("-"))
    slug = "-".join(part for part in slug.split("-") if part)[:24] or "quiz"
    number = int(st.session_state.get("pf_quiz_seq", 0)) + 1
    st.session_state["pf_quiz_seq"] = number
    return f"{slug}-{number}"


def render_header(state: dict | None) -> None:
    snapshot = rt.library()
    chosen = rt.scope()
    count = len(snapshot["documents"])

    if chosen:
        scope_tag = (f"Only {chosen}", "warn")
    else:
        scope_tag = (f"{count} document{'' if count == 1 else 's'} to draw from", "accent")

    with st.container(key="pf-bar-quiz"):
        head, actions = st.columns([4, 1.3], vertical_alignment="center")
        with head:
            ui.render(
                ui.topbar(
                    "Quiz",
                    SUBTITLE,
                    eyebrow="Practice",
                    meta=[scope_tag, ("Written by the local model", "quiet")],
                )
            )
        with actions:
            if state:
                if ui.button(
                    "New quiz",
                    key="quiz_quit_top",
                    icon="refresh",
                    width="stretch",
                ):
                    st.session_state.pop(QUIZ_KEY, None)
                    st.rerun()


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def start_quiz() -> bool:
    topic = (st.session_state.get("pf_quiz_topic") or "").strip()
    difficulty = st.session_state.get("pf_quiz_difficulty") or "Medium"
    count = int(st.session_state.get("pf_quiz_count") or 5)
    scope = rt.scope()

    with rt.working("Writing your questions…"):
        # The same context the backend would gather, narrowed to one document when
        # a source is chosen, so the scope picker really does scope the quiz.
        sources = rt.guard(rag.gather_context_for)(topic, n_results=4, filename=scope)
        built = rt.guard(quiz_backend.build_quiz)(topic, count, difficulty, sources=sources)
    if built is None:
        return False

    st.session_state[QUIZ_KEY] = {
        "uid": new_quiz_uid(topic),
        "topic": built.topic,
        "difficulty": built.difficulty,
        "questions": list(built.questions),
        "answers": [None] * len(built.questions),
        "index": 0,
        "submitted": False,
        "result": None,
    }
    rt.flash("success", f"{len(built.questions)} questions on {built.topic} are ready.")
    return True


def render_setup() -> None:
    documents = rt.library()["documents"]

    with st.container(key="pf-sheet-quiz-setup"):
        ui.render(
            ui.section(
                "Choose a topic",
                "Ask about anything in your study material.",
                mark="quiz",
            )
        )
        st.text_input(
            "Topic",
            key="pf_quiz_topic",
            placeholder="Normalization",
        )

        difficulty, count = st.columns(2)
        with difficulty:
            st.selectbox(
                "Difficulty",
                DIFFICULTIES,
                index=1,
                key="pf_quiz_difficulty",
                help="Easy checks definitions, Hard asks you to combine ideas.",
            )
        with count:
            st.selectbox("Questions", COUNTS, index=1, key="pf_quiz_count")

        if ui.button(
            "Start quiz",
            key="quiz_start",
            type="primary",
            icon="play",
            width="stretch",
        ):
            if start_quiz():
                st.rerun()

    ui.spacer("md")
    ui.render(ui.section("Draw from", aside=f"{len(documents)} indexed", mark="layers"))
    rt.source_picker("quiz")
    ui.render(
        ui.text_note(
            "Questions can only come from pages you have uploaded.",
            tone="quiet",
        )
    )


# ---------------------------------------------------------------------------
# Playing
# ---------------------------------------------------------------------------


def answered_count(state: dict) -> int:
    return sum(1 for answer in state["answers"] if answer is not None)


def unanswered_count(state: dict) -> int:
    return len(state["answers"]) - answered_count(state)


def submit_quiz(state: dict) -> None:
    """Grade once, then show the review. The only place feedback appears."""
    result = rt.guard(quiz_backend.score_quiz)(state["questions"], state["answers"])
    if result is None:
        return
    state["result"] = result
    state["submitted"] = True
    st.session_state[QUIZ_KEY] = state
    st.rerun()


def render_question(state: dict) -> None:
    questions = state["questions"]
    index = min(state["index"], len(questions) - 1)
    question = questions[index]
    uid = state["uid"]
    answered = answered_count(state)
    last = index == len(questions) - 1

    ui.render(ui.progress(answered, len(questions)))
    tags = [
        (state["topic"], "accent"),
        (state["difficulty"], "quiet"),
        (f"Question {index + 1} of {len(questions)}", "quiet"),
    ]
    if state["answers"][index] is not None:
        tags.append(("Answer chosen", "ok"))
    else:
        tags.append(("Not answered yet", "quiet"))
    ui.render(ui.tags(tags))
    ui.spacer("sm")

    with st.container(key="pf-sheet-quiz-question"):
        ui.render(ui.question(question.question))
        # Keyed by quiz and question, so a new quiz can never inherit the previous
        # one's selection, and coming back to a question keeps what was picked.
        pick_key = f"quiz_pick_{uid}_{index}"
        st.radio(
            "Choose one answer",
            question.options,
            index=None,
            label_visibility="collapsed",
            key=pick_key,
        )
        # The radio keeps its own value, so read it back rather than relying on a
        # callback: this is what records the answer, and it happens without a
        # rerun, so nothing is revealed.
        picked = st.session_state.get(pick_key)
        if picked is not None and picked in question.options:
            state["answers"][index] = question.options.index(picked)
            st.session_state[QUIZ_KEY] = state

    ui.spacer("md")
    submit_col, skip_col = st.columns(2, vertical_alignment="center")

    with submit_col:
        # Submit stays available on every question, so a student who cannot
        # place an answer is never stuck.
        if ui.button(
            "Submit quiz",
            key=f"quiz_submit_{uid}_{index}",
            type="primary",
            icon="target",
            width="stretch",
            help="Mark the quiz and see the answers with the pages behind them.",
        ):
            submit_quiz(state)
            return

    with skip_col:
        if ui.button(
            "Skip this question" if not last else "Last question",
            key=f"quiz_skip_{uid}_{index}",
            icon="arrow",
            width="stretch",
            disabled=last,
            help="Leave this one blank and come back to it if you can.",
        ):
            state["index"] = index + 1
            st.session_state[QUIZ_KEY] = state
            st.rerun()

    ui.render(
        ui.text_note(
            "Nothing is marked right or wrong until you submit.",
            tone="quiet",
        )
    )


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


def headline_for(percent: int) -> str:
    if percent == 100:
        return "Nothing left to fix here"
    if percent >= 80:
        return "Strong result"
    if percent >= 50:
        return "Halfway there"
    if percent > 0:
        return "Worth another pass"
    return "Read the pages, then retry"


def render_review(state: dict, result: dict) -> None:
    ui.render(ui.section("Review", "Every question, with the page that answered it.", mark="list"))
    for index, question in enumerate(state["questions"]):
        chosen = state["answers"][index]
        right = result["detail"][index]
        source = question.source

        if chosen is None:
            picked_label, picked_tone = "Not answered", "warn"
        else:
            picked_label, picked_tone = f"You chose {ui.letter(chosen)}", "ok" if right else "danger"

        meta = [(picked_label, picked_tone)]
        if source is not None:
            meta.append((f"{source.filename} · page {source.page}", "quiet"))

        with st.container(key=f"pf-item-review-{index}"):
            ui.render(
                ui.item_markup(
                    f"Q{index + 1}. {question.question}",
                    meta=meta,
                    note_text=question.explanation or "",
                    mark="check" if right else "close",
                    glyph_tone="sage" if right else "danger",
                )
            )
            ui.render(ui.answer_rows(question, chosen))
            if source is not None:
                # The page this answer came from, quoted, so the mark above is
                # something the student can check rather than take on trust.
                ui.render(ui.evidence([source]))


def render_results(state: dict) -> None:
    questions = state["questions"]
    result = state.get("result")
    if not result:
        # Defensive: a session marked submitted without a stored result.
        result = rt.guard(quiz_backend.score_quiz)(questions, state["answers"])
        if result is None:
            return
        state["result"] = result

    skipped = unanswered_count(state)

    with st.container(key="pf-sheet-quiz-result"):
        ui.render(
            ui.score(
                f"{result['score']} / {result['total']}",
                headline_for(result["percent"]),
                f"{state['topic']} · {state['difficulty']}",
            )
        )
        st.markdown(quiz_backend.result_message(result))
        if skipped:
            ui.render(
                ui.text_note(
                    f"{skipped} question{'' if skipped == 1 else 's'} left unanswered "
                    "still counted against the score. They are marked in the review below.",
                    tone="warn",
                )
            )

        ui.spacer("sm")
        again_col, home_col = st.columns(2)
        with again_col:
            if ui.button(
                "New quiz",
                key="quiz_again",
                type="primary",
                icon="refresh",
                width="stretch",
            ):
                st.session_state.pop(QUIZ_KEY, None)
                st.rerun()
        with home_col:
            if ui.button(
                "Back to home",
                key="quiz_home",
                icon="home",
                width="stretch",
            ):
                rt.go_to("home")

    ui.spacer("lg")
    render_review(state, result)


def render_active(state: dict) -> None:
    if state.get("submitted") or state["index"] >= len(state["questions"]):
        render_results(state)
        return
    render_question(state)


def render() -> None:
    rt.warm_up()
    state = st.session_state.get(QUIZ_KEY)
    render_header(state)

    if not rt.require_documents("take a quiz", mark="quiz"):
        return
    rt.ai_block()

    if not state:
        render_setup()
        return

    render_active(state)
