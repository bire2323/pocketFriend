"""Grounded multiple-choice quizzes.

PocketFriend retrieves material about the chosen topic, asks Gemma to write
questions from that material only, validates whatever comes back, and grades
the student's answers itself.

Two deliberate choices:

* Gemma is never trusted to grade. A string comparison grades an MCQ correctly.
* Gemma is never trusted to cite. The source attached to each question is the
  real chunk that was retrieved, not a page number the model made up.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional, Sequence

from . import config
from .gemma import ModelNotFoundError, OllamaUnavailableError, generate
from .prompts import quiz_json_prompt, quiz_text_prompt
from .rag import Source, build_context, gather_context_for

OPTION_LETTERS = ["A", "B", "C", "D"]


class QuizError(RuntimeError):
    """The quiz could not be produced."""


@dataclass
class Question:
    """One validated quiz question."""

    question: str
    options: list[str]  # rendered as "A. text", "B. text", ...
    correct_index: int
    explanation: str
    source: Optional[Source] = None

    @property
    def correct_letter(self) -> str:
        return OPTION_LETTERS[self.correct_index]

    def is_correct(self, chosen_index: int) -> bool:
        """Deterministic grading: compare positions, never ask a model."""
        return chosen_index == self.correct_index

    @property
    def source_label(self) -> str:
        return self.source.label if self.source else ""

    def with_source(self, source: Optional[Source]) -> "Question":
        return Question(
            question=self.question,
            options=self.options,
            correct_index=self.correct_index,
            explanation=self.explanation,
            source=source,
        )


@dataclass
class Quiz:
    """A generated quiz plus the context it was built from."""

    topic: str
    difficulty: str
    questions: list[Question] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    format_used: str = "json"

    def __len__(self) -> int:
        return len(self.questions)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _extract_json_array(text: str) -> Optional[list]:
    """Pull a JSON array out of a model response.

    Small models like to wrap JSON in prose or code fences, so we try the
    strict parse first and then the first balanced array in the text.
    """
    if not text:
        return None
    candidate = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1).strip()
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

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
                try:
                    parsed = json.loads(candidate[start : position + 1])
                    return parsed if isinstance(parsed, list) else None
                except json.JSONDecodeError:
                    return None
    return None


def _normalise_options(options: Sequence) -> Optional[list[str]]:
    """Clean and check that exactly four distinct options came back.

    Two identical option texts make a question unanswerable, so duplicates are
    rejected rather than shown to the student.
    """
    if not isinstance(options, (list, tuple)) or len(options) != 4:
        return None
    cleaned = []
    for option in options:
        text = re.sub(r"^\s*[\(\[]?[A-Da-d][\)\].]\s*", "", str(option)).strip()
        text = text.strip("\"' ")
        if not text:
            return None
        cleaned.append(text)
    if len({text.lower() for text in cleaned}) != len(cleaned):
        return None
    return [
        f"{OPTION_LETTERS[position]}. {text}" for position, text in enumerate(cleaned)
    ]


def _questions_from_json(payload: list, count: int) -> list[Question]:
    """Validate JSON entries into Question objects. Bad entries are skipped."""
    questions: list[Question] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        text = str(entry.get("question", "")).strip()
        options = _normalise_options(entry.get("options") or [])
        if not text or not options:
            continue

        correct = entry.get("correct_index", entry.get("correct_answer"))
        index = _resolve_correct_index(correct, options)
        if index is None:
            continue

        explanation = str(
            entry.get("explanation") or entry.get("why") or ""
        ).strip()
        if not explanation:
            explanation = "Review the source material for this question."

        questions.append(
            Question(
                question=text,
                options=options,
                correct_index=index,
                explanation=explanation,
            )
        )
        if len(questions) >= count:
            break
    return questions


def _resolve_correct_index(correct, options: Sequence[str]) -> Optional[int]:
    """Accept either a 0-based index or an "A"/"B"/... or letter answer."""
    if correct is None:
        return None
    if isinstance(correct, bool):
        return None
    if isinstance(correct, int):
        return correct if 0 <= correct < len(options) else None

    text = str(correct).strip()
    if text.isdigit():
        value = int(text)
        if 0 <= value < len(options):
            return value
        return None

    match = re.match(r"^\(?([A-Da-d])\)?[\.\):]?\s*(.*)$", text)
    if match:
        letter = match.group(1).upper()
        index = OPTION_LETTERS.index(letter)
        # "B" or "B. text" points at a position.
        if not match.group(2).strip():
            return index
        # "B. text" -> match the option text, in case the order drifted.
        wanted = match.group(2).strip().lower()
        for position, option in enumerate(options):
            if option.split(". ", 1)[-1].strip().lower() == wanted:
                return position
        return index
    return None


_BLOCK = re.compile(
    r"QUESTION:\s*(?P<question>.+?)\s*"
    r"A\.\s*(?P<a>.+?)\s*"
    r"B\.\s*(?P<b>.+?)\s*"
    r"C\.\s*(?P<c>.+?)\s*"
    r"D\.\s*(?P<d>.+?)\s*"
    r"ANSWER:\s*(?P<answer>[A-D])",
    re.IGNORECASE | re.DOTALL,
)
_WHY = re.compile(r"WHY:\s*(?P<why>.+?)(?=QUESTION:|$)", re.IGNORECASE | re.DOTALL)


def _questions_from_text(text: str, count: int) -> list[Question]:
    """Fallback parser for the line-based format."""
    questions: list[Question] = []
    for match in _BLOCK.finditer(text or ""):
        index = OPTION_LETTERS.index(match.group("answer").upper())
        tail = text[match.end() : match.end() + 400]
        why_match = _WHY.search(tail)
        explanation = why_match.group("why").strip() if why_match else ""
        explanation = " ".join(explanation.split())
        questions.append(
            Question(
                question=" ".join(match.group("question").split()),
                options=[
                    f"A. {' '.join(match.group('a').split())}",
                    f"B. {' '.join(match.group('b').split())}",
                    f"C. {' '.join(match.group('c').split())}",
                    f"D. {' '.join(match.group('d').split())}",
                ],
                correct_index=index,
                explanation=explanation
                or "Review the source material for this question.",
            )
        )
        if len(questions) >= count:
            break
    return questions


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def build_quiz(
    topic: str,
    count: int = 5,
    difficulty: str = "Medium",
    sources: Optional[Sequence[Source]] = None,
    model: Optional[str] = None,
) -> Quiz:
    """Create a quiz grounded in the student's own documents."""
    topic = (topic or "").strip()
    if not topic:
        raise QuizError("Choose a quiz topic first.")
    count = max(1, min(int(count), 10))
    if difficulty not in config.DIFFICULTIES:
        difficulty = "Medium"

    if sources is None:
        sources = gather_context_for(topic, n_results=4)
    sources = [source for source in sources if source.score >= config.RELEVANCE_THRESHOLD]

    if not sources:
        raise QuizError(
            "PocketFriend couldn't find material about "
            f"'{topic}' in your uploaded documents.\n\n"
            "Upload a PDF that covers this topic, or pick a topic that matches "
            "your notes."
        )

    context = build_context(sources[:4])

    try:
        raw = generate(quiz_json_prompt(topic, context, count, difficulty), model=model)
        questions = _questions_from_json(_extract_json_array(raw) or [], count)
        used = "json"
    except (OllamaUnavailableError, ModelNotFoundError) as exc:
        raise QuizError(str(exc)) from exc

    if len(questions) < count:
        # The JSON path failed or came back incomplete. Ask again in the simpler
        # line format, which small models follow more reliably.
        try:
            fallback = generate(
                quiz_text_prompt(topic, context, count, difficulty), model=model
            )
            parsed = _questions_from_text(fallback, count)
            if len(parsed) > len(questions):
                questions = parsed
                used = "text"
        except (OllamaUnavailableError, ModelNotFoundError) as exc:
            if not questions:
                raise QuizError(str(exc)) from exc

    if not questions:
        raise QuizError(
            "The local model could not produce a usable quiz about "
            f"'{topic}'.\n\nThis happens occasionally with small models. Try "
            "again, choose a narrower topic, or reduce the number of questions."
        )

    # Attach the real retrieved chunk to each question, spreading sources so the
    # quiz covers more than a single page.
    attached = [
        question.with_source(sources[index % len(sources)])
        for index, question in enumerate(questions)
    ]
    return Quiz(
        topic=topic,
        difficulty=difficulty,
        questions=attached,
        sources=list(sources),
        format_used=used,
    )


def score_quiz(questions: Sequence[Question], answers: Sequence[Optional[int]]) -> dict:
    """Grade the quiz in Python. No model involved.

    answers[i] is the option index the student picked, or None if skipped.
    """
    total = len(questions)
    correct = 0
    detail: list[bool] = []
    for index, question in enumerate(questions):
        chosen = answers[index] if index < len(answers) else None
        is_right = chosen is not None and question.is_correct(chosen)
        detail.append(is_right)
        if is_right:
            correct += 1
    return {
        "score": correct,
        "total": total,
        "percent": round((correct / total) * 100) if total else 0,
        "detail": detail,
    }


def result_message(result: dict) -> str:
    """A short, encouraging summary of a finished quiz."""
    percent = result["percent"]
    if percent == 100:
        headline = "Perfect score. Nothing left to fix here."
    elif percent >= 80:
        headline = "Strong result. Skim the ones you missed."
    elif percent >= 50:
        headline = "Halfway there. The explanations below are worth reading."
    elif percent > 0:
        headline = "Rough day. Review the source pages and try again."
    else:
        headline = "Tough start. Read the explanations, then retry the topic."
    return f"**Score: {result['score']} / {result['total']}** — {headline}"