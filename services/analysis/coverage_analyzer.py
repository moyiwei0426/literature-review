from __future__ import annotations

from collections import Counter

from core.models import PaperProfile


def _parse_year(paper_id: str) -> str:
    """Extract year from paper_id (filename format: {序号}_{年份}_{作者}_{期刊})."""
    parts = paper_id.split("_")
    for part in parts:
        if part.isdigit() and 1990 <= int(part) <= 2030:
            return part
    return "unknown"


def _looks_chinese_context(profile: PaperProfile) -> bool:
    haystacks = [
        profile.domain or "",
        profile.research_problem or "",
        profile.notes or "",
        *profile.datasets,
        *profile.tasks,
    ]
    text = " ".join(haystacks).lower()
    markers = [
        "china",
        "chinese",
        "pr china",
        "hong kong",
        "beijing",
        "shanghai",
        "hefei",
        "guangzhou",
        "shenzhen",
        "wuhan",
        "nanjing",
        "hangzhou",
        "suzhou",
        "chengdu",
    ]
    return any(marker in text for marker in markers)


def build_coverage_report(profiles: list[PaperProfile]) -> dict:
    method_counter = Counter()
    task_counter = Counter()
    language_counter = Counter()
    dataset_counter = Counter()
    year_counter = Counter()
    chinese_count = 0

    for profile in profiles:
        method_counter.update(profile.method_family)
        task_counter.update(profile.tasks)
        dataset_counter.update(profile.datasets)

        year = str(profile.year) if profile.year else _parse_year(profile.paper_id)
        year_counter.update([year])

        raw_lang = profile.language_scope or ""
        lang_lower = raw_lang.lower().strip()
        if lang_lower in ("chinese", "cn", "zh", "中文"):
            normalized = "chinese"
        elif lang_lower in ("english", "en", "eng", ""):
            normalized = "english"
        elif "arabic" in lang_lower:
            normalized = "arabic"
        else:
            normalized = raw_lang if raw_lang else "unknown"
        if normalized and normalized != "unknown":
            language_counter.update([normalized])

        if normalized == "chinese" or _looks_chinese_context(profile):
            chinese_count += 1

    return {
        "paper_count": len(profiles),
        "method_family_distribution": dict(method_counter),
        "task_distribution": dict(task_counter),
        "language_distribution": dict(language_counter),
        "dataset_distribution": dict(dataset_counter),
        "year_distribution": dict(year_counter),
        "chinese_coverage_count": chinese_count,
        "themes": list(method_counter.keys()),
    }
