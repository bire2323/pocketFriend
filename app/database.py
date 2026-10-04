"""Local SQLite storage for tasks and study plans.

Everything the student types stays in data/pocketfriend.db on their own
machine. No account, no sync, no cloud.

The date and priority ordering that drives "What should I do today?" lives here
in plain Python, so it is predictable and testable instead of being guessed by
a language model.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

from . import config


class DatabaseError(RuntimeError):
    """A storage problem the user should be told about."""


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    due_date    TEXT,
    priority    TEXT    NOT NULL DEFAULT 'medium',
    completed   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS study_plans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_name   TEXT    NOT NULL,
    exam_date   TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    plan_text   TEXT    NOT NULL,
    hours_per_day REAL,
    topics      TEXT,
    total_days  INTEGER
);
"""


@contextmanager
def get_connection(db_path: Optional[str | Path] = None) -> Iterator[sqlite3.Connection]:
    """Open a connection, creating the schema when needed."""
    path = Path(db_path) if db_path else config.DB_PATH
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(SCHEMA)
        yield connection
        connection.commit()
    except sqlite3.Error as exc:
        connection.rollback()
        raise DatabaseError(
            "PocketFriend couldn't read or write its local database.\n\n"
            f"Details: {exc}"
        ) from exc
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """One study task."""

    id: Optional[int]
    title: str
    description: str = ""
    due_date: Optional[date] = None
    priority: str = "medium"
    completed: bool = False
    created_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Task":
        return cls(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            due_date=parse_date(row["due_date"]),
            priority=row["priority"] or "medium",
            completed=bool(row["completed"]),
            created_at=_parse_timestamp(row["created_at"]),
        )

    # -- display helpers ----------------------------------------------------

    @property
    def due_label(self) -> str:
        return format_due_label(self.due_date)

    @property
    def priority_label(self) -> str:
        return {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}.get(
            self.priority, self.priority
        )


def parse_date(value) -> Optional[date]:
    """Parse an ISO date string. Returns None for empty or broken values."""
    if value in (None, "", "None"):
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_timestamp(value) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def format_due_label(due: Optional[date], today: Optional[date] = None) -> str:
    """Human wording for a due date: 'Overdue by 2 days', 'Due tomorrow', ..."""
    if due is None:
        return "No deadline"
    today = today or date.today()
    days = (due - today).days
    if days < 0:
        late = abs(days)
        return f"Overdue by {late} day{'s' if late != 1 else ''}"
    if days == 0:
        return "Due today"
    if days == 1:
        return "Due tomorrow"
    if days <= 7:
        return f"Due in {days} days"
    return f"Due {due.strftime('%d %b %Y')}"


# -- deterministic ordering --------------------------------------------------

# Importance contributed by the priority the student set.
_PRIORITY_WEIGHT = {"high": 30, "medium": 15, "low": 5}

# Urgency contributed by the due date. The buckets are spaced widely so a real
# deadline normally outranks a preference, and the priority the student set
# shifts items within and just across neighbouring buckets. Everything already
# overdue sits above everything that is not.
_URGENCY_OVERDUE_BASE = 85
_URGENCY_OVERDUE_PER_DAY = 2
_URGENCY = {
    0: 60,  # due today
    1: 50,  # tomorrow
}


def _urgency(due: Optional[date], today: date) -> int:
    """How pressing a due date is. Pure integer arithmetic, no model involved."""
    if due is None:
        return 4
    days = (due - today).days
    if days < 0:
        return _URGENCY_OVERDUE_BASE + min(abs(days), 14) * _URGENCY_OVERDUE_PER_DAY
    if days in _URGENCY:
        return _URGENCY[days]
    if days <= 3:
        return 40
    if days <= 7:
        return 28
    if days <= 14:
        return 16
    return 8


def priority_score(task: Task, today: Optional[date] = None) -> int:
    """Ranking score for one task. Higher means "do this first"."""
    today = today or date.today()
    weight = _PRIORITY_WEIGHT.get((task.priority or "medium").lower(), 15)
    return _urgency(task.due_date, today) + weight


def sort_tasks(tasks: list[Task], today: Optional[date] = None) -> list[Task]:
    """Sort tasks most urgent first.

    Ties fall back to the earlier due date and then to the older task, so the
    order is always fully deterministic.
    """
    today = today or date.today()
    far_future = date.max

    def key(task: Task):
        score = priority_score(task, today)
        due_key = task.due_date or far_future
        created_key = task.created_at or datetime.min
        return (-score, due_key, created_key)

    return sorted(tasks, key=key)


def rank_active_tasks(today: Optional[date] = None) -> list[Task]:
    """Every unfinished task, ranked. This is what the daily plan is built on."""
    return sort_tasks([task for task in list_tasks() if not task.completed], today)


# -- CRUD -------------------------------------------------------------------


def add_task(
    title: str,
    description: str = "",
    due_date: Optional[date | str] = None,
    priority: str = "medium",
) -> Task:
    """Create a task. Raises DatabaseError on failure."""
    title = (title or "").strip()
    if not title:
        raise ValueError("A task needs a title.")

    priority = (priority or "medium").strip().lower()
    if priority not in _PRIORITY_WEIGHT:
        priority = "medium"

    due = parse_date(due_date) if not isinstance(due_date, date) else due_date
    created = datetime.now()

    with get_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO tasks (title, description, due_date, priority, completed, created_at)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (
                title,
                (description or "").strip(),
                due.isoformat() if due else None,
                priority,
                created.isoformat(timespec="seconds"),
            ),
        )
        task_id = cursor.lastrowid

    return Task(
        id=task_id,
        title=title,
        description=(description or "").strip(),
        due_date=due,
        priority=priority,
        completed=False,
        created_at=created,
    )


def list_tasks(include_completed: bool = True) -> list[Task]:
    """All tasks, newest first."""
    query = "SELECT * FROM tasks"
    if not include_completed:
        query += " WHERE completed = 0"
    query += " ORDER BY id DESC"
    with get_connection() as connection:
        rows = connection.execute(query).fetchall()
    return [Task.from_row(row) for row in rows]


def get_task(task_id: int) -> Optional[Task]:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return Task.from_row(row) if row else None


def set_completed(task_id: int, completed: bool = True) -> bool:
    """Mark a task done or not done. Returns True when a row changed."""
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE tasks SET completed = ? WHERE id = ?", (1 if completed else 0, task_id)
        )
    return cursor.rowcount > 0


def toggle_task(task_id: int) -> Optional[Task]:
    """Flip a task's completion state and return the updated task."""
    task = get_task(task_id)
    if not task:
        return None
    set_completed(task_id, not task.completed)
    return get_task(task_id)


def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[date | str] = None,
    priority: Optional[str] = None,
) -> Optional[Task]:
    """Change the editable fields of a task. Only provided fields are touched."""
    fields: dict = {}
    if title is not None and title.strip():
        fields["title"] = title.strip()
    if description is not None:
        fields["description"] = description.strip()
    if due_date is not None:
        due = parse_date(due_date) if not isinstance(due_date, date) else due_date
        fields["due_date"] = due.isoformat() if due else None
    if priority is not None:
        clean = priority.strip().lower()
        fields["priority"] = clean if clean in _PRIORITY_WEIGHT else "medium"

    if not fields:
        return get_task(task_id)

    assignments = ", ".join(f"{key} = ?" for key in fields)
    with get_connection() as connection:
        connection.execute(
            f"UPDATE tasks SET {assignments} WHERE id = ?",
            [*fields.values(), task_id],
        )
    return get_task(task_id)


def delete_task(task_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return cursor.rowcount > 0


def count_tasks(include_completed: bool = False) -> int:
    query = "SELECT COUNT(*) FROM tasks"
    if not include_completed:
        query += " WHERE completed = 0"
    with get_connection() as connection:
        return int(connection.execute(query).fetchone()[0])


# ---------------------------------------------------------------------------
# Study plans
# ---------------------------------------------------------------------------


@dataclass
class StudyPlan:
    """A generated study plan, stored as rendered text."""

    id: Optional[int]
    exam_name: str
    exam_date: date
    created_at: Optional[datetime]
    plan_text: str
    hours_per_day: Optional[float] = None
    topics: str = ""
    total_days: Optional[int] = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "StudyPlan":
        return cls(
            id=row["id"],
            exam_name=row["exam_name"],
            exam_date=parse_date(row["exam_date"]) or date.today(),
            created_at=_parse_timestamp(row["created_at"]),
            plan_text=row["plan_text"],
            hours_per_day=row["hours_per_day"],
            topics=row["topics"] or "",
            total_days=row["total_days"],
        )

    @property
    def days_until_exam(self) -> int:
        return (self.exam_date - date.today()).days


def save_study_plan(
    exam_name: str,
    exam_date: date,
    plan_text: str,
    hours_per_day: Optional[float] = None,
    topics: str = "",
    total_days: Optional[int] = None,
) -> StudyPlan:
    """Store a plan so it can be reopened later."""
    exam_name = (exam_name or "").strip()
    if not exam_name:
        raise ValueError("A study plan needs an exam name.")
    if not isinstance(exam_date, date):
        exam_date = parse_date(exam_date) or date.today()

    created = datetime.now()
    with get_connection() as connection:
        cursor = connection.execute(
            """INSERT INTO study_plans
                   (exam_name, exam_date, created_at, plan_text, hours_per_day, topics, total_days)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                exam_name,
                exam_date.isoformat(),
                created.isoformat(timespec="seconds"),
                plan_text,
                hours_per_day,
                topics,
                total_days,
            ),
        )
        plan_id = cursor.lastrowid

    return StudyPlan(
        id=plan_id,
        exam_name=exam_name,
        exam_date=exam_date,
        created_at=created,
        plan_text=plan_text,
        hours_per_day=hours_per_day,
        topics=topics,
        total_days=total_days,
    )


def list_study_plans() -> list[StudyPlan]:
    """Plans with the soonest exam first, so the next deadline is obvious."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM study_plans ORDER BY exam_date ASC, id DESC"
        ).fetchall()
    return [StudyPlan.from_row(row) for row in rows]


def get_study_plan(plan_id: int) -> Optional[StudyPlan]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM study_plans WHERE id = ?", (plan_id,)
        ).fetchone()
    return StudyPlan.from_row(row) if row else None


def delete_study_plan(plan_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM study_plans WHERE id = ?", (plan_id,))
    return cursor.rowcount > 0


def next_exam(today: Optional[date] = None) -> Optional[StudyPlan]:
    """The closest exam that has not passed yet."""
    today = today or date.today()
    upcoming = [plan for plan in list_study_plans() if plan.exam_date >= today]
    return upcoming[0] if upcoming else None


def days_until(target: date, today: Optional[date] = None) -> int:
    """Days from today to a date. Negative when the date has passed."""
    return (target - (today or date.today())).days


def week_start(today: Optional[date] = None) -> date:
    """Monday of the current week, used to place tasks on the daily plan."""
    today = today or date.today()
    return today - timedelta(days=today.weekday())