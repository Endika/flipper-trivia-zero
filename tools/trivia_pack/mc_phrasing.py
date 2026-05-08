"""Drop questions whose phrasing assumes a multiple-choice option list.

OpenTDB ships every item with four answer choices. When we collapse to a
single-answer trivia format, questions of the form "Which of the following
European languages..." or "Of these films, which..." lose the list of
candidates they were referencing and become unanswerable on their own.
The same goes for answers that point back at the (now hidden) list, like
"All of the above" or "None of these songs".

This filter operates on the canonical English source. Spanish text is
derived via translation downstream, so filtering EN here is sufficient.
"""

from __future__ import annotations

import re

_PATTERNS: tuple[str, ...] = (
    # "Which of the following X is Y?", "Which of these X..."
    r"\bwhich of (the following|these|those)\b",
    # "Which one of these X...", "Which one of the following..."
    r"\bone of (the following|these|those)\b",
    # "Of the following, which X...", "Of the following X is Y?"
    r"\bof the following\b",
    # "Which is the largest of these 4 islands?" / "...of those..."
    r"\bof these\b",
    r"\bof those\b",
    # Answers like "All of the above" / "None of the above" reference the
    # original choice list directly.
    r"\bof the above\b",
)

_REGEX = re.compile("|".join(_PATTERNS), flags=re.IGNORECASE)


def is_multiple_choice_phrasing(question: str, answer: str) -> bool:
    """Return True iff the question or answer presupposes a list of options."""
    return bool(_REGEX.search(question) or _REGEX.search(answer))
