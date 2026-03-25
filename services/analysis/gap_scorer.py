from __future__ import annotations


def score_gaps(gaps: list[dict]) -> list[dict]:
    scored = []
    for gap in gaps:
        item = dict(gap)
        support_count = len(item.get("supporting_evidence", []))
        counter_count = len(item.get("counter_evidence", []))
        confidence = max(0.1, min(1.0, 0.4 + support_count * 0.2 - counter_count * 0.15))
        novelty_value = max(0.1, min(1.0, 0.5 + support_count * 0.1))
        review_worthiness = max(0.1, min(1.0, confidence * 0.6 + novelty_value * 0.4))
        item["confidence"] = round(confidence, 3)
        item["novelty_value"] = round(novelty_value, 3)
        item["review_worthiness"] = round(review_worthiness, 3)
        scored.append(item)
    return scored
