import json
from .engine import SchemaLockedDrafterEngine


def run_demo() -> None:
    engine = SchemaLockedDrafterEngine(":memory:")
    templates = engine.list_templates()
    print(f"Loaded {len(templates)} locked agreement templates.")

    draft = engine.create_draft(
        user_id="demo-user",
        template_id="mutual_nda",
        raw_fields={
            "party_a": "Acme Corp",
            "party_b": "Globex LLC",
            "effective_date": "2026-11-18",
            "governing_law": "Delaware",
        },
    )
    receipt = engine.export_pdf("demo-user", draft.draft_id)
    print(json.dumps({
        "draft_id": receipt.draft_id,
        "template_id": receipt.template_id,
        "parity_verified": receipt.parity_verified,
        "pdf_sha256": receipt.pdf_sha256,
    }, indent=2))


if __name__ == "__main__":
    run_demo()
