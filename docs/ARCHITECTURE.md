# Architecture: Schema-Locked Legal Drafter

## System Overview
The Schema-Locked Legal Drafter enforces deterministic, template-bound contract generation. All drafts are constrained to a locked 11-template catalog (`AgreementTemplate`) with zero invented clauses or unvalidated free-form legal text.

## Core Components
- **`legal_drafter/models.py`**: Defines `AgreementTemplate`, `AgreementDraft`, and `ExportReceipt` dataclasses with strict field metadata and validation states.
- **`legal_drafter/engine.py`**: Implements `SchemaLockedDrafterEngine`:
  1. **11-Template Catalog Validation**: Rejects unknown template IDs and enforces exact required/optional field schemas.
  2. **Typed Field Extraction**: Validates and coerces typed inputs (strings, dates, amounts) without generating or inventing clauses.
  3. **HTML XSS Escaping**: Escapes all user-supplied values via `html.escape(..., quote=True)` when rendering live HTML previews.
  4. **User-Scoped SQLite Storage**: Persists drafts in SQLite partitioned by `user_id`, preventing cross-user reads or exports.
  5. **100% Required-Field Export Gate**: Blocks PDF export until every required template field is populated and validated, guaranteeing preview-to-PDF byte parity via SHA-256 checksums.
- **`legal_drafter/cli.py`**: Runnable CLI demo entrypoint demonstrating template listing, draft creation, live preview rendering, and gated PDF export.
