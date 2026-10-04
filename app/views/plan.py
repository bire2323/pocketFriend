"""Study plan: one workspace for the plan, the tasks and today.

The three things that used to be separate pages answer one question - what am I
learning, what do I have to do, and what do I do next - so they live on one
screen: today's focus on the left with the task list, the study plan on the
right. `planner.build_study_plan`, `planner.build_daily_plan` and the
`database` task helpers are called exactly as they were before.
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from app import database, planner
from app.ui import components as ui
from app.ui import runtime as rt

SUBTITLE = "Your exam, your tasks and today's list, in one place."

PRIORITIES = ["High", "Medium", "Low"]

PLAN_KEY = "pf_plan_result"
DAILY_KEY = "pf_daily_plan"
OPEN_KEY = "pf_plan_form_open"

# Home used to deep-link into a numbered tab; map those onto this page's blocks.
LEGACY_FOCUS = {0: "plan", 1: "task", 2: "today"}


def render_header() -> None:
    tasks = database.count_tasks()
    documents = rt.document_count()
    exam = database.next_exam()

    meta = [
        (f"{tasks} open task{'' if tasks == 1 else 's'}", "quiet"),
        (f"{documents} document{'' if documents == 1 else 's'} to draw on", "quiet"),
    ]
    if exam:
        days = database.days_until(exam.exam_date)
        meta.append(
            (f"{exam.exam_name} · {days} day{'' if days == 1 else 's'} away", "danger" if days <= 3 else "accent")
        )

    with st.container(key="pf-bar-plan"):
        head, actions = st.columns([4, 1.4], vertical_alignment="center")
        with head:
            ui.render(ui.topbar("Study plan", SUBTITLE, meta=meta))
        with actions:
            if ui.button(
                "New study plan",
                key="plan_new_top",
                type="primary",
                icon="plus",
                width="stretch",
            ):
                st.session_state[OPEN_KEY] = not st.session_state.get(OPEN_KEY)


# ---------------------------------------------------------------------------
# Left: today's focus
# ---------------------------------------------------------------------------


def render_task_row(task, key_prefix: str, actions: bool = True) -> None:
    """A task with its real deadline, priority and a checkbox."""
    meta = [(task.priority.title(), "danger" if task.priority == "high" else "quiet")]
    if task.due_date or task.due_label:
        meta.append((task.due_label, "quiet"))

    with st.container(key=f"pf-item-{key_prefix}-{task.id}"):
        check, body, remove = st.columns([0.6, 7, 0.9], vertical_alignment="center")
        with check:
            done = st.checkbox(
                "Done",
                value=task.completed,
                key=f"task_done_{task.id}",
                label_visibility="collapsed",
                help=task.title,
            )
        with body:
            ui.render(
                ui.item_markup(
                    task.title,
                    meta=meta,
                    note_text=task.description or "",
                    mark="check",
                    done=task.completed,
                )
            )
        if actions:
            with remove:
                deleted = ui.button(
                    "Delete",
                    key=f"task_delete_{task.id}",
                    icon="trash",
                    help=f"Delete {task.title}",
                    width="stretch",
                )
        else:
            deleted = False

    if done != task.completed:
        database.set_completed(task.id, done)
        st.rerun()
    if deleted:
        database.delete_task(task.id)
        rt.flash("success", f"{task.title} was deleted.")
        st.rerun()


def add_task() -> None:
    title = (st.session_state.get("task_title") or "").strip()
    if not title:
        rt.flash("warn", "Give the task a name first.")
        return
    due = st.session_state.get("task_due")
    database.add_task(
        title,
        st.session_state.get("task_note") or "",
        due if isinstance(due, date) else None,
        (st.session_state.get("task_priority") or "Medium").lower(),
    )
    st.session_state["pf_reset_task"] = True
    rt.flash("success", f"{title} added to your tasks.")


def render_add_task() -> None:
    # The widget keys can only be reset before the widgets are created.
    if st.session_state.pop("pf_reset_task", False):
        st.session_state["task_title"] = ""
        st.session_state["task_note"] = ""

    with st.container(key="pf-composer-task"):
        ui.render(ui.section("Add a task", "One line is enough.", mark="plus"))
        st.text_input("Task", key="task_title", label_visibility="collapsed",
                      placeholder="Redo normalisation exercises")
        priority, due, add = st.columns([1, 1, 1], vertical_alignment="bottom")
        with priority:
            st.selectbox("Priority", PRIORITIES, index=1, key="task_priority",
                         label_visibility="collapsed")
        with due:
            st.date_input("Due date", key="task_due", value=None, label_visibility="collapsed")
        with add:
            if ui.button("Add", key="task_add", type="primary", icon="plus", width="stretch"):
                add_task()
                st.rerun()
        st.text_input("Notes (optional)", key="task_note", label_visibility="collapsed",
                      placeholder="Chapter 4, questions 1-10")


def group_tasks() -> tuple[list, list, list]:
    """Today, upcoming and completed, using the app's own ranking for today."""
    everything = database.list_tasks(include_completed=True)
    ranked = database.rank_active_tasks()
    ranked_ids = {task.id for task in ranked[:5]}
    today = ranked[:5]
    upcoming = [
        task
        for task in everything
        if not task.completed and task.id not in ranked_ids
    ]
    upcoming.sort(key=lambda task: (task.due_date or date.max, -database.priority_score(task)))
    completed = [task for task in everything if task.completed]
    return today, upcoming, completed


def render_task_groups() -> None:
    today, upcoming, completed = group_tasks()
    total_open = len(today) + len(upcoming)

    ui.render(
        ui.section(
            "Tasks",
            "Next up is ordered by deadline and priority; Plan my day is the honest answer "
            "to what today looks like.",
            aside=f"{total_open} open",
            mark="list",
        )
    )

    if total_open == 0 and not completed:
        ui.render(
            ui.empty(
                "No tasks yet",
                "Add one above, or build a study plan and PocketFriend will suggest what "
                "to revise.",
                mark="list",
            )
        )
        return

    if today:
        ui.render(ui.zonehead("Next up", "target"))
        for task in today:
            render_task_row(task, "task-today")

    if upcoming:
        ui.spacer("sm")
        ui.render(ui.zonehead("Upcoming", "clock"))
        for task in upcoming[:8]:
            render_task_row(task, "task-upcoming")
        if len(upcoming) > 8:
            ui.render(ui.text_note(f"and {len(upcoming) - 8} more", tone="quiet"))

    if completed:
        ui.spacer("sm")
        ui.render(ui.zonehead(f"Completed · {len(completed)}", "check"))
        for task in completed[:6]:
            render_task_row(task, "task-done")


def render_daily_plan() -> None:
    """Today's ordered list, with the honest reason it is in that order."""
    minutes = st.session_state.get("today_minutes", 90)

    plan = st.session_state.get(DAILY_KEY)
    if plan is None:
        ui.render(
            ui.empty(
                "Plan my day",
                "Tell PocketFriend how long you have. It reads your tasks and exam dates, "
                "then puts the day in order.",
                mark="spark",
            )
        )
        control, button = st.columns([1, 1], vertical_alignment="bottom")
        with control:
            st.number_input(
                "Minutes available",
                min_value=15,
                max_value=480,
                value=int(minutes),
                step=15,
                key="today_minutes",
                help="PocketFriend lists everything worth doing and tells you honestly if "
                "that is more than this.",
            )
        with button:
            if ui.button("Plan my day", key="today_build", type="primary",
                         icon="spark", width="stretch"):
                with rt.working("Deciding what matters most today…"):
                    built = rt.guard(planner.build_daily_plan)(
                        limit=6, available_minutes=int(minutes)
                    )
                if built is not None:
                    st.session_state[DAILY_KEY] = built
                    st.rerun()
        return

    ui.render(
        ui.nums(
            [
                {"value": f"{plan.total_minutes} min", "label": "Planned"},
                {"value": str(len(plan.items)), "label": "Items"},
                {
                    "value": "Yes" if plan.exam_summary else "None",
                    "label": "Exam ahead",
                },
            ]
        )
    )
    if plan.warning:
        ui.render(ui.note(ui.esc(plan.warning), title="More than you have time for", tone="warn"))
    if plan.exam_summary:
        ui.render(ui.text_note(plan.exam_summary, tone="quiet"))

    if not plan.is_empty:
        for index, item in enumerate(plan.items):
            meta = [(f"{item.minutes} min" if item.minutes else "Study", "quiet")]
            if item.due_label:
                meta.append((item.due_label, "quiet"))
            with st.container(key=f"pf-item-today-{index}"):
                ui.render(
                    ui.item_markup(
                        item.title,
                        meta=meta,
                        note_text=item.detail or item.note or "",
                        mark="list",
                    )
                )

    if plan.rationale:
        ui.spacer("sm")
        ui.render(ui.panel("Why this order", ui.esc(plan.rationale)))

    if ui.button("Plan again", key="today_rebuild", icon="refresh", width="stretch"):
        st.session_state.pop(DAILY_KEY, None)
        st.rerun()


# ---------------------------------------------------------------------------
# Right: the study plan
# ---------------------------------------------------------------------------


def build_plan() -> None:
    exam_name = (st.session_state.get("plan_exam_name") or "").strip()
    exam_date = st.session_state.get("plan_exam_date")
    hours = float(st.session_state.get("plan_hours") or 2.0)
    topics_text = st.session_state.get("plan_topics") or ""
    use_documents = bool(st.session_state.get("plan_use_documents"))

    if not exam_name:
        rt.flash("warn", "Give the exam a name first, so the plan has a title.")
        return
    if not isinstance(exam_date, date):
        rt.flash("warn", "Pick the date of the exam.")
        return
    if use_documents and not rt.document_count():
        use_documents = False

    with rt.working("Building your plan…"):
        result = rt.guard(planner.build_study_plan)(
            exam_name, exam_date, hours, topics_text, use_documents
        )
    if result is None:
        return

    st.session_state[PLAN_KEY] = result
    # Close the form and drop it from session state, so the rerun below renders
    # the result instead of the form that would otherwise overwrite it.
    st.session_state[OPEN_KEY] = False
    rt.guard(database.save_study_plan)(
        exam_name,
        exam_date,
        planner.render_plan_markdown(result),
        result.hours_per_day,
        ", ".join(result.topics),
        result.total_days,
    )
    tasks = rt.guard(planner.save_plan_tasks)(result) or []

    message = f"Your {result.total_days}-day plan for {result.exam_name} is ready."
    if result.ai_notes:
        message += f" {result.ai_notes}"
    if tasks:
        message += (
            f" It is on your task list as {len(tasks)} task"
            f"{'' if len(tasks) == 1 else 's'}, so it shows up in today's plan."
        )
    rt.flash("success", message)
    st.rerun()


def render_plan_form() -> None:
    has_documents = rt.document_count() > 0
    with st.container(key="pf-sheet-plan-form"):
        ui.render(ui.section("Build a study plan", "An exam, a date, and how much time you have.",
                             mark="plan"))
        name_column, date_column = st.columns([1.4, 1])
        with name_column:
            st.text_input("Exam name", key="plan_exam_name", placeholder="Database Systems")
        with date_column:
            st.date_input("Exam date", key="plan_exam_date",
                          value=date.today() + timedelta(days=14))

        hours_column, use_column = st.columns([1, 1], vertical_alignment="bottom")
        with hours_column:
            st.number_input(
                "Hours per day",
                min_value=0.5,
                max_value=12.0,
                value=2.0,
                step=0.5,
                key="plan_hours",
                help="How many focused hours you can give this subject each day.",
            )
        with use_column:
            st.toggle(
                "Build it from my documents",
                value=has_documents,
                key="plan_use_documents",
                disabled=not has_documents,
                help=(
                    "Pages you uploaded fill in the detail for each day."
                    if has_documents
                    else "Upload a PDF first and this fills itself in."
                ),
            )
        st.text_area(
            "Topics to cover",
            key="plan_topics",
            placeholder="One per line, or separated by commas",
            height=88,
        )
        if ui.button("Build my plan", key="plan_build", type="primary",
                     icon="spark", width="stretch"):
            build_plan()
        if not has_documents:
            ui.render(
                ui.text_note(
                    "No documents yet, so this plan comes from the exam date and your topics. "
                    "Add a PDF and every day fills in with real pages.",
                    tone="quiet",
                )
            )


def render_plan_result(result) -> None:
    ui.render(
        ui.section(
            "Your plan",
            f"{result.total_days} days · {result.hours_per_day:g} hours a day",
            aside=result.exam_date.strftime("%a %d %b %Y"),
            mark="plan",
        )
    )
    ui.render(ui.tags([(result.exam_name, "accent")] + [(topic, "quiet") for topic in result.topics[:6]]))

    with st.container(key="pf-sheet-plan-result"):
        for day in result.days:
            ui.render(
                ui.day(
                    day.day_number,
                    day.date.strftime("%a %d %b"),
                    day.topics,
                    day.bullets,
                    day.reading,
                )
            )

        ui.download_button(
            "Save as Markdown",
            planner.render_plan_markdown(result),
            file_name=f"{result.exam_name.lower().replace(' ', '-')}-plan.md",
            mime="text/markdown",
            icon="download",
            width="stretch",
            key="plan_download",
        )

    if result.sources:
        ui.spacer("sm")
        ui.render(ui.section("Pages this plan is built on", mark="quote"))
        ui.render(ui.evidence(result.sources[:4]))


def render_active_plan() -> None:
    result = st.session_state.get(PLAN_KEY)
    open_form = st.session_state.get(OPEN_KEY)
    if result is None and not open_form:
        open_form = True

    if result is not None and not open_form:
        render_plan_result(result)
        if ui.button("Build another plan", key="plan_reopen", icon="plus", width="stretch"):
            st.session_state[OPEN_KEY] = True
            st.rerun()
        return

    render_plan_form()
    if result is not None:
        if ui.button("Close", key="plan_close", icon="close", width="stretch"):
            st.session_state[OPEN_KEY] = False
            st.rerun()
        ui.render(ui.section("Current plan", mark="plan"))
        render_plan_result(result)


def render_saved_plans() -> None:
    plans = database.list_study_plans()
    if not plans:
        return

    ui.render(ui.section("Saved plans", aside="Soonest exam first", mark="clock"))
    for plan in plans[:5]:
        days = database.days_until(plan.exam_date)
        meta = [
            (plan.exam_date.strftime("%a %d %b %Y"), "quiet"),
            (
                f"{days} day{'' if days == 1 else 's'} away" if days >= 0 else "Past",
                "accent" if days >= 0 else "quiet",
            ),
        ]
        if plan.hours_per_day:
            meta.append((f"{plan.hours_per_day:g}h a day", "quiet"))
        with st.container(key=f"pf-item-plan-{plan.id}"):
            info, delete = st.columns([7, 0.8], vertical_alignment="center")
            with info:
                ui.render(
                    ui.item_markup(
                        plan.exam_name,
                        meta=meta,
                        note_text=plan.topics or "",
                        mark="plan",
                    )
                )
            with delete:
                removed = ui.button(
                    "Delete",
                    key=f"plan_delete_{plan.id}",
                    icon="trash",
                    help=f"Delete the {plan.exam_name} plan",
                    width="stretch",
                )
        if removed:
            database.delete_study_plan(plan.id)
            st.session_state.pop(PLAN_KEY, None)
            rt.flash("success", f"The {plan.exam_name} plan was deleted.")
            st.rerun()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def render() -> None:
    rt.warm_up()
    render_header()
    rt.ai_block()

    # older links asked for a numbered section; honour it by opening that block
    legacy = LEGACY_FOCUS.get(st.session_state.pop("pf_plan_tab", None))
    if legacy == "plan":
        st.session_state[OPEN_KEY] = True
    elif legacy == "task":
        st.session_state["task_title"] = st.session_state.get("task_title", "")

    left, right = st.columns([1.45, 1], gap="large")

    with left:
        with st.container(key="pf-sheet-plan-focus"):
            ui.render(
                ui.section(
                    "Today's focus",
                    "What to do next, and why it is next.",
                    aside=date.today().strftime("%A %d %B"),
                    mark="target",
                )
            )
            render_daily_plan()

            ui.spacer("md")
            ui.render(ui.rule())
            render_add_task()
            ui.spacer("md")
            render_task_groups()

    with right:
        render_active_plan()
        ui.spacer("md")
        render_saved_plans()
