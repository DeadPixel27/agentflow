"""Receipt / expense extraction template."""

from app.models.domain.template import PipelineTemplate

RECEIPT_TEMPLATE = PipelineTemplate(
    template_id="receipt",
    name="Receipt Scanner",
    description="Extract merchant, total, tax, items from receipts for expense reports.",
    icon="credit-card",
    category="finance",
    task_description=(
        "Extract expense data from these receipts. "
        "Capture merchant name, total, tax, payment method, and line items."
    ),
    fields=[
        "merchant_name",
        "merchant_address",
        "receipt_date",
        "receipt_number",
        "subtotal",
        "tax_amount",
        "tip_amount",
        "total_amount",
        "payment_method",
        "card_last_four",
        "line_items",
        "expense_category",
    ],
    extraction_instructions=(
        "For line_items, return array of {item, quantity, price}. "
        "expense_category should be one of: meals, travel, office_supplies, "
        "software, equipment, entertainment, utilities, other. "
        "Infer category from merchant name and items. "
        "If tip is not present, set tip_amount to 0."
    ),
    rules=[
        {
            "field": "total_amount",
            "operator": "gt",
            "value": 5000,
            "flag_name": "needs_approval",
        },
    ],
    output_format="csv",
    suggested_steps=[
        "processor.ocr",
        "transform.field_extractor",
        "transform.rules",
        "output.formatter",
    ],
    sort_order=4,
)
