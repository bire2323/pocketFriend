"""Presentation layer for PocketFriend.

`theme` holds the design system, `components` holds the reusable pieces and
`runtime` holds the shared data access, error handling and navigation. None of
them contain product logic: documents, retrieval, planning and quiz scoring all
still live in the app modules they came from.
"""

from . import components, runtime, theme  # noqa: F401

__all__ = ["components", "runtime", "theme"]