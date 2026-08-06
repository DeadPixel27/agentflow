"""Invoice extraction template."""

from app.models.domain.template import PipelineTemplate

INVOICE_TEMPLATE = PipelineTemplate(
    template_id="invoice",
    name="Invoice Parser",
    description="Extract vendor, amounts, dates, line items from invoices.",
    icon="receipt",
    category="finance",
    task_description=(
        "Extract structured data from these invoices. "
        "Pull header fields and all line items. "
        "Normalize amounts to numbers (no currency symbols). "
        "Dates in ISO format (YYYY-MM-DD)."
    ),
    fields=[
        "invoice_number",
        "vendor_name",
        "vendor_address",
        "invoice_date",
        "due_date",
        "subtotal",
        "tax_amount",
        "total_amount",
        "currency",
        "payment_terms",
        "line_items",
    ],
    extraction_instructions=(
        "For line_items, return an array of objects with keys: "
        "description, quantity, unit_price, amount. "
        "If tax is not explicitly stated, set tax_amount to null. "
        "payment_terms examples: 'Net 30', 'Due on receipt', 'Net 60'. "
        "If multiple currencies appear, use the one on the total line."
    ),
    rules=[
        {
            "field": "total_amount",
            "operator": "gt",
            "value": 50000,
            "flag_name": "high_value_invoice",
        },
        {
            "field": "due_date",
            "operator": "lt",
            "value": "today",
            "flag_name": "overdue",
        },
    ],
    output_format="csv",
    suggested_steps=[
        "processor.ocr",
        "transform.field_extractor",
        "transform.rules",
        "output.formatter",
    ],
    sort_order=1,
)
