"""Home: the thing you came back to do.

No hero, no marketing. One composer, then what needs doing today, what is
coming up, and what is in the library. Every number comes from the app's own
data; nothing is invented and nothing is hidden behind a marketing panel.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from app import database, planner
from app.ui import components as ui
from app.ui import runtime as rt

QUICK_ACTIONS = [
    ("Ask", "ask", "ask", "Question a document"),
    ("Study Plan", "plan", "plan", "Schedule revision"),
    ("Quiz", "quiz", "quiz", "Test yourself"),
    ("Add PDF", "documents", "upload", "Grow the library"),
]


def is_first_run() -> bool:
    """True while the app still has nothing of the student's in it."""
    if st.session_state.get("pf_onboarding_done"):
        return False
    if rt.document_count() > 0:
        return False
    if database.count_tasks(include_completed=True) > 0:
        return False
    return not database.list_study_plans()


def greeting() -> tuple[str, str]:
    """A short opening line, then the real state of the student's work."""
    hour = datetime.now().hour
    word = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"

    open_tasks = database.count_tasks(include_completed=False)
    exam = database.next_exam()
    documents = rt.document_count()

    if not documents and not open_tasks:
        return word, "Nothing here yet. Add a PDF and PocketFriend can start helping."

    parts = []
    if documents:
        parts.append(f"{documents} document{'' if documents == 1 else 's'} ready to search")
    if open_tasks:
        parts.append(f"{open_tasks} open task{'' if open_tasks == 1 else 's'}")
    if exam:
        days = database.days_until(exam.exam_date)
        if days >= 0:
            parts.append(f"{exam.exam_name} in {days} day{'' if days == 1 else 's'}")
    return word, " · ".join(parts) if parts else "PocketFriend is ready."


def render_composer() -> None:
    """The one input on this page. A question goes straight to Ask."""
    with st.container(key="pf-composer-home"):
        left, right = st.columns([5, 1], vertical_alignment="bottom")
        with left:
            st.text_area(
                "What are you studying today?",
                key="pf_home_question",
                label_visibility="collapsed",
                placeholder="What are you studying today?",
                height=84,
            )
        with right:
            if ui.button(
                "Ask",
                key="home_ask",
                type="primary",
                icon="send",
                width="stretch",
            ):
                start_question()


def start_question(text: str = "") -> None:
    """Hand a question to the Ask page, or explain why it cannot be asked."""
    text = (text or st.session_state.get("pf_home_question", "")).strip()
    if not text:
        rt.flash("warn", "Type a question first, then press Ask.")
        return
    if rt.document_count() == 0:
        rt.flash("warn", "Add a PDF first - answers come from your own pages.")
        rt.go_to("documents")
        return
    st.session_state["pf_ask_draft"] = text
    rt.go_to("ask")


def render_quick_actions() -> None:
    for column, (label, route, mark, _hint) in zip(st.columns(4), QUICK_ACTIONS):
        with column:
            if ui.button(
                label,
                key=f"home_quick_{route}",
                icon=mark,
                width="stretch",
            ):
                rt.go_to(route)


def task_row(task, action: bool = False) -> None:
    """One task, flat, with its real deadline and an optional finish action."""
    minutes = planner.TIME_ESTIMATES.get(task.priority, 45)
    overdue = task.due_label.lower().startswith("overdue")
    meta = [
        (f"{minutes} min", "quiet"),
        (task.due_label, "danger" if overdue else "quiet"),
    ]
    with st.container(key=f"pf-item-task-{task.id}"):
        body, action_column = st.columns([7, 1], vertical_alignment="center")
        with body:
            ui.render(
                ui.item_markup(
                    task.title,
                    meta=meta,
                    note_text=task.description or "",
                    mark="check",
                    glyph_tone="accent" if overdue else "",
                )
            )
        if action:
            with action_column:
                if ui.button(
                    "Done",
                    key=f"home_done_{task.id}",
                    icon="check",
                    help=f"Mark {task.title} as done",
                    width="stretch",
                ):
                    database.set_completed(task.id, True)
                    rt.flash("success", f"Done: {task.title}")
                    st.rerun()


def render_today(ranked: list) -> None:
    ui.render(
        ui.section(
            "Today's focus",
            "The order PocketFriend would plan your day in.",
            aside=f"{len(ranked)} open",
            mark="spark",
        )
    )
    if not ranked:
        ui.render(
            ui.empty(
                "Nothing scheduled",
                "Add a task or set an exam date and your day gets planned automatically.",
                mark="check",
            )
        )
        if ui.button("Add a task", key="home_add_task_empty", icon="plus"):
            rt.go_to("plan")
        return

    for task in ranked[:3]:
        task_row(task, action=True)

    if len(ranked) > 3:
        with st.container(key="pf-item-more-tasks"):
            more, action_column = st.columns([7, 1], vertical_alignment="center")
            with more:
                ui.render(
                    ui.text_note(
                        f"{len(ranked) - 3} more open task{'' if len(ranked) - 3 == 1 else 's'}",
                        tone="quiet",
                    )
                )
            with action_column:
                if st.button("See all", key="home_see_all_tasks", width="stretch"):
                    rt.go_to("plan")


def render_upcoming(tasks: list) -> None:
    upcoming = [task for task in tasks if not task.completed][:4]
    ui.render(ui.section("Coming up", aside="Next open tasks", mark="clock"))
    if not upcoming:
        ui.render(ui.text_note("No open tasks left.", tone="quiet"))
        return
    for task in upcoming:
        task_row(task)


def render_library() -> None:
    snapshot = rt.library()
    documents = snapshot["documents"]
    pages = snapshot["pages"]

    ui.render(
        ui.section(
            "Your library",
            aside=f"{len(documents)} PDF{'' if len(documents) == 1 else 's'}",
            mark="file",
        )
    )
    if not documents:
        ui.render(
            ui.empty(
                "No documents yet",
                "Upload lecture notes or a revision sheet and ask questions about them.",
                hint="Everything stays on this computer.",
                mark="file",
            )
        )
        if ui.button("Upload a PDF", key="home_upload", type="primary", icon="upload"):
            rt.go_to("documents")
        return

    ui.render(
        ui.list_rows(
            [(name, f"{pages.get(name, 0)} pages") for name in documents[:5]],
            mark="file",
        )
    )
    if len(documents) > 5:
        ui.render(ui.text_note(f"and {len(documents) - 5} more", tone="quiet"))
    if ui.button("Manage documents", key="home_manage_docs", icon="folder"):
        rt.go_to("documents")


def render_plan(plan) -> None:
    if not plan:
        return
    days = database.days_until(plan.exam_date)
    remaining = (
        f"In {days} day{'' if days == 1 else 's'}"
        if days >= 0
        else "Exam date has passed"
    )
    ui.render(ui.section("Active study plan", mark="plan"))
    with st.container(key="pf-item-plan-home"):
        ui.render(
            ui.item_markup(
                plan.exam_name,
                meta=[
                    (plan.exam_date.strftime("%a %d %b"), "accent"),
                    (remaining, "quiet"),
                    (
                        f"{plan.hours_per_day:g}h a day"
                        if plan.hours_per_day
                        else "Day by day",
                        "quiet",
                    ),
                ],
                note_text=plan.topics or "",
                mark="plan",
                glyph_tone="accent",
            )
        )
    if ui.button("Open study plan", key="home_open_plan", icon="plan"):
        rt.go_to("plan")


def render_first_run() -> None:
    ui.render(ui.section("Start here", "Two steps, then PocketFriend does the rest.", mark="spark"))
    ui.render(
        ui.steps(
            [
                ("Add your material", "Upload lecture notes or a revision sheet as a PDF."),
                ("Ask, plan or quiz", "Ask a question, build a study plan, or take a quiz."),
                ("Stays on this computer", "Nothing is uploaded. Gemma runs through Ollama."),
            ]
        )
    )
    ui.spacer("md")
    left, right = st.columns(2)
    if ui.button(
        "Upload a PDF", key="first_upload", type="primary", icon="upload", width="stretch"
    ):
        rt.go_to("documents")
    if ui.button("Load sample material", key="first_demo", width="stretch"):
        st.session_state["pf_autoload_demo"] = True
        rt.go_to("documents")


def render() -> None:
    word, summary = greeting()

    with st.container(key="pf-bar-home"):
        head, actions = st.columns([4, 1.2], vertical_alignment="center")
        with head:
            ui.render(ui.topbar(word, summary, eyebrow="PocketFriend"))
        with actions:
            if ui.button(
                "New question",
                key="home_new_question",
                type="primary",
                icon="plus",
                width="stretch",
            ):
                st.session_state["pf_ask_draft"] = ""
                rt.go_to("ask")

    if is_first_run():
        render_first_run()
        return

    render_composer()
    ui.spacer("md")
    render_quick_actions()
    ui.spacer("lg")

    ranked = database.rank_active_tasks()
    everything = database.list_tasks(include_completed=True)
    focus_ids = {task.id for task in ranked[:3]}
    upcoming = [task for task in everything if task.id not in focus_ids]

    left, right = st.columns([1.55, 1], gap="large")

    with left:
        with st.container(key="pf-sheet-home-focus"):
            render_today(ranked)
            ui.spacer("md")
            ui.render(ui.rule())
            render_upcoming(upcoming)

    with right:
        exam = database.next_exam()
        with st.container(key="pf-sheet-home-side"):
            render_plan(exam)
            if exam:
                ui.spacer("md")
                ui.render(ui.rule())
            render_library()
