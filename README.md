# Schema-Locked Legal Drafter

> **Project 14 (C3: AI Coder)** — Template-constrained legal agreement drafting SaaS across **11 document schemas** with typed extraction, XSS-escaped live preview, and user-scoped SQLite storage.

## Attribution

Inspired by and adapted from [**ed-donner/prelegal**](https://github.com/ed-donner/prelegal), re-engineered with strict schema-locked generation, deterministic HTML/XSS escaping, and user-scoped SQLite persistence.

---

## Architecture Overview

```
+-------------------+      +-----------------------+      +----------------------+
|  Next.js / CLI    | ---> |  FastAPI / LiteLLM    | ---> |  Schema-Locked       |
|  Client           |      |  Typed Extraction     |      |  Template Renderer   |
+-------------------+      +-----------------------+      +----------------------+
                                      |                              |
                                      v                              v
                           +-----------------------+      +----------------------+
                           |  11 Locked Document   |      |  XSS-Escaped Live    |
                           |  Schemas & Validators |      |  HTML/Markdown View  |
                           +-----------------------+      +----------------------+
                                      |
                                      v
                           +-----------------------+
                           |  User-Scoped SQLite   |
                           |  Storage & Audit Log  |
                           +-----------------------+
```

---

## 6-Stage Workflow

1. **Schema Selection**: User selects one of the 11 supported legal agreement schemas (`nda_mutual`, `nda_one_way`, `msa`, `sow`, `consulting_agreement`, `employment_offer`, `ip_assignment`, `dpa`, `saas_subscription`, `advisor_agreement`, `settlement_release`).
2. **Typed Field Extraction**: Natural language deal notes or structured form inputs are parsed into strongly typed schema fields (`DocumentFieldValues`) with required-field and enum validation.
3. **Schema-Locked Validation**: Any missing required clauses, invalid governing law values, or unapproved clause injections are rejected before rendering.
4. **Template-Constrained Rendering**: Approved field values populate deterministic, immutable legal template skeletons—preventing LLM hallucination of unauthorized legal terms.
5. **XSS-Escaped Live Preview**: Every interpolated user string is escaped with `html.escape(..., quote=True)` prior to rendering live HTML previews.
6. **User-Scoped SQLite Persistence**: Drafts and revision receipts are persisted in SQLite keyed by `(user_id, draft_id)`, enforcing strict tenant isolation on reads and updates.

---

## Data Contract

- `DocumentSchema`: Defines `schema_id`, `title`, `required_fields`, `optional_fields`, and `template_body`.
- `DraftRequest`: Captures `user_id`, `schema_id`, `raw_inputs`, and optional `draft_id`.
- `DraftResult`: Returns `draft_id`, `user_id`, `schema_id`, `validated_fields`, `rendered_text`, `escaped_preview_html`, and `created_at`.

---

## Production Controls

- **Zero Free-Form Clause Hallucination**: Only pre-approved template skeletons are rendered; AI extraction is confined to typed slot values.
- **XSS Prevention**: All user-supplied values are HTML-escaped (`<`, `>`, `&`, `"`, `'`) in live preview output.
- **User-Scoped Access Control**: `get_draft(draft_id, user_id)` and `list_drafts(user_id)` reject cross-user access with `UnauthorizedDraftAccessError`.
- **CI & Evaluation**: Automated `pytest` suite and `evaluation/eval_cases.json` verify schema coverage, XSS escaping, and tenant isolation.

---

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run CLI demo
python -m legal_drafter.cli

# Run test suite
pytest -q
```
