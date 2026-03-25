from core.models import PaperChunk
from services.extraction.claim_linker import build_claim_evidence_links
from services.extraction.extractor import PaperExtractor


def test_extraction_smoke() -> None:
    chunks = [
        PaperChunk(chunk_id="c1", paper_id="p1", section="abstract", text="This paper proposes a pipeline.", order_index=0),
        PaperChunk(chunk_id="c2", paper_id="p1", section="method", text="The method links evidence to claims.", order_index=1),
    ]
    profile, report = PaperExtractor().extract("p1", chunks)
    links = build_claim_evidence_links(profile)
    assert profile.paper_id == "p1"
    assert len(profile.main_claims) >= 1
    assert len(links) >= 1
    assert report["chunk_count"] == 2
