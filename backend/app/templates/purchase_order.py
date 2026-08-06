"""Purchase order extraction template."""

from app.models.domain.template import PipelineTemplate

PURCHASE_ORDER_TEMPLATE = PipelineTemplate(
    template_id="purchase_order",
    name="Purchase Order Extractor",
    description="Extract PO details, line items, shipping info from purchase orders.",
    icon="package",
    category="finance",
    task_description=(
        "Extract purchase order data. "
        "Capture PO number, vendor, ship-to, all line items with SKU/quantity/price."
    ),
    fields=[
        "po_number",
        "po_date",
        "vendor_name",
        "vendor_contact",
        "ship_to_name",
        "ship_to_address",
        "line_items",
        "subtotal",
        "shipping_cost",
        "tax",
        "grand_total",
        "delivery_date",
        "payment_terms",
    ],
    extraction_instructions=(
        "For line_items, return array of {sku, description, quantity, unit_price, total}. "
        "If SKU is not present, use 'N/A'. "
        "shipping_cost should be 0 if free shipping."
    ),
    rules=[
        {
            "field": "grand_total",
            "operator": "gt",
            "value": 100000,
            "flag_name": "large_order",
        },
    ],
    output_format="csv",
    suggested_steps=[
        "processor.ocr",
        "transform.field_extractor",
        "transform.rules",
        "output.formatter",
    ],
    sort_order=5,
)
