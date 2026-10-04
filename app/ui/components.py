"""Reusable presentation pieces.

Rules for everything in this module:

* it returns HTML strings (or writes one st.markdown) and never touches data;
* anything user supplied goes through :func:`esc`;
* the CSS lives in :mod:`app.ui.theme`, so a component is markup plus a class name.

Streamlit widgets stay Streamlit widgets. Wherever a widget needs a frame - a
row, a workspace zone, the composer - the frame comes from a keyed container, so
native behaviour and accessibility are never traded away for looks.
"""

from __future__ import annotations

import contextlib
from typing import Iterable, Optional, Sequence

import streamlit as st

from .theme import BRAND, TAGLINE, _ICON_PATHS

TONES = ("accent", "sage", "ok", "warn", "danger", "quiet")


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------


def esc(value) -> str:
    """Escape anything that came from the user, a file or the model."""
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _tone(value: Optional[str]) -> str:
    tone = (value or "").strip().lower()
    return tone if tone in TONES else "quiet"


def render(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


@contextlib.contextmanager
def icon_scope(name: str, unique: str = "x"):
    """Draw a line icon inside the buttons created inside this block.

    The icon is the same SVG the rest of the interface uses, painted with a CSS
    mask on the button's own ::before. Wrapping in a keyed container keeps the
    button a real button: keyboard focus, screen readers and Streamlit's own
    click handling are untouched.
    """
    with st.container(key=f"pf-ic-{name}-{unique}"):
        yield


def button(label: str, icon: Optional[str] = None, key: Optional[str] = None, **kwargs):
    """`st.button` with an optional icon from the app's own icon set."""
    if not icon:
        return st.button(label, key=key, **kwargs)
    with icon_scope(icon, key or label):
        clicked = st.button(label, key=key, **kwargs)
    return clicked


def download_button(label: str, data, icon: Optional[str] = None, **kwargs):
    """`st.download_button` with an optional icon from the app's own icon set.

    `data` sits in the same position as `st.download_button`'s own second
    argument so callers can pass it positionally, as they do with Streamlit's.
    `icon` is keyword-only here because Streamlit also has an `icon` argument of
    its own, which would otherwise be filled with our icon name.
    """
    if not icon:
        return st.download_button(label, data, **kwargs)
    with icon_scope(icon, kwargs.get("key") or label):
        clicked = st.download_button(label, data, **kwargs)
    return clicked


def rule(tight: bool = False) -> None:
    render(f'<div class="pf-rule{" pf-rule--tight" if tight else ""}"></div>')


def spacer(size: str = "md") -> None:
    render(f'<span class="pf-spacer pf-spacer--{size}"></span>')


def icon(name: str, size: int = 15, extra: str = "") -> str:
    """One line icon, same drawing as the CSS masks in the navigation."""
    path = _ICON_PATHS.get(name)
    if not path:
        return ""
    classes = f"pf-i {extra}".strip()
    return (
        f'<svg class="{classes}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{path}</svg>'
    )


def tag(text: str, tone: str = "neutral", mark: str = "") -> str:
    icon_html = icon(mark, 12) if mark else ""
    body = f'<span class="pf-cite__file">{esc(text)}</span>' if mark == "file" else esc(text)
    return f'<span class="pf-tag pf-tag--{_tone(tone)}">{icon_html}{body}</span>'


def tags(items: Iterable) -> str:
    return f'<div class="pf-tags">{"".join(tag(*item) for item in items)}</div>'


def panel(title: str, body_html: str = "", mark: str = "") -> str:
    head = (
        f'<div class="pf-panel__title">{icon(mark, 13) if mark else ""}{esc(title)}</div>'
        if title
        else ""
    )
    return f'<div class="pf-panel">{head}{body_html}</div>'


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def brand(name: str = BRAND, tagline: str = TAGLINE) -> str:
    return (
        '<div class="pf-brand">'
        f'<span class="pf-brand__mark">{icon("book", 16)}</span>'
        '<span class="pf-brand__text">'
        f'<div class="pf-brand__name">{esc(name)}</div>'
        f'<div class="pf-brand__tag">{esc(tagline)}</div>'
        "</span></div>"
    )


def navlabel(text: str) -> str:
    return f'<div class="pf-navlabel">{esc(text)}</div>'


def facts(pairs: Sequence[tuple]) -> str:
    rows = "".join(
        f'<div class="pf-fact"><span class="pf-fact__label">{esc(label)}</span>'
        f'<span class="pf-fact__value">{esc(value)}</span></div>'
        for label, value in pairs
    )
    return f'<div class="pf-facts">{rows}</div>'


def status(tone: str, label: str, detail: str = "") -> str:
    detail_html = f'<div class="pf-status__detail">{esc(detail)}</div>' if detail else ""
    return (
        f'<div class="pf-status pf-status--{_tone(tone)}">'
        f'<span class="pf-status__dot"></span><div>'
        f'<div class="pf-status__label">{esc(label)}</div>{detail_html}</div></div>'
    )


def note(body_html: str, title: Optional[str] = None, tone: str = "neutral") -> str:
    head = f'<span class="pf-note__title">{esc(title)}</span>' if title else ""
    return f'<div class="pf-note pf-note--{_tone(tone)}"><div class="pf-note__body">{head}{body_html}</div></div>'


def text_note(text: str, title: Optional[str] = None, tone: str = "neutral") -> str:
    return note(esc(text), title=title, tone=tone)


def side_note(html: str) -> str:
    return f'<div class="pf-side-note">{html}</div>'


# ---------------------------------------------------------------------------
# Page furniture
# ---------------------------------------------------------------------------


def topbar(
    title: str,
    subtitle: str = "",
    eyebrow: str = "",
    meta: Optional[Sequence[tuple]] = None,
) -> str:
    parts = ['<div class="pf-top">', '<div class="pf-top__main">']
    if eyebrow:
        parts.append(f'<div class="pf-top__eyebrow">{esc(eyebrow)}</div>')
    parts.append(f'<h1 class="pf-top__title">{esc(title)}</h1>')
    if subtitle:
        parts.append(f'<p class="pf-top__sub">{esc(subtitle)}</p>')
    if meta:
        parts.append(f'<div class="pf-top__meta">{"".join(tag(*item) for item in meta)}</div>')
    parts.append("</div></div>")
    return "".join(parts)


def section(
    title: str,
    sub: Optional[str] = None,
    aside: Optional[str] = None,
    mark: str = "",
) -> str:
    glyph = icon(mark, 14) if mark else ""
    sub_html = f'<div class="pf-section__sub">{esc(sub)}</div>' if sub else ""
    aside_html = f'<span class="pf-section__aside">{esc(aside)}</span>' if aside else ""
    return (
        '<div class="pf-section"><div>'
        f'<div class="pf-section__title">{glyph}{esc(title)}</div>{sub_html}'
        f'</div>{aside_html}</div>'
    )


def zonehead(text: str, mark: str = "") -> str:
    return f'<div class="pf-zonehead">{icon(mark, 13) if mark else ""}{esc(text)}</div>'


def kv(pairs: Sequence[tuple]) -> str:
    rows = "".join(
        f'<div class="pf-kv__row"><span class="pf-kv__key">{esc(key)}</span>'
        f'<span class="pf-kv__val">{esc(value)}</span></div>'
        for key, value in pairs
    )
    return f'<div class="pf-kv">{rows}</div>'


def nums(items: Sequence[dict]) -> str:
    cells = "".join(
        f'<div><div class="pf-num__value">{esc(item["value"])}</div>'
        f'<div class="pf-num__label">{esc(item["label"])}</div></div>'
        for item in items
    )
    return f'<div class="pf-nums">{cells}</div>'


def list_rows(items: Sequence[tuple], mark: str = "file") -> str:
    rows = "".join(
        f'<div class="pf-list__row"><span class="pf-list__glyph">{icon(mark, 15)}</span>'
        f'<span class="pf-list__name">{esc(name)}</span>'
        f'<span class="pf-list__meta">{esc(detail)}</span></div>'
        for name, detail in items
    )
    return f'<div class="pf-list">{rows}</div>'


def steps(items: Sequence[tuple]) -> str:
    rows = "".join(
        f'<div><div class="pf-item__title">{esc(title)}</div>'
        f'<div class="pf-item__note">{esc(body)}</div></div>'
        for title, body in items
    )
    return f'<div class="pf-nums" style="gap:var(--s7)">{rows}</div>'


# ---------------------------------------------------------------------------
# Items: one row per document, task or plan
# ---------------------------------------------------------------------------


def item_markup(
    title: str,
    meta: Optional[Sequence[tuple]] = None,
    note_text: str = "",
    mark: str = "file",
    glyph_tone: str = "",
    done: bool = False,
) -> str:
    """Body of a row. Escaped, flat, and aligned to the icon column."""
    title_class = "pf-item__title" + (" pf-item__title--done" if done else "")
    glyph_tone = f" pf-item__glyph--{_tone(glyph_tone)}" if glyph_tone else ""
    meta_html = f'<div class="pf-item__meta">{"".join(tag(*m) for m in meta)}</div>' if meta else ""
    note_html = f'<div class="pf-item__note">{esc(note_text)}</div>' if note_text else ""
    return (
        '<div class="pf-item__body">'
        f'<span class="pf-item__glyph{glyph_tone}">{icon(mark, 14)}</span>'
        '<span class="pf-item__text">'
        f'<div class="{title_class}">{esc(title)}</div>{meta_html}{note_html}'
        "</span></div>"
    )


def source_item(name: str, meta: str = "", selected: bool = False) -> str:
    """A selectable row in the sources list (left zone of Ask)."""
    classes = "pf-srcitem" + (" pf-srcitem--on" if selected else "")
    return (
        f'<div class="{classes}">'
        f'<span class="pf-srcitem__glyph">{icon("file", 14)}</span>'
        "<span>"
        f'<div class="pf-srcitem__name">{esc(name)}</div>'
        f'<div class="pf-srcitem__meta">{esc(meta)}</div>'
        "</span></div>"
    )


# ---------------------------------------------------------------------------
# Sources: citations and the evidence column
# ---------------------------------------------------------------------------


def citation(source) -> str:
    filename = getattr(source, "filename", "document")
    page = getattr(source, "page", 0)
    score = float(getattr(source, "score", 0.0) or 0.0)
    match = (
        f'<span class="pf-cite__match">{score:.2f}</span>'
        if score
        else ""
    )
    return (
        '<span class="pf-cite">'
        f'<span class="pf-cite__file">{esc(filename)}</span> '
        f'<span class="pf-cite__sep">·</span> '
        f'<span class="pf-cite__page">p. {esc(page)}</span>'
        f'{match}</span>'
    )


def citations(sources: Sequence) -> str:
    return "".join(citation(source) for source in sources)


def evidence(sources: Sequence, show_match: bool = True) -> str:
    """Right-hand zone: filename, page, excerpt. Makes grounding obvious."""
    blocks = []
    for source in sources:
        filename = getattr(source, "filename", "document")
        page = getattr(source, "page", 0)
        excerpt = source.excerpt() if hasattr(source, "excerpt") else str(source)
        score = float(getattr(source, "score", 0.0) or 0.0)
        match = ""
        if show_match and score:
            percent = max(3, min(100, round(score * 100)))
            match = (
                '<div class="pf-ev__match"><span>match</span>'
                f'<span class="pf-meter"><span class="pf-meter__fill" style="width:{percent}%">'
                f'</span></span><span>{score:.2f}</span></div>'
            )
        blocks.append(
            '<div class="pf-ev">'
            '<div class="pf-ev__head">'
            f'<span class="pf-ev__file">{esc(filename)}</span>'
            f'<span class="pf-ev__page">p. {esc(page)}</span></div>'
            f'<div class="pf-ev__excerpt">{esc(excerpt)}</div>{match}</div>'
        )
    return "".join(blocks)


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


def question_bubble(text: str) -> str:
    return f'<div class="pf-ask"><div class="pf-ask__bubble">{esc(text)}</div></div>'


def answer_head(label: str = "ANSWER") -> str:
    return f'<div class="pf-answer__head">{icon("spark", 12)}{esc(label)}</div>'


def answer_foot(sources: Sequence) -> str:
    """The provenance line under an answer: compact [file · p. n] citations."""
    if not sources:
        return ""
    return (
        '<div class="pf-answer__foot">'
        f'<span class="pf-answer__label">{icon("quote", 12)}From your documents</span>'
        f"{citations(sources)}</div>"
    )


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------


def progress(done: int, total: int) -> str:
    percent = round((done / total) * 100) if total else 0
    return (
        '<div class="pf-progress">'
        f'<span class="pf-progress__count">{done} / {total}</span>'
        f'<span class="pf-progress__bar"><span class="pf-progress__fill" style="width:{percent}%">'
        "</span></span></div>"
    )


def question(text: str, hint: str = "") -> str:
    hint_html = f'<div class="pf-question__hint">{esc(hint)}</div>' if hint else ""
    return f'<div class="pf-question">{esc(text)}</div>{hint_html}'


def letter(index: int) -> str:
    return "ABCDEFGH"[index]


def answer_rows(question_obj, chosen: Optional[int]) -> str:
    """Answered choices: the right one and the student's pick are unmistakable."""
    rows = []
    for index, option in enumerate(question_obj.options):
        if index == question_obj.correct_index:
            tone, flag = "ok", "correct"
        elif index == chosen:
            tone, flag = "bad", "your answer"
        else:
            tone, flag = "", ""
        rows.append(
            f'<div class="pf-answerrow pf-answerrow--{tone}">'
            f'<span class="pf-answerrow__key">{letter(index)}</span>'
            f'<span class="pf-answerrow__text">{esc(option)}</span>'
            f'<span class="pf-answerrow__flag">{esc(flag)}</span></div>'
        )
    return f'<div class="pf-answerlist">{"".join(rows)}</div>'


def verdict(ok: bool, title: str, body: str = "") -> str:
    glyph = icon("check", 12) if ok else icon("close", 12)
    body_html = f"<div>{esc(body)}</div>" if body else ""
    tone = "ok" if ok else "bad"
    return (
        f'<div class="pf-verdict pf-verdict--{tone}">'
        f'<span class="pf-verdict__glyph">{glyph}</span>'
        f'<span><span class="pf-verdict__title">{esc(title)}</span>{body_html}</span></div>'
    )


def score(value: str, label: str, meta: str = "") -> str:
    meta_html = f'<div class="pf-score__meta">{esc(meta)}</div>' if meta else ""
    return (
        '<div class="pf-score">'
        f'<div class="pf-score__value">{esc(value)}</div>'
        f'<div><div class="pf-score__label">{esc(label)}</div>{meta_html}</div></div>'
    )


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def day(number: int, date_label: str, topics: Sequence[str], bullets: Sequence[str], reading: str = "") -> str:
    bullets_html = "".join(f"<li>{esc(item)}</li>" for item in bullets)
    reading_html = (
        f'<div class="pf-item__meta"><span class="pf-tag pf-tag--accent">Read {esc(reading)}</span></div>'
        if reading
        else ""
    )
    return (
        '<div class="pf-day">'
        f'<div class="pf-day__num">{esc(number)}</div><div>'
        f'<div class="pf-day__title">{esc(", ".join(topics))}</div>'
        f'<div class="pf-day__meta">{esc(date_label)}</div>'
        f'<ul class="pf-day__list">{bullets_html}</ul>{reading_html}</div></div>'
    )


# ---------------------------------------------------------------------------
# Empty states and loading
# ---------------------------------------------------------------------------


def empty(
    title: str,
    body: str = "",
    hint: str = "",
    mark: str = "layers",
    center: bool = False,
) -> str:
    glyph = icon(mark, 15)
    hint_html = f'<div class="pf-empty__hint">{esc(hint)}</div>' if hint else ""
    classes = "pf-empty" + (" pf-empty--center" if center else "")
    return (
        f'<div class="{classes}">'
        f'<div class="pf-empty__row"><span class="pf-empty__glyph">{glyph}</span>'
        "<span>"
        f'<div class="pf-empty__title">{esc(title)}</div>'
        f'<div class="pf-empty__body">{esc(body)}</div>'
        "</span></div>"
        f"{hint_html}</div>"
    )


def loading(text: str) -> str:
    return (
        '<div class="pf-loading">'
        '<span class="pf-loading__dots"><span></span><span></span><span></span></span>'
        f'<span class="pf-loading__text">{esc(text)}</span></div>'
    )
