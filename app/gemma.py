"""Local AI access through Ollama (Google Gemma).

This is the only module that talks to a language model. It never raises raw
library errors at the UI: every failure is converted into a clear message that
the Streamlit app can show to the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, Optional

import ollama

from . import config
from .prompts import BASE_SYSTEM_PROMPT


class OllamaUnavailableError(RuntimeError):
    """Ollama is not running or cannot be reached."""

    def __init__(self, message: str = "PocketFriend cannot reach Ollama."):
        super().__init__(message)


class ModelNotFoundError(RuntimeError):
    """Ollama is running, but the selected model has not been pulled."""


def _get(obj: object, key: str, default: object = None) -> object:
    """Read a field from a dict or an attribute-style object.

    The ollama client returns pydantic-style responses, but plain dicts show up
    in tests and older client versions, so we support both.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@dataclass
class AIStatus:
    """Everything the UI needs to describe the local AI connection."""

    ollama_running: bool = False
    model: str = config.OLLAMA_MODEL
    model_available: bool = False
    local_models: list[str] = field(default_factory=list)
    detail: str = ""

    @property
    def ready(self) -> bool:
        return self.ollama_running and self.model_available

    @property
    def headline(self) -> str:
        if not self.ollama_running:
            return "Ollama is not running"
        if not self.model_available:
            return f"Model '{self.model}' is not installed"
        return "Local AI ready"

    def user_message(self) -> str:
        """A friendly, actionable message for the Streamlit UI."""
        if not self.ollama_running:
            return (
                "PocketFriend cannot reach Ollama. Please start Ollama and try "
                "again.\n\n"
                "**Start it:**\n"
                "- Windows / macOS / Linux: open the Ollama app or run "
                "`ollama serve` in a terminal."
            )
        if not self.model_available:
            return (
                f"Ollama is running, but the model `{self.model}` is not available "
                "locally.\n\n"
                f"**Fix it:** run `ollama pull {self.model}` in a terminal."
            )
        return "Gemma is running locally through Ollama."


def _client() -> ollama.Client:
    return ollama.Client(host=config.OLLAMA_HOST, timeout=config.OLLAMA_TIMEOUT)


def check_ollama(model: Optional[str] = None) -> AIStatus:
    """Check Ollama availability and whether the selected model is present.

    Never raises: returns an AIStatus describing what is wrong so the UI can
    render a helpful message instead of a traceback.
    """
    target_model = model or config.OLLAMA_MODEL
    status = AIStatus(model=target_model)

    try:
        response = _client().list()
    except Exception as exc:  # connection refused, bad host, timeout, not installed
        status.detail = f"{type(exc).__name__}: {exc}"
        return status

    status.ollama_running = True

    models = _get(response, "models", []) or []
    names = []
    for entry in models:
        name = _get(entry, "model") or _get(entry, "name") or ""
        if name:
            names.append(str(name))
    status.local_models = sorted(names)

    # Ollama reports "gemma3:1b" but a pull of "gemma3" shows up as "gemma3:latest".
    def matches(available: str) -> bool:
        if available == target_model:
            return True
        base = target_model.split(":")[0]
        return available.split(":")[0] == base

    status.model_available = any(matches(name) for name in names)
    if status.model_available and not status.detail:
        status.detail = f"Found {len(names)} local model(s)."
    return status


def require_ready(model: Optional[str] = None) -> None:
    """Raise a friendly error unless the local AI is usable."""
    status = check_ollama(model)
    if not status.ollama_running:
        raise OllamaUnavailableError(status.user_message())
    if not status.model_available:
        raise ModelNotFoundError(status.user_message())


def list_local_models() -> list[str]:
    """Names of every model already pulled into Ollama."""
    return check_ollama().local_models


def generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """Send a prompt to Gemma and return clean text.

    `max_tokens` overrides the default response budget for the rare request that
    needs a longer answer than one chat reply, such as a whole study plan.

    Raises OllamaUnavailableError or ModelNotFoundError with user-facing text
    instead of leaking library exceptions.
    """
    target_model = model or config.OLLAMA_MODEL
    require_ready(target_model)

    options = {
        "temperature": config.TEMPERATURE if temperature is None else temperature,
        "num_predict": int(max_tokens) if max_tokens else config.MAX_TOKENS,
    }

    messages = [
        {
            "role": "system",
            "content": (system_prompt or BASE_SYSTEM_PROMPT).strip(),
        },
        {"role": "user", "content": prompt.strip()},
    ]

    try:
        response = _client().chat(
            model=target_model, messages=messages, options=options, stream=False
        )
    except OllamaUnavailableError:
        raise
    except Exception as exc:
        message = str(exc)
        if "not found" in message.lower() and "model" in message.lower():
            raise ModelNotFoundError(status_message_for(target_model)) from exc
        raise OllamaUnavailableError(
            "PocketFriend could not get a response from the local model.\n\n"
            f"Details: {type(exc).__name__}: {message}"
        ) from exc

    content = _get(_get(response, "message", {}), "content", "") or ""
    return clean_output(str(content))


def stream(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
) -> Iterator[str]:
    """Yield response chunks as they arrive, for the chat-style page."""
    target_model = model or config.OLLAMA_MODEL
    require_ready(target_model)

    messages = [
        {"role": "system", "content": (system_prompt or BASE_SYSTEM_PROMPT).strip()},
        {"role": "user", "content": prompt.strip()},
    ]
    try:
        for part in _client().chat(
            model=target_model,
            messages=messages,
            options={"temperature": config.TEMPERATURE, "num_predict": config.MAX_TOKENS},
            stream=True,
        ):
            chunk = _get(_get(part, "message", {}), "content", "") or ""
            if chunk:
                yield chunk
    except Exception as exc:
        raise OllamaUnavailableError(
            "PocketFriend lost the connection to the local model while generating.\n\n"
            f"Details: {type(exc).__name__}: {exc}"
        ) from exc


def status_message_for(model: Optional[str] = None) -> str:
    target_model = model or config.OLLAMA_MODEL
    return (
        f"Ollama is running, but the model `{target_model}` is not available locally."
        f"\n\n**Fix it:** run `ollama pull {target_model}` in a terminal."
    )


def ping(model: Optional[str] = None, prompt: str = "Reply with the single word: ready") -> tuple[bool, str]:
    """Run a tiny completion. Returns (success, message). Never raises."""
    try:
        reply = generate(prompt, system_prompt="You are a connectivity test.", model=model)
        return True, reply.strip()
    except (OllamaUnavailableError, ModelNotFoundError) as exc:
        return False, str(exc)
    except Exception as exc:  # last-resort guard
        return False, f"{type(exc).__name__}: {exc}"


_LEAK_PATTERNS = (
    re.compile(r"^(?:CONTEXT|SOURCE|SOURCES)\s*:\s*$", re.IGNORECASE | re.MULTILINE),
)


def clean_output(text: str) -> str:
    """Tidy raw model output for display.

    Small models like to echo the prompt scaffolding back. We strip empty
    scaffolding lines and collapse runaway blank lines, but we never alter the
    words of the answer itself.
    """
    if not text:
        return ""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    for pattern in _LEAK_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    lines = [line.rstrip() for line in cleaned.split("\n")]
    # Collapse runs of 3+ blank lines into a single blank line.
    out: list[str] = []
    blanks = 0
    for line in lines:
        if line:
            blanks = 0
            out.append(line)
        else:
            blanks += 1
            if blanks <= 1:
                out.append("")
    return "\n".join(out).strip()