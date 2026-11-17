import hashlib
import html
import json
import sqlite3
import uuid
from typing import Dict, List, Optional

from .models import AgreementDraft, AgreementTemplate, ExportReceipt


def _build_catalog() -> Dict[str, AgreementTemplate]:
    specs = [
        ("mutual_nda", "Mutual Non-Disclosure Agreement", ["party_a", "party_b", "effective_date", "governing_law"], ["term_years"]),
        ("one_way_nda", "One-Way Non-Disclosure Agreement", ["disclosing_party", "receiving_party", "effective_date"], ["purpose"]),
        ("consulting_services", "Consulting Services Agreement", ["client_name", "consultant_name", "fee_amount", "start_date"], ["scope"]),
        ("employment_offer", "Employment Offer Letter", ["employer_name", "candidate_name", "role_title", "base_salary"], ["start_date"]),
        ("independent_contractor", "Independent Contractor Agreement", ["company_name", "contractor_name", "rate", "effective_date"], ["deliverables"]),
        ("saas_subscription", "SaaS Subscription Agreement", ["provider_name", "customer_name", "plan_tier", "annual_fee"], ["renewal_term"]),
        ("ip_assignment", "Intellectual Property Assignment", ["assignor", "assignee", "effective_date"], ["consideration"]),
        ("advisory_board", "Advisory Board Agreement", ["company_name", "advisor_name", "equity_grant", "effective_date"], ["vesting_months"]),
        ("data_processing", "Data Processing Addendum", ["controller", "processor", "effective_date"], ["jurisdiction"]),
        ("software_license", "Commercial Software License", ["licensor", "licensee", "license_fee", "effective_date"], ["seat_limit"]),
        ("termination_release", "Mutual Termination and Release", ["party_a", "party_b", "termination_date"], ["settlement_amount"]),
    ]
    catalog: Dict[str, AgreementTemplate] = {}
    for tid, title, req, opt in specs:
        placeholders = " | ".join(f"{k}: {{{k}}}" for k in req + opt)
        catalog[tid] = AgreementTemplate(
            template_id=tid,
            title=title,
            required_fields=req,
            optional_fields=opt,
            body_template=f"{title} — {placeholders}",
        )
    return catalog


class SchemaLockedDrafterEngine:
    """Deterministic, schema-locked legal drafter with user-scoped SQLite storage."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.catalog: Dict[str, AgreementTemplate] = _build_catalog()
        assert len(self.catalog) == 11
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drafts (
                draft_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                template_id TEXT NOT NULL,
                fields_json TEXT NOT NULL,
                preview_html TEXT NOT NULL,
                preview_sha256 TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def list_templates(self) -> List[AgreementTemplate]:
        return list(self.catalog.values())

    def get_template(self, template_id: str) -> AgreementTemplate:
        if template_id not in self.catalog:
            raise ValueError(f"Unknown template_id: {template_id}")
        return self.catalog[template_id]

    def _extract_typed_fields(self, template: AgreementTemplate, raw_fields: Dict[str, object]) -> Dict[str, str]:
        allowed = set(template.required_fields) | set(template.optional_fields)
        extracted: Dict[str, str] = {}
        for key, value in raw_fields.items():
            if key not in allowed:
                raise ValueError(f"Invented or undeclared field '{key}' is not permitted by template '{template.template_id}'")
            if value is not None:
                text = str(value).strip()
                if text:
                    extracted[key] = text
        return extracted

    def _render_preview_html(self, template: AgreementTemplate, fields: Dict[str, str]) -> str:
        safe_parts = [f"<h1>{html.escape(template.title, quote=True)}</h1>", "<dl>"]
        for key in template.required_fields + template.optional_fields:
            raw_val = fields.get(key, "[MISSING]" if key in template.required_fields else "")
            safe_parts.append(f"<dt>{html.escape(key, quote=True)}</dt><dd>{html.escape(raw_val, quote=True)}</dd>")
        safe_parts.append("</dl>")
        return "\n".join(safe_parts)

    def create_draft(self, user_id: str, template_id: str, raw_fields: Optional[Dict[str, object]] = None) -> AgreementDraft:
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required")
        template = self.get_template(template_id)
        fields = self._extract_typed_fields(template, raw_fields or {})
        missing = [f for f in template.required_fields if f not in fields]
        preview_html = self._render_preview_html(template, fields)
        preview_sha256 = hashlib.sha256(preview_html.encode("utf-8")).hexdigest()
        draft_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO drafts (draft_id, user_id, template_id, fields_json, preview_html, preview_sha256) VALUES (?, ?, ?, ?, ?, ?)",
            (draft_id, user_id, template_id, json.dumps(fields, sort_keys=True), preview_html, preview_sha256),
        )
        self.conn.commit()
        return AgreementDraft(
            draft_id=draft_id,
            user_id=user_id,
            template_id=template_id,
            fields=fields,
            missing_fields=missing,
            preview_html=preview_html,
            preview_sha256=preview_sha256,
        )

    def get_draft(self, user_id: str, draft_id: str) -> AgreementDraft:
        row = self.conn.execute(
            "SELECT draft_id, user_id, template_id, fields_json, preview_html, preview_sha256 FROM drafts WHERE draft_id = ? AND user_id = ?",
            (draft_id, user_id),
        ).fetchone()
        if row is None:
            raise PermissionError(f"Draft '{draft_id}' not found for user '{user_id}'")
        template = self.get_template(row[2])
        fields = json.loads(row[3])
        missing = [f for f in template.required_fields if f not in fields]
        return AgreementDraft(
            draft_id=row[0],
            user_id=row[1],
            template_id=row[2],
            fields=fields,
            missing_fields=missing,
            preview_html=row[4],
            preview_sha256=row[5],
        )

    def export_pdf(self, user_id: str, draft_id: str) -> ExportReceipt:
        draft = self.get_draft(user_id, draft_id)
        if draft.missing_fields:
            raise ValueError(f"Export blocked: missing required fields {draft.missing_fields}")
        canonical_payload = draft.preview_html.encode("utf-8")
        pdf_bytes = b"%PDF-1.4\n%SCHEMA-LOCKED\n" + canonical_payload + b"\n%%EOF\n"
        payload_start = len(b"%PDF-1.4\n%SCHEMA-LOCKED\n")
        payload_end = len(pdf_bytes) - len(b"\n%%EOF\n")
        extracted_payload = pdf_bytes[payload_start:payload_end]
        pdf_sha256 = hashlib.sha256(extracted_payload).hexdigest()
        return ExportReceipt(
            draft_id=draft.draft_id,
            user_id=draft.user_id,
            template_id=draft.template_id,
            pdf_bytes=pdf_bytes,
            pdf_sha256=pdf_sha256,
            preview_sha256=draft.preview_sha256,
            parity_verified=(pdf_sha256 == draft.preview_sha256),
        )
