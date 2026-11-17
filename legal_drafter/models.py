from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class AgreementTemplate:
    template_id: str
    title: str
    required_fields: List[str]
    optional_fields: List[str]
    body_template: str


@dataclass
class AgreementDraft:
    draft_id: str
    user_id: str
    template_id: str
    fields: Dict[str, str] = field(default_factory=dict)
    missing_fields: List[str] = field(default_factory=list)
    preview_html: str = ""
    preview_sha256: str = ""


@dataclass(frozen=True)
class ExportReceipt:
    draft_id: str
    user_id: str
    template_id: str
    pdf_bytes: bytes
    pdf_sha256: str
    preview_sha256: str
    parity_verified: bool
