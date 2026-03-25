from __future__ import annotations

from difflib import SequenceMatcher

from core.models import PaperCandidate
from .title_normalizer import normalize_title


def exact_match(left: PaperCandidate, right: PaperCandidate) -> bool:
    if left.doi and right.doi and left.doi == right.doi:
        return True
    if left.arxiv_id and right.arxiv_id and left.arxiv_id == right.arxiv_id:
        return True
    return normalize_title(left.title) == normalize_title(right.title)


def fuzzy_match_score(left: PaperCandidate, right: PaperCandidate) -> float:
    title_score = SequenceMatcher(None, normalize_title(left.title), normalize_title(right.title)).ratio()
    same_year = left.year is not None and right.year is not None and left.year == right.year
    same_first_author = bool(left.authors and right.authors and left.authors[0] == right.authors[0])
    bonus = 0.1 if same_year else 0.0
    bonus += 0.1 if same_first_author else 0.0
    return min(1.0, title_score + bonus)
