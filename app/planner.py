"""Study planning and the daily action plan.

Both features follow the same rule: Python decides the schedule, Gemma does the
writing. Dates, deadlines, ordering and page references are computed here, so
the plan is correct even when the local model is vague.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional, Sequence

from . import config, database
from .gemma import ModelNotFoundError, OllamaUnavailableError, generate
from .prompts import (
    daily_explanation_prompt,
    focus_tip_prompt,
    study_plan_days_prompt,
)
from .rag import Source, build_context, gather_context_for

# Longest slice of one page's text sent to the model per plan day. Enough for a
# heading and its definition, short enough that a two-week plan still fits.
MAX_DAY_CONTEXT_CHARS = 700

# Suggested length per task, in minutes. A plain default the student can see and
# adjust by hand, never a number the model invented.
TIME_ESTIMATES = {"high": 60, "medium": 45, "low": 30}


class PlannerError(RuntimeError):
    """A study plan could not be built."""


@dataclass
class StudyDay:
    """One day of a study plan."""

    day_number: int
    date: date
    topics: list[str] = field(default_factory=list)
    hours: float = 2.0
    reading: str = ""
    bullets: list[str] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    generated: bool = False  # True when Gemma wrote the detail

    @property
    def label(self) -> str:
        return f"Day {self.day_number}"


@dataclass
class StudyPlanResult:
    """A finished plan, ready to render and to save."""

    exam_name: str
    exam_date: date
    total_days: int
    hours_per_day: float
    topics: list[str] = field(default_factory=list)
    days: list[StudyDay] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    plan_text: str = ""
    ai_notes: str = ""

    def to_markdown(self) -> str:
        return render_plan_markdown(self)


@dataclass
class DailyItem:
    """One entry on today's action list."""

    title: str
    kind: str  # "task" or "study"
    minutes: int
    detail: str = ""
    sources: list[Source] = field(default_factory=list)
    task_id: Optional[int] = None
    due_label: str = ""
    priority: str = ""
    note: str = ""


@dataclass
class DailyPlan:
    """Today's ordered action list plus Gemma's explanation of the order."""

    date: date
    items: list[DailyItem] = field(default_factory=list)
    rationale: str = ""
    exam_summary: str = ""
    sources: list[Source] = field(default_factory=list)
    total_minutes: int = 0
    warning: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_topics(text: str) -> list[str]:
    """Split a free-text topic list into clean topic names."""
    if not text:
        return []
    raw = re.split(r"[,\n;•]| and ", text)
    seen: list[str] = []
    for topic in raw:
        cleaned = re.sub(r"^\s*[-*\d.)\s]+", "", topic).strip().strip(".")
        if cleaned and len(cleaned) > 1 and cleaned.lower() not in {
            item.lower() for item in seen
        }:
            seen.append(cleaned)
    return seen


def _topics_for(exam_name: str, topics: Sequence[str]) -> list[str]:
    """Fall back to the exam name so a plan is never empty."""
    return list(topics) if topics else [exam_name]


def assign_topics_to_days(topics: Sequence[str], days: int) -> list[list[str]]:
    """Spread topics across days.

    Topics cycle in order, so every topic gets its own day until the days run
    out, and extra topics wrap onto the earlier days. Empty days become
    consolidation days, which is what a real revision timetable looks like.
    """
    buckets: list[list[str]] = [[] for _ in range(max(1, days))]
    for index, topic in enumerate(topics):
        buckets[index % len(buckets)].append(topic)
    return buckets


def format_page_references(sources: Sequence[Source]) -> str:
    """Turn real retrieved sources into a readable reading list."""
    by_file: dict[str, set[int]] = {}
    for source in sources:
        if source.page > 0:
            by_file.setdefault(source.filename, set()).add(source.page)
    if not by_file:
        return ""
    parts = []
    for filename in sorted(by_file):
        pages = sorted(by_file[filename])
        parts.append(f"{filename} p. {_format_pages(pages)}")
    return ", ".join(parts)


def _format_pages(pages: Sequence[int]) -> str:
    """Collapse consecutive page numbers: [2,3,4,7] -> '2-4, 7'."""
    if not pages:
        return ""
    ranges: list[str] = []
    start = previous = pages[0]
    for page in pages[1:]:
        if page == previous + 1:
            previous = page
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = page
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ", ".join(ranges)


def _collect_sources(topic_sources: dict[str, list[Source]]) -> list[Source]:
    """Flatten topic sources, keeping the best chunk per page."""
    best: dict[tuple, Source] = {}
    for sources in topic_sources.values():
        for source in sources:
            key = (source.filename, source.page)
            if key not in best or source.score > best[key].score:
                best[key] = source
    return sorted(best.values(), key=lambda s: (-s.score, s.filename, s.page))


# ---------------------------------------------------------------------------
# Study plan
# ---------------------------------------------------------------------------


def build_study_plan(
    exam_name: str,
    exam_date: date,
    hours_per_day: float = 2.0,
    topics_text: str = "",
    use_documents: bool = True,
    today: Optional[date] = None,
    model: Optional[str] = None,
) -> StudyPlanResult:
    """Build a day-by-day revision plan for an exam.

    The schedule, hours and page references are computed here. Gemma only fills
    in the three practice bullets per day, and only when it is available and
    returns something usable.
    """
    exam_name = (exam_name or "").strip()
    if not exam_name:
        raise PlannerError("Give the exam a name so the plan can be saved.")
    if not isinstance(exam_date, date):
        raise PlannerError("Choose a valid exam date.")
    if not isinstance(today, date):
        today = date.today()

    days_available = (exam_date - today).days
    if days_available < 0:
        raise PlannerError(
            "That exam date has already passed. Pick a future date and try again."
        )
    if days_available == 0:
        raise PlannerError(
            "The exam is today. Create a plan for an exam at least one day away."
        )

    total_days = min(days_available, config.MAX_PLAN_DAYS)
    hours = max(0.5, min(float(hours_per_day or 2), 12))
    topics = _topics_for(exam_name, parse_topics(topics_text))

    # Retrieve material per topic so page references are real.
    topic_sources: dict[str, list[Source]] = {}
    if use_documents:
        for topic in topics:
            topic_sources[topic] = [
                source
                for source in gather_context_for(topic, n_results=3)
                if source.score >= config.RELEVANCE_THRESHOLD
            ]

    # Topics with the most material come first: that is what the student can
    # actually revise from.
    order = sorted(
        range(len(topics)),
        key=lambda i: (-len(topic_sources.get(topics[i], [])), i),
    )
    topics = [topics[i] for i in order]
    topic_sources = {topic: topic_sources.get(topic, []) for topic in topics}

    buckets = assign_topics_to_days(topics, total_days)
    plan_days: list[StudyDay] = []

    for index, day_topics in enumerate(buckets, start=1):
        sources = _collect_sources({t: topic_sources.get(t, []) for t in day_topics})
        reading = format_page_references(sources)
        day = StudyDay(
            day_number=index,
            date=today + timedelta(days=index),
            topics=list(day_topics),
            hours=hours,
            reading=reading,
            sources=sources,
        )
        if not day_topics:
            # No new material: a consolidation day.
            day.topics = ["Consolidation and practice"]
            day.bullets = [
                "Re-read your notes from the previous days and highlight anything you could not explain out loud.",
                "Answer 5 practice questions on the topics you have already covered.",
                "Write a one-page summary of each topic from memory, then check it against your notes.",
            ]
        else:
            day.bullets = _default_bullets(day_topics, reading)
        plan_days.append(day)

    ai_notes = ""
    if use_documents:
        ai_notes = _enrich_days(plan_days, exam_name, exam_date, model=model)

    result = StudyPlanResult(
        exam_name=exam_name,
        exam_date=exam_date,
        total_days=total_days,
        hours_per_day=hours,
        topics=topics,
        days=plan_days,
        sources=_collect_sources(topic_sources),
    )
    result.plan_text = render_plan_markdown(result)
    if ai_notes:
        result.ai_notes = ai_notes
    return result


def _default_bullets(topics: Sequence[str], reading: str) -> list[str]:
    """Deterministic bullets used when the model is unavailable."""
    label = ", ".join(topics)
    bullets = []
    if reading:
        bullets.append(f"Read {reading} and mark the parts that define {label}.")
    else:
        bullets.append(f"Read your notes on {label} and mark the key definitions.")
    bullets.append(f"Write out the main ideas of {label} in your own words.")
    bullets.append("Complete 5 practice questions, then check your answers.")
    return bullets


def _extract_json_array(text: str) -> Optional[list]:
    """Pull a JSON array out of a model response.

    Small models wrap JSON in prose or code fences and add trailing commas, so
    this tries the strict parse, then a fenced block, then a relaxed pass that
    strips trailing commas. Returns None rather than raising, so a malformed
    response just means "no enrichment".

    More forgiving than `quiz._extract_json_array`, which treats a broken parse
    as a signal to retry the quiz in another format. Here a whole plan has
    already been generated, so salvaging most of it is worth more than a clean
    rejection.
    """
    if not text:
        return None

    candidate = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1).strip()

    for attempt in (candidate, _relax_json(candidate)):
        if not attempt:
            continue
        try:
            parsed = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            return parsed

    start = candidate.find("[")
    if start == -1:
        return None
    depth = 0
    for position in range(start, len(candidate)):
        char = candidate[position]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                for attempt in (candidate[start : position + 1], _relax_json(candidate[start : position + 1])):
                    if not attempt:
                        continue
                    try:
                        parsed = json.loads(attempt)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(parsed, list):
                        return parsed
                return None
    return None


def _relax_json(text: str) -> str:
    """Remove trailing commas and Python-style quoting a small model may emit."""
    relaxed = re.sub(r",\s*([\]}])", r"\1", text)
    return relaxed.replace("'", '"')


def _bullets_from_entry(entry: object) -> Optional[list[str]]:
    """Validate one enrichment entry into a clean list of bullets."""
    if not isinstance(entry, dict):
        return None
    raw = entry.get("bullets")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return None

    bullets: list[str] = []
    for item in raw:
        text = " ".join(str(item).lstrip("-* ").split()).strip("\"' ")
        if text and 10 <= len(text) <= 300:
            bullets.append(text)
    return bullets if len(bullets) >= 2 else None


def _day_context(days: Sequence[StudyDay]) -> dict[int, str]:
    """Retrieval text for each day, as a single labelled block per day.

    One chunk per day. A 1B model follows "the notes for this day" more reliably
    the shorter each block is, and a longer plan would otherwise send a prompt
    the local model cannot hold.
    """
    return {
        day.day_number: " ".join(
            f"[{source.label}] {source.text}".split()
        )
        for day in days
        if (source := _pick_day_source(day))
    }


def _pick_day_source(day: StudyDay) -> Optional[Source]:
    if not day.sources:
        return None
    best = max(day.sources, key=lambda source: source.score)
    # Long chunks crowd out the rest of the plan; keep the start, which is where
    # a definition or heading lives.
    return Source(
        filename=best.filename,
        page=best.page,
        text=" ".join(best.text.split())[:MAX_DAY_CONTEXT_CHARS],
        chunk_id=best.chunk_id,
        score=best.score,
    )


def _is_off_topic(day: StudyDay, bullets: Sequence[str]) -> bool:
    """True when the bullets are plainly about a different day's subject.

    A 1B model given a whole plan at once sometimes answers Day 2 with Day 3's
    topic. That reads as correct on the page, so it is caught here: a day keeps
    its computed checklist unless at least one bullet mentions its own focus.
    """
    words = {
        word
        for topic in day.topics
        for word in re.findall(r"[a-z]{4,}", topic.lower())
    }
    if not words:
        return False
    text = " ".join(bullets).lower()
    return not any(word in text for word in words)


def _enrich_days(
    days: Sequence[StudyDay],
    exam_name: str,
    exam_date: date,
    model: Optional[str] = None,
) -> str:
    """Ask Gemma for the detail on every day in one request.

    One Ollama call covers the whole plan. Days the model skips, mangles or
    answers about the wrong subject keep the checklist Python computed, so a
    partial answer still improves the plan without inventing anything. Returns a
    note when some days fell back.
    """
    targets = [
        day
        for day in days
        if day.topics
        and day.topics != ["Consolidation and practice"]
        and day.sources
    ]
    if not targets:
        return ""

    contexts = _day_context(targets)
    try:
        raw = generate(
            study_plan_days_prompt(
                exam_name=exam_name,
                exam_date=exam_date.strftime("%d %B %Y"),
                hours=targets[0].hours,
                days=[
                    {
                        "day": day.day_number,
                        "topics": ", ".join(day.topics),
                        "notes": contexts.get(day.day_number, ""),
                    }
                    for day in targets
                ],
            ),
            model=model,
            # Three bullets per day is a long JSON answer. The default reply
            # budget cuts it off mid-object, which reads as a total failure
            # rather than a partial one.
            max_tokens=min(260 + 170 * len(targets), 4000),
        )
    except (OllamaUnavailableError, ModelNotFoundError):
        return ""  # Local AI is not usable: keep the deterministic plan.

    entries = _extract_json_array(raw) or []
    by_day: dict[int, list[str]] = {}
    for entry in entries:
        bullets = _bullets_from_entry(entry)
        if bullets is None or not isinstance(entry, dict):
            continue
        day_number = entry.get("day", entry.get("day_number"))
        try:
            day_number = int(day_number)
        except (TypeError, ValueError):
            continue
        by_day.setdefault(day_number, bullets)

    rejected = 0
    for day in targets:
        bullets = by_day.get(day.day_number)
        if not bullets:
            continue
        if _is_off_topic(day, bullets):
            rejected += 1
            del by_day[day.day_number]
            continue
        day.bullets = bullets[:3]
        day.generated = True

    failures = len(targets) - len(by_day)
    if not failures:
        return ""
    if failures == len(targets):
        if rejected:
            return (
                "Gemma's detail was about the wrong topics, so every day uses "
                "the default checklist."
            )
        return "Gemma did not return usable detail, so every day uses the default checklist."
    note = (
        f"{failures} of {len(targets)} day(s) fell back to the default checklist "
        "because Gemma's detail did not parse."
    )
    if rejected:
        note += f" {rejected} of those were about the wrong topic."
    return note


def render_plan_markdown(plan: StudyPlanResult) -> str:
    """Render the plan as markdown for storage and display."""
    lines = [
        f"# {plan.exam_name} Study Plan",
        "",
        f"**Exam date:** {plan.exam_date.strftime('%A %d %B %Y')} "
        f"({database.days_until(plan.exam_date)} days from today)",
        f"**Study time:** {plan.hours_per_day:g} hour(s) per day "
        f"over {plan.total_days} day(s)",
    ]
    if plan.topics:
        lines.append(f"**Topics:** {', '.join(plan.topics)}")
    lines.append("")

    for day in plan.days:
        lines.append(f"## {day.label} — {day.date.strftime('%a %d %b')}")
        lines.append(f"*Focus: {', '.join(day.topics)}*")
        lines.append("")
        for bullet in day.bullets:
            lines.append(f"- {bullet}")
        lines.append("")

    if plan.sources:
        lines.append("## 📚 Sources used")
        for source in plan.sources:
            lines.append(f"- 📄 {source.label}")
        lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Plan -> tasks
# ---------------------------------------------------------------------------

# Prefix on every generated task, so the plan's work can be found again and
# kept in step with the plan it came from. It is also how duplicates are
# avoided: a task carrying this prefix and the same title is the same day of the
# same plan, not a new one.
TASK_SOURCE_PREFIX = "Study plan:"


def task_title_for_day(plan_exam_name: str, day: StudyDay) -> str:
    """The title a plan day gets in the task list."""
    return f"{TASK_SOURCE_PREFIX} {day.label} - {', '.join(day.topics)} ({plan_exam_name})"


def task_description_for_day(day: StudyDay, hours: float) -> str:
    """The bullets and reading list for a day, as the task's own instructions.

    Stored as one line, because that is how the task list renders a description.
    """
    parts = [f"About {hours:g} hour{'s' if hours != 1 else ''}."]
    if day.reading:
        parts.append(f"Reading: {day.reading}.")
    for bullet in day.bullets:
        text = bullet.rstrip(".!?")
        parts.append(f"{text}.")
    return " ".join(part for part in parts if part)


def task_priority_for_day(day: StudyDay, total_days: int) -> str:
    """Priority from the plan itself, using the existing three levels.

    The exam is the deadline, so the last stretch of the plan is the urgent part.
    """
    remaining = total_days - day.day_number
    if remaining <= 1:
        return "high"
    if remaining <= 3:
        return "medium"
    return "low"


def save_plan_tasks(plan: StudyPlanResult) -> list[database.Task]:
    """Store one task per plan day so the daily plan can act on the plan.

    Uses the existing `database.add_task` writer. Tasks already created for the
    same plan day are left alone, so rebuilding a plan or rerunning the page
    never doubles the list. Returns the tasks that exist for this plan.
    """
    existing = {
        task.title: task
        for task in database.list_tasks(include_completed=True)
        if task.title.startswith(TASK_SOURCE_PREFIX)
    }

    saved: list[database.Task] = []
    for day in plan.days:
        title = task_title_for_day(plan.exam_name, day)
        current = existing.get(title)
        if current is not None:
            saved.append(current)
            continue
        task = database.add_task(
            title,
            task_description_for_day(day, day.hours),
            day.date,
            task_priority_for_day(day, plan.total_days),
        )
        existing[title] = task
        saved.append(task)
    return saved


# ---------------------------------------------------------------------------
# Today's plan
# ---------------------------------------------------------------------------


def build_daily_plan(
    today: Optional[date] = None,
    limit: int = 5,
    available_minutes: Optional[int] = None,
    model: Optional[str] = None,
) -> DailyPlan:
    """Decide what to work on today.

    The ordering is entirely deterministic (database.rank_active_tasks) so the
    same inputs always give the same plan. Gemma only adds the explanation and
    an optional per-item note.
    """
    if not isinstance(today, date):
        today = date.today()

    ranked = database.rank_active_tasks(today=today)
    exam = database.next_exam(today=today)

    items: list[DailyItem] = []
    for task in ranked[:limit]:
        items.append(
            DailyItem(
                title=task.title,
                kind="task",
                minutes=TIME_ESTIMATES.get(task.priority, 45),
                task_id=task.id,
                due_label=task.due_label,
                priority=task.priority,
                detail=task.description or "",
            )
        )

    # An exam on the horizon is itself something to work on.
    if exam is not None and len(items) < limit:
        sources = gather_context_for(exam.exam_name, n_results=2)
        sources = [s for s in sources if s.score >= config.RELEVANCE_THRESHOLD]
        days_left = database.days_until(exam.exam_date, today)
        item = DailyItem(
            title=f"Review material for the {exam.exam_name} exam",
            kind="study",
            minutes=60,
            detail=(
                f"{days_left} day(s) to go — focus on the pages below and turn "
                "them into 5 practice questions."
            ),
            sources=sources,
        )
        if sources:
            item.detail = (
                f"{days_left} day(s) to go. Start with {format_page_references(sources)}."
            )
        items.append(item)

    plan = DailyPlan(
        date=today,
        items=items,
        exam_summary=_exam_summary(exam, today),
        sources=[s for item in items for s in item.sources],
    )
    plan.total_minutes = sum(item.minutes for item in items)

    if available_minutes and plan.total_minutes > available_minutes:
        # Keep the list but tell the student honestly how it compares.
        plan.warning = (
            f"This list is about {plan.total_minutes} minutes. That is more than "
            f"the {available_minutes} minutes you said you have, so start at the "
            "top and stop when your time is up."
        )

    if items:
        plan.rationale = _why_this_order(plan)
        add_focus_tip(plan, model=model)
    return plan


def _exam_summary(exam: Optional[database.StudyPlan], today: date) -> str:
    if exam is None:
        return "No exam recorded yet."
    days_left = database.days_until(exam.exam_date, today)
    when = "today" if days_left == 0 else f"in {days_left} day(s)"
    return f"{exam.exam_name} on {exam.exam_date.strftime('%d %B %Y')} ({when})"


def _why_this_order(plan: DailyPlan) -> str:
    """Explain the order using only facts Python already computed.

    Dates and priorities are never handed to the model for narration. A 1B model
    asked to "explain" this ranking produced sentences that contradicted the
    list, so the reasoning is generated here and Gemma is only used for the
    grounded content tip.
    """
    if not plan.items:
        return ""

    first = plan.items[0]
    sentences: list[str] = []

    if first.kind == "task":
        detail = f"{first.due_label.lower()}"
        sentences.append(
            f"**{first.title}** comes first: it is {detail}, and you marked it "
            f"{first.priority} priority."
        )
    else:
        sentences.append(
            f"**{first.title}** comes first because {first.detail or 'your exam is the nearest deadline.'}"
        )

    follow_ups = [item for item in plan.items[1:] if item.kind == "task"]
    if follow_ups:
        overdue = [
            item for item in follow_ups if item.due_label.lower().startswith("overdue")
        ]
        if overdue:
            titles = " and ".join(f"*{item.title}*" for item in overdue[:2])
            sentences.append(
                f"{titles} {'is' if len(overdue) == 1 else 'are'} already overdue, "
                "so it follows immediately."
            )
        else:
            next_item = follow_ups[0]
            sentences.append(
                f"Then **{next_item.title}** ({next_item.due_label.lower()})."
            )

    exam = database.next_exam(today=plan.date)
    if exam is not None:
        days_left = database.days_until(exam.exam_date, plan.date)
        if days_left <= 3 and not any(item.kind == "study" for item in plan.items[1:]):
            sentences.append(
                f"Your **{exam.exam_name}** exam is in {days_left} day(s), so exam "
                "review goes before anything optional."
            )

    return " ".join(sentences)


def add_focus_tip(plan: DailyPlan, model: Optional[str] = None) -> str:
    """Ask Gemma for one grounded tip about the first item with real material.

    Skipped silently when the local AI is unavailable.
    """
    for item in plan.items:
        if not item.sources:
            continue
        try:
            tip = generate(
                focus_tip_prompt(item.title, build_context(item.sources[:1])),
                model=model,
            )
        except (OllamaUnavailableError, ModelNotFoundError):
            return ""
        tip = " ".join(tip.split())
        if tip and len(tip) < 300:
            item.note = tip
            return tip
    return ""


def annotate_items_with_notes(
    plan: DailyPlan, model: Optional[str] = None
) -> None:
    """Add a one-line 'what to watch out for' note to each study item.

    Skipped silently when the local AI is unavailable.
    """
    for item in plan.items:
        if item.note or not item.sources:
            continue
        try:
            note = generate(
                daily_explanation_prompt(item.title, build_context(item.sources[:1])),
                model=model,
            )
        except (OllamaUnavailableError, ModelNotFoundError):
            return
        note = " ".join(note.split())
        if note and len(note) < 300:
            item.note = note