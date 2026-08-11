"""Invoice Parser — structured extraction from invoices globally."""

from app.models.domain.template import PipelineTemplate

INVOICE_TEMPLATE = PipelineTemplate(
    template_id="invoice",
    name="Invoice Parser",
    description="Extract vendor details, amounts, dates, and line items from invoices",
    icon="receipt",
    category="finance",
    task_description="Extract structured fields from invoices including vendor info, financial totals, dates, and individual line items",
    fields=[
        "invoice_number",
        "vendor_name",
        "buyer_name",
        "invoice_date",
        "due_date",
        "currency",
        "subtotal",
        "tax_amount",
        "total_amount",
        "po_reference",
        "line_items",
    ],
    extraction_instructions="""Extract all fields from the invoice document.

FIELD LOCATIONS AND GUIDANCE:
- invoice_number: Near top-right of document. Labeled "Invoice #", "Bill No", "Reference", "Inv No", "Document Number". Extract exactly as printed including prefixes (e.g. "INV-2024-0031").
- vendor_name: The company ISSUING the invoice. Found in header/logo area, or "From" / "Seller" / "Billed From" section. Return in Title Case.
- buyer_name: The company RECEIVING the invoice. Found in "Bill To" / "Ship To" / "Customer" / "Billed To" section. Return in Title Case.
- invoice_date: Date the invoice was issued. Look for "Invoice Date", "Date", "Issue Date", "Bill Date". Return as YYYY-MM-DD.
- due_date: Payment deadline. Look for "Due Date", "Payment Due", "Due By". If "Net 30" or "Net 60" stated instead, calculate from invoice_date. Return as YYYY-MM-DD.
- currency: ISO 4217 code inferred from currency symbol or document context. "$" -> "USD", "€" -> "EUR", "₹" -> "INR", "£" -> "GBP".
- subtotal: Amount before tax. Look for "Subtotal", "Sub Total", "Net Amount". Plain number, no symbols.
- tax_amount: Total tax. Look for "Tax", "VAT", "GST", "Sales Tax". If tax is split (CGST + SGST), SUM them. Plain number, no symbols. Null if no tax line exists.
- total_amount: Final amount due. Look for "Total", "Grand Total", "Amount Due", "Balance Due". Usually the largest/boldest number, often at bottom. Plain number, no symbols.
- po_reference: Purchase order number referenced on the invoice. Look for "PO #", "PO Number", "Purchase Order", "Order Ref". Null if not present.
- line_items: Array of objects from the line item table. Each object: {"description": string, "quantity": number, "unit_price": number, "amount": number}. Extract ALL rows. If quantity is blank, default to 1. If a description spans multiple lines, merge into one item. "amount" should be quantity x unit_price if not explicitly stated.

If a field is not present in the document, return null. Never guess.

EXAMPLE EXTRACTION:
Input text: "Invoice #INV-2024-0031 | Date: March 15, 2024 | Due: April 14, 2024\\nFrom: Acme Corp\\nTo: Widget Inc\\nSubtotal: $1,200.00 | Tax (10%): $120.00 | Total: $1,320.00"
Output: {"invoice_number": "INV-2024-0031", "vendor_name": "Acme Corp", "buyer_name": "Widget Inc", "invoice_date": "2024-03-15", "due_date": "2024-04-14", "currency": "USD", "subtotal": 1200.00, "tax_amount": 120.00, "total_amount": 1320.00, "po_reference": null, "line_items": []}""",
    rules=[
        {
            "field": "total_amount",
            "operator": "gt",
            "value": 10000,
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
