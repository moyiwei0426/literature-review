from __future__ import annotations

import re


def normalize_title(title: str) -> str:
    text = title.lower().strip()
    text = re.sub(r"\bv\d+\b", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
