"""Purchase Order Extractor — structured extraction from POs."""

from app.models.domain.template import PipelineTemplate

PURCHASE_ORDER_TEMPLATE = PipelineTemplate(
    template_id="purchase_order",
    name="Purchase Order Extractor",
    description="Extract PO details, vendor info, shipping, and line items from purchase orders",
    icon="clipboard-list",
    category="finance",
    task_description="Extract structured fields from purchase orders including PO number, vendor, dates, shipping details, and line items",
    fields=[
        "po_number",
        "vendor_name",
        "buyer_name",
        "po_date",
        "delivery_date",
        "currency",
        "subtotal",
        "tax_amount",
        "total_amount",
        "ship_to_address",
        "line_items",
    ],
    extraction_instructions="""Extract all fields from the purchase order document.

FIELD LOCATIONS AND GUIDANCE:
- po_number: Near top of document. Labeled "PO #", "Purchase Order", "Order Number", "PO Number". Extract exactly as printed.
- vendor_name: The supplier receiving the order. Look for "Vendor", "Supplier", "Ship From", "Sold By". Return in Title Case.
- buyer_name: The company placing the order. Look for "Buyer", "Company", "Ordered By", "Bill To". Usually the company with the logo.
- po_date: Date the PO was issued. Look for "PO Date", "Order Date", "Date". Return as YYYY-MM-DD.
- delivery_date: Expected/required delivery. Look for "Delivery Date", "Required By", "Ship By", "Expected Delivery", "ETA". Return as YYYY-MM-DD. Null if not specified.
- currency: ISO 4217 code from symbol or context.
- subtotal: Amount before tax. Plain number.
- tax_amount: Tax total. Null if not present (many POs omit tax).
- total_amount: Final PO value. Plain number.
- ship_to_address: Delivery address. Single string with commas. Null if same as buyer address or not specified.
- line_items: Array of {"description": string, "sku": string or null, "quantity": number, "unit_price": number, "amount": number}. Extract ALL rows from the order table. SKU/part number may be labeled "Item #", "SKU", "Part No", "Catalog #".

If a field is not present, return null. Do not default amounts to 0 - use null.

EXAMPLE EXTRACTION:
Input: "PURCHASE ORDER PO-2024-0587\\nDate: 2024-03-15\\nVendor: Industrial Supply Co\\nBuyer: Acme Manufacturing\\nShip To: 789 Factory Rd, Detroit, MI 48201\\nDelivery: April 1, 2024\\n1x Widget A (SKU: WA-100) @ $50.00 = $50.00\\n5x Bolt Pack (SKU: BP-200) @ $12.00 = $60.00\\nSubtotal: $110.00 | Tax: $9.90 | Total: $119.90"
Output: {"po_number": "PO-2024-0587", "vendor_name": "Industrial Supply Co", "buyer_name": "Acme Manufacturing", "po_date": "2024-03-15", "delivery_date": "2024-04-01", "currency": "USD", "subtotal": 110.00, "tax_amount": 9.90, "total_amount": 119.90, "ship_to_address": "789 Factory Rd, Detroit, MI 48201", "line_items": [{"description": "Widget A", "sku": "WA-100", "quantity": 1, "unit_price": 50.00, "amount": 50.00}, {"description": "Bolt Pack", "sku": "BP-200", "quantity": 5, "unit_price": 12.00, "amount": 60.00}]}""",
    rules=[
        {
            "field": "total_amount",
            "operator": "gt",
            "value": 50000,
            "flag_name": "high_value_po",
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
