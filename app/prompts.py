"""Prompt templates for Gemma.

The grounding rules live in one place so every feature tells the model the
same thing: answer only from the supplied context, and never invent a source.
"""

from textwrap import dedent
from typing import Sequence

BASE_SYSTEM_PROMPT = dedent(
    """\
    You are PocketFriend, a private study assistant that runs entirely on the
    user's own computer.

    Rules you must always follow:
    1. Answer only from the CONTEXT provided in the user message. Treat the
       context as the only source of truth about the user's documents.
    2. If the answer is not present in the context, reply exactly:
       "I couldn't find enough relevant information in your uploaded documents."
       Do not guess, and do not fill the gap with general knowledge.
    3. Never invent file names, page numbers, quotes or citations.
    4. Be concise and practical. Use short paragraphs or bullet points.
    5. Speak directly to the student. Plain language, no filler, no preamble.
    """
).strip()


def _clean(text: str) -> str:
    return dedent(text).strip()


def answer_question_prompt(question: str, context: str, history: str = "") -> str:
    """Grounded question answering prompt."""
    history_block = f"\nEarlier in this conversation:\n{history}\n" if history else ""
    return _clean(
        f"""
        Here is the relevant text from the student's uploaded documents.

        CONTEXT:
        ---
        {context}
        ---

        STUDENT QUESTION:
        {question}
        {history_block}
        Answer the question using only the CONTEXT above.
        Start with the direct answer in the first sentence.
        """
    )


def explain_topic_prompt(topic: str, context: str, level: str = "beginner") -> str:
    """Explain a topic the way a student is meeting it for the first time."""
    return _clean(
        f"""
        Here is the relevant text from the student's uploaded documents.

        CONTEXT:
        ---
        {context}
        ---

        TOPIC: {topic}
        EXPLANATION LEVEL: {level}

        Explain this topic to a student who is learning it for the first time.
        Use only the CONTEXT above for the facts. Use one everyday analogy, then
        give the concrete definition, then list 3 short key points.
        """
    )


def quiz_json_prompt(topic: str, context: str, count: int, difficulty: str) -> str:
    """Ask for multiple-choice questions as JSON.

    The app validates the JSON and grades answers itself, so the model only has
    to produce the question content.
    """
    return _clean(
        f"""
        Create a {difficulty.lower()} multiple-choice quiz about: {topic}

        Use ONLY the facts in the CONTEXT below.

        CONTEXT:
        ---
        {context}
        ---

        Return ONLY a JSON array with exactly {count} objects.
        Each object must have these keys:
        {{
          "question": "the question text",
          "options": ["A. first option text", "B. ...", "C. ...", "D. ..."],
          "correct_index": 0,
          "explanation": "one or two sentences explaining why the answer is correct"
        }}

        Rules:
        - "options" must have exactly 4 entries starting with "A.", "B.", "C.", "D."
        - "correct_index" must be the 0-based position of the correct option.
        - Never mention where the fact came from; the app adds real citations.
        - Output the JSON array only. No commentary before or after.
        """
    )


def quiz_text_prompt(topic: str, context: str, count: int, difficulty: str) -> str:
    """Line-based quiz fallback for when the model cannot produce valid JSON."""
    return _clean(
        f"""
        Create a {difficulty.lower()} multiple-choice quiz about: {topic}
        using ONLY the CONTEXT below.

        CONTEXT:
        ---
        {context}
        ---

        Use EXACTLY this format for each of the {count} questions, with no extra text:

        QUESTION: <question text>
        A. <option>
        B. <option>
        C. <option>
        D. <option>
        ANSWER: <A, B, C or D>
        WHY: <one sentence explaining the correct answer>
        """
    )


def study_day_prompt(
    exam_name: str,
    day_number: int,
    total_days: int,
    exam_date: str,
    hours: float,
    topics: str,
    context: str,
) -> str:
    """One day of a study plan, grounded in retrieved material."""
    return _clean(
        f"""
        You are helping a student prepare for the "{exam_name}" exam on {exam_date}.
        This is Day {day_number} of {total_days}. The student has about {hours} hours.

        Focus topics for today: {topics}

        Relevant text from the student's documents:
        ---
        {context}
        ---

        Write the plan for this day using ONLY the facts in the text above.
        Output exactly 3 bullet lines, each starting with "- ":
        - one bullet naming what to read or review, including the section or page topic
        - one bullet listing concrete points or definitions to cover
        - one bullet describing a short practice activity
        Do not write a heading. Do not explain your reasoning.
        """
    )


def study_plan_days_prompt(
    exam_name: str,
    exam_date: str,
    hours: float,
    days: Sequence[dict],
) -> str:
    """Every day of a study plan in one request, as a JSON array.

    The planner used to ask Gemma one day at a time. On a small local model that
    cost 25-45 seconds per day, so a two-week plan took minutes. One request for
    the whole plan keeps the generation to a single Ollama call.

    `days` is a sequence of dicts in order, each with:
      "day":     the day number
      "topics":  the focus for that day
      "context": the retrieved text for that day, labelled with where it came from

    Each day carries its own text on purpose. With one shared block, a 1B model
    drifts and answers Day 2 with Day 3's topic, which is worse than no answer
    at all because it looks right. Days the model gets wrong or omits simply keep
    the checklist the planner computed in Python.
    """
    count = len(days)
    blocks = "\n\n".join(
        f'{{"day": {day["day"]}, "topics": "{day["topics"]}", "notes": "{day["notes"]}"}}'
        for day in days
    )
    return _clean(
        f"""
        You are helping a student prepare for the "{exam_name}" exam on {exam_date}.
        The student has about {hours} hours a day, over {count} day(s).

        Here is the plan, one object per day. Each object carries the text
        retrieved for that day and nothing else:

        [
        {blocks}
        ]

        Write the revision detail for EVERY day above, using ONLY the "notes" of
        that same day.

        Return ONLY a JSON array with exactly {count} objects, in the same order as
        the plan, each with these keys:
        {{"day": 1, "bullets": ["...", "...", "..."]}}

        Rules:
        - "day" must repeat the day number of the object you are filling in.
        - Every bullet must be about that day's own "topics", never another day's.
        - "bullets" must have exactly 3 short strings.
        - bullet 1: what to read or review, naming the section or topic.
        - bullet 2: the concrete points or definitions to cover.
        - bullet 3: a short practice activity.
        - Write each bullet as a short instruction to the student, beginning with a
          verb such as Read, Cover or Try. Do not copy a sentence out of the text,
          do not repeat the same sentence twice in one bullet, and do not add a
          label followed by a colon.
        - Do not add keys, commentary, or markdown fences.
        """
    )


def daily_explanation_prompt(item_title: str, context: str) -> str:
    """A one-line "what to watch out for" note about a study item.

    Asked about document content only, never about dates or ordering, for the
    same reason as `focus_tip_prompt`: a 1B model given scheduling detail tends
    to contradict the UI it is meant to support.
    """
    return _clean(
        f"""
        A student is working through this item: "{item_title}"

        This text comes from their own documents:
        ---
        {context}
        ---

        In one short sentence, tell them the single thing most worth watching out
        for while they work through that text. Name one specific term, definition
        or common mistake that appears in it.

        Do not mention dates, deadlines or priorities. Do not use bullet points.
        """
    )


def focus_tip_prompt(item_title: str, context: str) -> str:
    """A short, grounded suggestion about what to concentrate on.

    This prompt is only ever asked about the content of a document, never about
    dates, deadlines or the ordering of tasks. Keeping it away from anything the
    app already knows is what stops a small model from contradicting the UI.
    """
    return _clean(
        f"""
        A student is about to work through this item: "{item_title}"

        This text comes from their own documents:
        ---
        {context}
        ---

        In one sentence, tell them the single most useful thing to understand
        from that text while they work on it. Mention one specific term, name or
        definition from the text.

        Do not mention dates, deadlines or priorities. Do not use bullet points.
        """
    )