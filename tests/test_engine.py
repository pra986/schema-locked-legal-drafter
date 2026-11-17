import pytest
from legal_drafter.engine import SchemaLockedDrafterEngine


def test_incomplete_field_pdf_export_blocked() -> None:
    engine = SchemaLockedDrafterEngine(":memory:")
    draft = engine.create_draft(
        user_id="alice",
        template_id="mutual_nda",
        raw_fields={"party_a": "Acme Corp"},
    )
    assert len(draft.missing_fields) > 0
    with pytest.raises(ValueError, match="Export blocked"):
        engine.export_pdf("alice", draft.draft_id)


def test_html_xss_escaping_in_party_names() -> None:
    engine = SchemaLockedDrafterEngine(":memory:")
    xss = '<script>alert("xss")</script>'
    draft = engine.create_draft(
        user_id="alice",
        template_id="mutual_nda",
        raw_fields={
            "party_a": xss,
            "party_b": "Globex LLC",
            "effective_date": "2026-11-18",
            "governing_law": "Delaware",
        },
    )
    assert "<script>" not in draft.preview_html
    assert "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;" in draft.preview_html


def test_cross_user_document_isolation() -> None:
    engine = SchemaLockedDrafterEngine(":memory:")
    draft = engine.create_draft(
        user_id="alice",
        template_id="one_way_nda",
        raw_fields={
            "disclosing_party": "Acme Corp",
            "receiving_party": "Beta Inc",
            "effective_date": "2026-11-18",
        },
    )
    with pytest.raises(PermissionError):
        engine.get_draft("bob", draft.draft_id)
    with pytest.raises(PermissionError):
        engine.export_pdf("bob", draft.draft_id)


def test_preview_to_pdf_byte_parity() -> None:
    engine = SchemaLockedDrafterEngine(":memory:")
    draft = engine.create_draft(
        user_id="alice",
        template_id="mutual_nda",
        raw_fields={
            "party_a": "Acme Corp",
            "party_b": "Globex LLC",
            "effective_date": "2026-11-18",
            "governing_law": "Delaware",
        },
    )
    receipt = engine.export_pdf("alice", draft.draft_id)
    assert receipt.parity_verified is True
    assert receipt.pdf_sha256 == draft.preview_sha256
    assert draft.preview_html.encode("utf-8") in receipt.pdf_bytes
