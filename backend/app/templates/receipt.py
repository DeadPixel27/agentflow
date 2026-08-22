"""Receipt Scanner — expense extraction from receipts and POS printouts."""

from app.models.domain.template import PipelineTemplate

RECEIPT_TEMPLATE = PipelineTemplate(
    template_id="receipt",
    name="Receipt Scanner",
    description="Extract merchant, totals, payment method, and line items from receipts",
    icon="scan",
    category="finance",
    task_description="Extract expense data from receipts including merchant info, transaction totals, payment details, and individual items",
    fields=[
        "merchant_name",
        "store_address",
        "receipt_date",
        "receipt_number",
        "currency",
        "subtotal",
        "tax_amount",
        "total_amount",
        "payment_method",
        "card_last_four",
        "expense_category",
        "line_items",
    ],
    extraction_instructions="""Extract all fields from the receipt. Receipts are often low-quality scans or phone photos with faded thermal paper text - extract what you can clearly read, return null for anything unclear.

FIELD LOCATIONS AND GUIDANCE:
- merchant_name: Usually at the very top, largest text, often the store/restaurant name. Return in Title Case. If a franchise brand is shown (e.g. McDonald's, Starbucks) but the legal entity is not legible, use the brand name.
- store_address: Below merchant name. Single string with commas. Null if not legible.
- receipt_date: Look for date near top or bottom. Formats vary: "03/15/24", "2024-03-15", "Mar 15 2024", "15.03.2024". Return as YYYY-MM-DD.
- receipt_number: Look for "Receipt #", "Trans #", "Transaction", "Check #", "Ticket". Often near top or bottom. Extract exactly as printed. Null if not present - many receipts don't have one.
- currency: Infer from symbol or locale. "$" -> "USD" unless context suggests otherwise (CAD, AUD).
- subtotal: Amount before tax. Look for "Subtotal", "Sub". Plain number.
- tax_amount: Look for "Tax", "VAT", "GST", "HST". If multiple tax lines, SUM them. Null if no tax line.
- total_amount: Final amount paid/charged. Look for "Total", "Amount", "Grand Total", "Amount Paid", "Amount paid", "Paid". The value may be on the next line after the label. Plain number. Include tip if the receipt shows one final total after tip.
- payment_method: How it was paid. Look for "VISA", "MASTERCARD", "AMEX", "CASH", "DEBIT", card logos. Return one of: "credit_card", "debit_card", "cash", "mobile_payment", "other". Null if unclear.
- card_last_four: Last 4 digits of card number. ONLY extract if clearly printed (e.g. "****1234", "XXXX-XXXX-XXXX-5678"). Do NOT guess. Null if not visible.
- expense_category: Infer from merchant name and items. One of: "meals", "transport", "office_supplies", "groceries", "entertainment", "travel", "utilities", "other".
- line_items: Array of {"description": string, "quantity": number, "amount": number}. Receipt items are often abbreviated ("LG COFFEE BLK"). Extract description as-is. If quantity not shown, default to 1.

IMPORTANT FOR RECEIPTS:
- Text may be faded, tilted, or partially cut off - extract what you can see clearly.
- Do NOT hallucinate values from blurry or illegible text. Return null instead.
- Prices may appear on the same line as the item or on the next line.

EXAMPLE EXTRACTION:
Input: "STARBUCKS #12345\\n123 MAIN ST\\n03/15/2024 10:32AM\\nLG PIKE PLACE    4.95\\nCROISSANT        3.50\\nSUBTOTAL        8.45\\nTAX        0.74\\nTOTAL        9.19\\nVISA ****1234"
Output: {"merchant_name": "Starbucks", "store_address": "123 Main St", "receipt_date": "2024-03-15", "receipt_number": null, "currency": "USD", "subtotal": 8.45, "tax_amount": 0.74, "total_amount": 9.19, "payment_method": "credit_card", "card_last_four": "1234", "expense_category": "meals", "line_items": [{"description": "LG Pike Place", "quantity": 1, "amount": 4.95}, {"description": "Croissant", "quantity": 1, "amount": 3.50}]}""",
    rules=[
        {
            "field": "total_amount",
            "operator": "gt",
            "value": 500,
            "flag_name": "high_expense",
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
