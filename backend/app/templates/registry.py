"""Template registry — canonical source of pipeline template definitions."""

from typing import Optional

from app.models.domain.template import PipelineTemplate
from app.templates.contract import CONTRACT_TEMPLATE
from app.templates.invoice import INVOICE_TEMPLATE
from app.templates.medical_bill import MEDICAL_BILL_TEMPLATE
from app.templates.purchase_order import PURCHASE_ORDER_TEMPLATE
from app.templates.real_estate import LEASE_TEMPLATE
from app.templates.receipt import RECEIPT_TEMPLATE
from app.templates.resume import RESUME_TEMPLATE

ALL_TEMPLATES: list[PipelineTemplate] = [
    INVOICE_TEMPLATE,
    RESUME_TEMPLATE,
    CONTRACT_TEMPLATE,
    RECEIPT_TEMPLATE,
    PURCHASE_ORDER_TEMPLATE,
    LEASE_TEMPLATE,
    MEDICAL_BILL_TEMPLATE,
]

_TEMPLATES_BY_ID: dict[str, PipelineTemplate] = {
    template.template_id: template for template in ALL_TEMPLATES
}


def get_all_templates() -> list[PipelineTemplate]:
    return list(ALL_TEMPLATES)


def get_template_by_id(template_id: str) -> Optional[PipelineTemplate]:
    return _TEMPLATES_BY_ID.get(template_id)
