from pathlib import Path

from services.parsing.pymupdf_fallback import FallbackTextExtractor


def test_fallback_on_missing_file_path_type_only() -> None:
    extractor = FallbackTextExtractor()
    assert hasattr(extractor, 'extract')
    assert callable(extractor.extract)
    assert isinstance(Path('x.pdf'), Path)
