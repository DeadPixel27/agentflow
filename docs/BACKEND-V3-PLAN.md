# Backend V3 — Extraction Hardening + Refiner Plan Mode

> Transcribed from `backend-v3-opus4.6/` screenshots (Aug 8, 2026). Source images gitignored.

> **What this is:** One-shot Cursor prompt. Harden extraction + add Plan Mode refinement chat.
> All changes in `backend/`. ~6-7 hours total.
>
> **How to use:** Paste from START to END into Cursor.

---

## --- START PROMPT ---

You are hardening extraction quality and adding Plan Mode refinement to the AgentFlow backend. Codebase: `github.com/kabirrao2002/agentflow`, branch `develop`, working in `backend/`.

### What this covers (10 tasks):
1. Harden `field_extractor.py` SYSTEM_PROMPT (normalization rules)
2. Rewrite Invoice template (rich instructions + few-shot)
3. Rewrite Receipt template (OCR-specific)
4. Trim Contract template (16 → 9 fields)
5. Trim Lease template (18 → 11 fields)
6. Improve Purchase Order instructions
7. Add Bank Statement template
8. Improve Refiner system prompt (few-shot + classification)
9. Remove sample_results[:3] cap + add refinement history chain
10. Add Plan Mode refinement chat endpoint (cheap clarification before expensive re-run)

---

### TASK 1: Harden `field_extractor.py` SYSTEM_PROMPT

**File:** `app/services/extraction/field_extractor.py`

Find the current `SYSTEM_PROMPT` string and REPLACE it with:

```python
SYSTEM_PROMPT = """You are a precise document data extractor. Given document text and a list of fields to extract, return a JSON object with the extracted values.

CRITICAL RULES:
- Extract ONLY information explicitly present in the document. Never infer or guess.
- If a field is not clearly present, return null. It is BETTER to return null than an incorrect value.
- Search the ENTIRE document for each field — headers, footers, sidebars, tables, fine print.
- For array fields (e.g. line_items), extract ALL matching rows. Do not truncate.

NORMALIZATION RULES:
- Dates: ALWAYS return YYYY-MM-DD regardless of input format.
  Handle: DD/MM/YYYY, MM/DD/YYYY, DD.MM.YYYY, "March 15, 2024", "15th Mar '24", "15-Mar-2024".
  When ambiguous (e.g. 01/02/2024), infer from document context (country, language, other dates).
  If still ambiguous, prefer DD/MM/YYYY.
- Amounts: Return plain numbers ONLY. Strip ALL currency symbols ($, €, £, ¥, ₹),
  commas, spaces, and thousand separators.
  "$1,234.56" -> 1234.56 | "€1.234,56" -> 1234.56 | "₹1,50,000" -> 150000 | "£12,000" -> 12000
- Currency: Return ISO 4217 3-letter code. "$" -> "USD", "€" -> "EUR", "₹" -> "INR", "£" -> "GBP", "¥" -> "JPY".
  If no symbol, infer from address/locale. If unknown, return null.
- Phone numbers: Digits and + only. "+1 (555) 123-4567" -> "+15551234567"
- Names: Title Case. "JOHN DOE" -> "John Doe", "josé garcía" -> "José García".
- Tax IDs: Extract as-is (GSTIN, VAT, EIN, ABN, etc.) — do not normalize.
- Addresses: Single string with commas. Preserve structure.

SYNONYM AWARENESS (extract even if labeled differently):
- Invoice Number = Bill No, Reference, Factura Nr, Rechnungsnummer, Invoice #, Document Number
- Vendor/seller = Supplier, Billed From, Party Name, Company Name, From
- Buyer = Bill To, Customer, Billed To, Ship To, Purchaser
- Total Amount = Grand Total, Net Amount, Amount Due, Balance Due, Gesamtbetrag
- Tax = VAT, GST, Sales Tax, TVA, MwSt, IGST, CGST, SGST, HST
- Date = Invoice Date, Bill Date, Issue Date, Document Date, Rechnungsdatum

Return ONLY valid JSON. No markdown, no explanation, no extra text."""
```

---

### TASK 2: Rewrite Invoice Template

**File:** `app/templates/invoice.py`

Replace the ENTIRE file content with:

```python
"""Invoice Parser — structured extraction from invoices globally."""

from app.models.domain.template import PipelineTemplate

invoice_template = PipelineTemplate(
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
        {
            "step_order": 1,
            "agent_type": "processor.ocr",
            "config": {},
            "reason": "Many invoices arrive as scans or photos - OCR extracts text first",
        },
        {
            "step_order": 2,
            "agent_type": "transform.field_extractor",
            "config": {},
            "reason": "LLM extracts structured fields from invoice text",
        },
        {
            "step_order": 3,
            "agent_type": "transform.rules",
            "config": {},
            "reason": "Flag high-value and overdue invoices",
        },
        {
            "step_order": 4,
            "agent_type": "output.formatter",
            "config": {"format": "csv"},
            "reason": "Format results for download or delivery",
        },
    ],
)
```

---

### TASK 3: Rewrite Receipt Template

**File:** `app/templates/receipt.py`

Replace the ENTIRE file content with:

```python
"""Receipt Scanner — expense extraction from receipts and POS printouts."""

from app.models.domain.template import PipelineTemplate

receipt_template = PipelineTemplate(
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
- merchant_name: Usually at the very top, largest text, often the store/restaurant name. Return in Title Case.
- store_address: Below merchant name. Single string with commas. Null if not legible.
- receipt_date: Look for date near top or bottom. Formats vary: "03/15/24", "2024-03-15", "Mar 15 2024", "15.03.2024". Return as YYYY-MM-DD.
- receipt_number: Look for "Receipt #", "Trans #", "Transaction", "Check #", "Ticket". Often near top or bottom. Extract exactly as printed. Null if not present - many receipts don't have one.
- currency: Infer from symbol or locale. "$" -> "USD" unless context suggests otherwise (CAD, AUD).
- subtotal: Amount before tax. Look for "Subtotal", "Sub". Plain number.
- tax_amount: Look for "Tax", "VAT", "GST", "HST". If multiple tax lines, SUM them. Null if no tax line.
- total_amount: Final amount. Usually largest number, near bottom, labeled "Total", "Amount", "Grand Total". Plain number.
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
        {
            "step_order": 1,
            "agent_type": "processor.ocr",
            "config": {},
            "reason": "Receipts are almost always scans or photos - OCR is required",
        },
        {
            "step_order": 2,
            "agent_type": "transform.field_extractor",
            "config": {},
            "reason": "LLM extracts structured fields from receipt text",
        },
        {
            "step_order": 3,
            "agent_type": "transform.rules",
            "config": {},
            "reason": "Flag high-expense receipts",
        },
        {
            "step_order": 4,
            "agent_type": "output.formatter",
            "config": {"format": "csv"},
            "reason": "Format results for expense reporting",
        },
    ],
)
```

---

### TASK 4: Trim Contract Template (16 → 9 fields)

**File:** `app/templates/contract.py`

Replace the ENTIRE file content with:

```python
"""Contract Analyzer — key term extraction from legal agreements."""

from app.models.domain.template import PipelineTemplate

contract_template = PipelineTemplate(
    template_id="contract",
    name="Contract Analyzer",
    description="Extract key terms, dates, parties, and financial details from contracts and agreements",
    icon="file-text",
    category="legal",
    task_description="Extract core contract terms including parties, dates, value, and key clauses from legal agreements",
    fields=[
        "contract_type",
        "party_a_name",
        "party_b_name",
        "effective_date",
        "expiration_date",
        "contract_value",
        "currency",
        "governing_law",
        "auto_renewal",
    ],
    extraction_instructions="""Extract core contract terms. Contracts are dense legal documents - focus on clearly stated facts, not interpretations.

FIELD LOCATIONS AND GUIDANCE:
- contract_type: The kind of agreement. Usually stated in the title or first paragraph. One of: "NDA", "Service Agreement", "Employment Contract", "Lease", "Partnership", "License", "Purchase Agreement", "Other". If unclear, return "Other".
- party_a_name: First named party. Usually in the preamble ("This agreement is between [Party A] and [Party B]"). Also called "Company", "Employer", "Licensor", "Landlord". Return full legal name.
- party_b_name: Second named party. Also called "Contractor", "Employee", "Licensee", "Tenant". Return full legal name.
- effective_date: When the contract takes effect. Look for "Effective Date", "Commencement Date", "dated as of". Return as YYYY-MM-DD.
- expiration_date: When the contract ends. Look for "Termination Date", "End Date", "Expiry", "Term: 12 months from...". If "perpetual" or "until terminated", return null. Return as YYYY-MM-DD.
- contract_value: Total monetary value or annual value. Look for "Total Value", "Annual Fee", "Contract Price", "Compensation". Plain number. Null if not a financial contract (e.g. NDA).
- currency: ISO 4217 code. Infer from document context.
- governing_law: Jurisdiction. Look for "Governing Law", "This agreement shall be governed by the laws of...". Return as stated (e.g. "State of Delaware", "England and Wales", "India").
- auto_renewal: Boolean. Does the contract auto-renew? Look for "automatically renew", "auto-renewal", "evergreen". Return true/false. If not mentioned, return false.

IMPORTANT:
- Do NOT attempt to extract obligations, liability caps, or clause interpretations - these require legal judgment.
- Extract only clearly stated facts and terms.
- If a field requires interpretation, return null.

EXAMPLE EXTRACTION:
Input: "SERVICE AGREEMENT\\nThis Agreement is entered into as of January 1, 2024 between Acme Corp ('Company') and Jane Smith ('Contractor').\\nTerm: 12 months, ending December 31, 2024. Auto-renews annually unless 30 days notice.\\nCompensation: $120,000 per year.\\nGoverning Law: State of California."
Output: {"contract_type": "Service Agreement", "party_a_name": "Acme Corp", "party_b_name": "Jane Smith", "effective_date": "2024-01-01", "expiration_date": "2024-12-31", "contract_value": 120000, "currency": "USD", "governing_law": "State of California", "auto_renewal": true}""",
    rules=[
        {
            "field": "expiration_date",
            "operator": "lt",
            "value": "today",
            "flag_name": "expired_contract",
        },
    ],
    output_format="json",
    suggested_steps=[
        {
            "step_order": 1,
            "agent_type": "processor.text_extract",
            "config": {},
            "reason": "Contracts are typically digital PDFs with embedded text",
        },
        {
            "step_order": 2,
            "agent_type": "transform.field_extractor",
            "config": {},
            "reason": "LLM extracts key contract terms",
        },
        {
            "step_order": 3,
            "agent_type": "transform.rules",
            "config": {},
            "reason": "Flag expired contracts",
        },
        {
            "step_order": 4,
            "agent_type": "output.formatter",
            "config": {"format": "json"},
            "reason": "Format results as JSON for review",
        },
    ],
)
```

---

### TASK 5: Trim Lease Template (18 → 11 fields)

**File:** `app/templates/real_estate.py`

Replace the ENTIRE file content with:

```python
"""Lease Analyzer — extraction from rental and lease agreements."""

from app.models.domain.template import PipelineTemplate

real_estate_template = PipelineTemplate(
    template_id="real_estate",
    name="Lease Analyzer",
    description="Extract key terms from rental and lease agreements",
    icon="home",
    category="real_estate",
    task_description="Extract property details, parties, financial terms, and key dates from lease agreements",
    fields=[
        "property_address",
        "property_type",
        "landlord_name",
        "tenant_name",
        "lease_start_date",
        "lease_end_date",
        "monthly_rent",
        "security_deposit",
        "currency",
        "pet_policy",
        "auto_renewal",
    ],
    extraction_instructions="""Extract core lease terms. Focus on clearly stated facts and financial terms.

FIELD LOCATIONS AND GUIDANCE:
- property_address: Full address of the rental property. Usually in the preamble or "Premises" section. Single string with commas.
- property_type: One of: "apartment", "house", "condo", "commercial", "office", "retail", "industrial", "other". Infer from context if not explicitly stated.
- landlord_name: Property owner or management company. Look for "Landlord", "Lessor", "Owner", "Property Manager". Full legal name.
- tenant_name: Person or entity renting. Look for "Tenant", "Lessee", "Renter". Full legal name.
- lease_start_date: Look for "Commencement Date", "Start Date", "Beginning". Return as YYYY-MM-DD.
- lease_end_date: Look for "Termination Date", "End Date", "Expiration". Return as YYYY-MM-DD. If "month-to-month", return null.
- monthly_rent: Monthly payment amount. Look for "Rent", "Monthly Rent", "Base Rent". Plain number. If annual rent given, divide by 12.
- security_deposit: Look for "Security Deposit", "Deposit", "Bond". Plain number.
- currency: ISO 4217 code inferred from document.
- pet_policy: One of: "allowed", "not_allowed", "conditional", "not_mentioned". Look for "Pets", "Animals", "Pet Policy" sections.
- auto_renewal: Boolean. Does the lease auto-renew or convert to month-to-month? Look for "renewal", "automatically extend". Return true/false.

EXAMPLE EXTRACTION:
Input: "RESIDENTIAL LEASE AGREEMENT\\nLandlord: Green Property LLC\\nTenant: John Smith\\nPremises: 456 Oak Ave, Apt 2B, Portland, OR 97201\\nTerm: July 1, 2024 to June 30, 2025\\nRent: $1,850/month, due on the 1st\\nDeposit: $3,700\\nPets: Small dogs allowed with $500 pet deposit"
Output: {"property_address": "456 Oak Ave, Apt 2B, Portland, OR 97201", "property_type": "apartment", "landlord_name": "Green Property LLC", "tenant_name": "John Smith", "lease_start_date": "2024-07-01", "lease_end_date": "2025-06-30", "monthly_rent": 1850, "security_deposit": 3700, "currency": "USD", "pet_policy": "conditional", "auto_renewal": false}""",
    rules=[
        {
            "field": "lease_end_date",
            "operator": "lt",
            "value": "today",
            "flag_name": "lease_expired",
        },
    ],
    output_format="json",
    suggested_steps=[
        {
            "step_order": 1,
            "agent_type": "processor.text_extract",
            "config": {},
            "reason": "Leases are typically digital PDFs with embedded text",
        },
        {
            "step_order": 2,
            "agent_type": "transform.field_extractor",
            "config": {},
            "reason": "LLM extracts key lease terms",
        },
        {
            "step_order": 3,
            "agent_type": "transform.rules",
            "config": {},
            "reason": "Flag expired leases",
        },
        {
            "step_order": 4,
            "agent_type": "output.formatter",
            "config": {"format": "json"},
            "reason": "Format results as JSON",
        },
    ],
)
```

---

### TASK 6: Improve Purchase Order Instructions

**File:** `app/templates/purchase_order.py`

Replace the ENTIRE file content with:

```python
"""Purchase Order Extractor — structured extraction from POs."""

from app.models.domain.template import PipelineTemplate

purchase_order_template = PipelineTemplate(
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
        {
            "step_order": 1,
            "agent_type": "processor.ocr",
            "config": {},
            "reason": "POs may arrive as scans or PDFs - OCR handles both",
        },
        {
            "step_order": 2,
            "agent_type": "transform.field_extractor",
            "config": {},
            "reason": "LLM extracts structured fields from PO text",
        },
        {
            "step_order": 3,
            "agent_type": "transform.rules",
            "config": {},
            "reason": "Flag high-value purchase orders",
        },
        {
            "step_order": 4,
            "agent_type": "output.formatter",
            "config": {"format": "csv"},
            "reason": "Format results for procurement systems",
        },
    ],
)
```

---

### TASK 7: Add Bank Statement Template

**New file:** `app/templates/bank_statement.py`

```python
"""Bank Statement Parser — transaction extraction from bank statements."""

from app.models.domain.template import PipelineTemplate

bank_statement_template = PipelineTemplate(
    template_id="bank_statement",
    name="Bank Statement Parser",
    description="Extract account details and all transactions from bank statements",
    icon="landmark",
    category="finance",
    task_description="Extract account information, balances, and every transaction from bank or financial statements",
    fields=[
        "account_holder",
        "account_number",
        "bank_name",
        "statement_period",
        "currency",
        "opening_balance",
        "closing_balance",
        "transactions",
    ],
    extraction_instructions="""Extract account details and ALL transactions from the bank statement.

FIELD LOCATIONS AND GUIDANCE:
- account_holder: Name on the account. Usually near top, labeled "Account Holder", "Name", "Customer". Return full name.
- account_number: Account number as printed. Often partially masked (e.g. "****1234", "XXXX-5678"). Extract exactly as shown.
- bank_name: Name of the financial institution. Usually in header/logo area.
- statement_period: The date range this statement covers. Look for "Statement Period", "From/To", "Period". Return as a string: "YYYY-MM-DD to YYYY-MM-DD".
- currency: ISO 4217 code. Infer from symbol, bank locale, or explicit mention.
- opening_balance: Balance at start of period. Look for "Opening Balance", "Beginning Balance", "Previous Balance", "Balance Brought Forward". Plain number.
- closing_balance: Balance at end of period. Look for "Closing Balance", "Ending Balance", "Balance Carried Forward". Plain number.
- transactions: Array of ALL transaction rows. Each object: {"date": "YYYY-MM-DD", "description": string, "amount": number, "type": "debit" or "credit"}.
  - date: Transaction date. Return as YYYY-MM-DD.
  - description: Transaction description or payee. Extract as-is but trim excess whitespace.
  - amount: Transaction amount as a POSITIVE number (always positive).
  - type: "debit" if it reduces the balance (withdrawals, payments, fees), "credit" if it increases it (deposits, transfers in, interest).
Look for the transaction table - it may span multiple pages. Extract EVERY row, do not truncate.

IMPORTANT:
- Bank statements can be multi-page. Transaction tables may continue across pages - extract ALL rows.
- Debit/credit may be indicated by: separate columns (Debit | Credit), +/- signs, "DR"/"CR" labels, or parentheses for debits.
- Running balance column (if present) is NOT a transaction - do not extract it as a transaction.
- Header rows, subtotals, and page footers should NOT be extracted as transactions.

EXAMPLE EXTRACTION:
Input: "FIRST NATIONAL BANK\\nAccount: John Smith | ****4567\\nPeriod: Mar 1-31, 2024\\nOpening: $5,230.00\\n03/01 PAYROLL DEPOSIT  +2,500.00\\n03/05 AMAZON.COM -89.99\\n03/10 RENT PAYMENT  -1,500.00\\nClosing: $6,140.01"
Output: {"account_holder": "John Smith", "account_number": "****4567", "bank_name": "First National Bank", "statement_period": "2024-03-01 to 2024-03-31", "currency": "USD", "opening_balance": 5230.00, "closing_balance": 6140.01, "transactions": [{"date": "2024-03-01", "description": "Payroll Deposit", "amount": 2500.00, "type": "credit"}, {"date": "2024-03-05", "description": "Amazon.com", "amount": 89.99, "type": "debit"}, {"date": "2024-03-10", "description": "Rent Payment", "amount": 1500.00, "type": "debit"}]}""",
    rules=[
        {
            "field": "transactions",
            "operator": "gt",
            "value": 5000,
            "flag_name": "large_transaction",
        },
    ],
    output_format="csv",
    suggested_steps=[
        {
            "step_order": 1,
            "agent_type": "processor.ocr",
            "config": {},
            "reason": "Bank statements may be scanned or digital - OCR handles both",
        },
        {
            "step_order": 2,
            "agent_type": "transform.field_extractor",
            "config": {},
            "reason": "LLM extracts account details and all transactions",
        },
        {
            "step_order": 3,
            "agent_type": "transform.rules",
            "config": {},
            "reason": "Flag large transactions",
        },
        {
            "step_order": 4,
            "agent_type": "output.formatter",
            "config": {"format": "csv"},
            "reason": "Format for bookkeeping and reconciliation",
        },
    ],
)
```

**Register it — modify `app/templates/registry.py`:**

Add import and registration:

```python
from app.templates.bank_statement import bank_statement_template
```

```python
# In the TEMPLATES dict or list, add:
bank_statement_template
```

Make sure the bank_statement template appears in `get_all_templates()` and `get_template("bank_statement")`.

---

### TASK 8: Improve Refiner System Prompt

**File:** `app/services/pipeline/pipeline_refiner.py`

Find the current `REFINE_SYSTEM_PROMPT` and REPLACE it with:

```python
REFINE_SYSTEM_PROMPT = """You are a pipeline editor. Given the current pipeline definition, sample extraction results, and the user's change request, return a MODIFIED pipeline.

REFINEMENT TYPES - identify which type the user is requesting:

1. FIELD CORRECTION - user says a value is wrong or formatted incorrectly
   -> Add a reusable rule to extraction_prompt, NOT a one-time fix
   -> Make rules GENERAL (e.g. "Dates in DD/MM format -> YYYY-MM-DD") not document-specific
   -> NEVER hardcode a specific correct value into extraction_prompt

2. ADD FIELD - user wants additional data extracted
   -> Add the field to the field_extractor step's config.fields list
   -> Add guidance to extraction_prompt explaining where to find the new field

3. REMOVE FIELD - user doesn't need a field
   -> Remove from config.fields
   -> Clean up any related extraction_prompt instructions

4. ADD RULE - user wants flagging/filtering
   -> Add to rules step config.rules (create a rules step if one doesn't exist)
   -> Available operators: gt, lt, eq, neq, contains

5. FORMAT CHANGE - user wants different output format
   -> Update formatter step config

CRITICAL RULES:
- Only change what the user asked for. Keep everything else EXACTLY the same.
- Do NOT modify fields that the user didn't mention.
- Do NOT remove fields unless explicitly asked.
- Return the FULL pipeline (all steps), not just the changed parts.
- Use ONLY agent_type values from the available_agents catalog.
- extraction_prompt must be the COMPLETE updated prompt (not just additions).
- When writing extraction_prompt rules, make them GENERAL and REUSABLE:
  BAD:  "The date in document abc-123 should be 2024-03-15"
  GOOD: "Dates in this vendor's invoices use DD/MM/YYYY format. Normalize to YYYY-MM-DD."
- Verify your output has all original fields plus additions minus explicit removals.

EXAMPLE:
User: "the amounts still have dollar signs, and also extract payment_status"
Current fields: ["vendor_name", "invoice_number", "total_amount", "invoice_date"]
Sample results: [{"vendor_name": "Acme", "total_amount": "$1,234", "invoice_date": "2024-03-15"}]

Expected changes:
1. Add amount normalization rule to extraction_prompt
2. Add "payment_status" to config.fields
3. Add guidance for payment_status to extraction_prompt
4. Keep all other fields and steps unchanged

Expected extraction_prompt update:
"...existing instructions..."
Amounts: Return plain numbers only. Strip all currency symbols ($, €, ₹, £). No commas. $1,234 -> 1234.
payment_status: Look for 'Paid', 'Unpaid', 'Pending', 'Overdue', 'Due'. Return one of: paid, unpaid, pending, overdue. Null if not stated."

PREVIOUS REFINEMENTS (if provided):
If previous_refinements is present, these are summaries of what was already tried.
Do NOT undo previous fixes unless the user explicitly asks.
Build on previous refinements, don't reset them."""
```

---

### TASK 9: Remove Sample Results Cap + Add Refinement History

**File:** `app/services/pipeline/pipeline_refiner.py`

In the `refine_pipeline()` function, find where `sample_results` is sliced to 3:

```python
"sample_results": sample_results[:3],
```

Replace with:

```python
"sample_results": sample_results[:10],
```

(10 is a reasonable cap to avoid token overflow while covering edge cases.)

---

**File:** `app/services/pipeline/refine_service.py`

In the `refine_and_start()` method, AFTER resolving the parent run's plan and BEFORE building the WorkflowContext, add refinement history collection:

```python
# Collect refinement history from parent chain
refinement_history = []
current = parent
seen_ids: set[str] = set()
while current and current.parent_run_id and len(refinement_history) < 5:
    if current.run_id in seen_ids:
        break
    seen_ids.add(current.run_id)
    if current.refine_summary:
        refinement_history.append(current.refine_summary)
    prev = self._repo.get_run(current.parent_run_id)
    current = prev
refinement_history.reverse()  # oldest first
```

Then include it in the WorkflowContext data:

```python
ctx = WorkflowContext(
    upload_id=parent.upload_id,
    task_description=message,
    data={
        "current_steps": planned_steps,
        "sample_results": sample_rows,
        "extraction_prompt": base_prompt,
        "previous_refinements": refinement_history,  # NEW
    },
)
```

And in the PipelineRefinerHandler.execute() method in `app/agents/handlers/transforms/pipeline_refiner.py`, pass previous_refinements to refine_pipeline():

```python
previous_refinements = ctx.data.get("previous_refinements", [])
```

Then in refine_pipeline() in pipeline_refiner.py, include it in the user prompt payload if non-empty:

```python
if previous_refinements:
    payload["previous_refinements"] = previous_refinements
```

---

### TASK 10: Plan Mode Refinement Chat Endpoint

> Currently every chat message triggers the expensive refiner LLM (70b model + full pipeline context)
> AND a full re-extraction of all documents. Plan Mode adds a cheap clarification layer:
> user chats with a small/fast model to clarify intent, then clicks "Apply" to trigger the real refiner once.

#### 10a. API models — add to `app/models/api/runs.py`

```python
class RefineChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class RefinePlanRequest(BaseModel):
    """Plan mode: clarify user intent before expensive re-run."""
    message: str = Field(min_length=1)
    chat_history: list[RefineChatMessage] = Field(default_factory=list)

class RefinePlanResponse(BaseModel):
    """Response from plan mode clarification."""
    ready: bool  # true = user can click Apply
    message: str  # assistant response to show in chat
    planned_changes: list[str] = Field(default_factory=list)  # bullet list of changes
    accumulated_instruction: str = ""  # full instruction to send to /refine when ready
```

#### 10b. Plan Mode service — `app/services/pipeline/refine_chat.py`

**New file:**

```python
"""Plan Mode refinement chat — cheap clarification before expensive re-run.

Uses the fast 8b model with minimal context (field names + 2 sample rows)
to understand what the user wants. When the user confirms, returns a clear
instruction string to pass to the existing refine_and_start() method.
"""

import json
import logging
from typing import Any

from app.services.llm.groq_client import complete_json

logger = logging.getLogger("refine_chat")

_PLAN_MODEL = "llama-3.1-8b-instant"

_PLAN_SYSTEM_PROMPT = """You are a data extraction assistant in PLAN MODE. You help users clarify what they want to change in their document extraction results BEFORE running the expensive re-extraction.

You do NOT execute changes. You understand, clarify, and summarize.

CONTEXT: The user has extracted data from documents and sees results in a table. They want to fix or improve something.

YOUR JOB:
1. Understand what the user wants to change
2. If ambiguous, ask ONE specific clarifying question (not "could you elaborate?" - ask about the specific field/format/value)
3. Summarize the planned changes clearly
4. When you have enough clarity, set ready=true

RULES:
- Keep responses under 3 sentences
- Reference actual field names and sample values from the context
- Accumulate changes across multiple messages - don't reset
- When ready=true, write accumulated_instruction as a detailed, unambiguous instruction for a pipeline editor. This instruction must be self-contained - the pipeline editor will NOT see the chat history.

OUTPUT FORMAT (JSON):
If still clarifying:
{"ready": false, "message": "your response", "planned_changes": ["change 1", "change 2"], "accumulated_instruction": ""}
If ready to apply:
{"ready": true, "message": "Ready to apply: [summary]. Click Apply to re-run.", "planned_changes": ["change 1"], "accumulated_instruction": "Detailed instruction for the pipeline editor: ..."}"""


async def plan_refinement(
    message: str,
    chat_history: list[dict[str, str]],
    field_names: list[str],
    sample_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Cheap clarification turn. Uses 8b model with minimal context.

    Returns dict with: ready, message, planned_changes, accumulated_instruction
    """
    # Build minimal context - only field names + 2 sample rows
    user_prompt = json.dumps({
        "fields_in_results": field_names,
        "sample_values": sample_rows[:2],
        "chat_history": chat_history,
        "latest_message": message,
    }, indent=2, default=str)

    result = await complete_json(
        _PLAN_SYSTEM_PROMPT,
        user_prompt,
        model=_PLAN_MODEL,
    )

    return {
        "ready": bool(result.get("ready", False)),
        "message": str(result.get("message", "I didn't understand that. Could you describe what field or value needs to change?")),
        "planned_changes": result.get("planned_changes", []),
        "accumulated_instruction": str(result.get("accumulated_instruction", "")),
    }
```

#### 10c. Route — add to `app/api/routes/runs.py`

Add this endpoint alongside the existing `/refine`:

```python
@router.post("/{run_id}/refine/plan", response_model=RefinePlanResponse)
async def refine_plan(
    run_id: str,
    body: RefinePlanRequest,
    repo: RepoDep,
) -> RefinePlanResponse:
    """
    Plan Mode: clarify user intent with a cheap/fast model before re-running.
    Call this for each chat message. When response.ready is true,
    call POST /refine with the accumulated_instruction as the message.
    """
    from app.services.pipeline.refine_chat import plan_refinement

    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # Extract field names and sample rows from run results
    rows = (run.result or {}).get("rows", [])
    field_names = list(rows[0].keys()) if rows else []
    skip = {"document_id", "flags"}
    field_names = [f for f in field_names if f not in skip]

    chat_history = [{"role": m.role, "content": m.content} for m in body.chat_history]

    try:
        result = await plan_refinement(
            message=body.message,
            chat_history=chat_history,
            field_names=field_names,
            sample_rows=rows[:2],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Plan mode failed: {e}")

    return RefinePlanResponse(
        ready=result["ready"],
        message=result["message"],
        planned_changes=result["planned_changes"],
        accumulated_instruction=result["accumulated_instruction"],
    )
```

Add imports at the top of runs.py:

```python
from app.models.api.runs import (
    # ... existing imports ...
    RefinePlanRequest,
    RefinePlanResponse,
)
```

#### 10d. How the two endpoints work together

Frontend flow:

1. User types "fix the dates" → POST `/api/runs/{id}/refine/plan`
   `{ message: "fix the dates", chat_history: [] }`
   → `{ ready: false, message: "I'll normalize dates to YYYY-MM-DD. Currently seeing '03/15/2024'. Confirm?", planned_changes: ["Normalize dates to YYYY-MM-DD"] }`

2. User types "no, keep DD/MM/YYYY" → POST `/api/runs/{id}/refine/plan`
   `{ message: "no, keep DD/MM/YYYY", chat_history: [prev messages] }`
   → `{ ready: true, message: "Ready: normalize all dates to DD/MM/YYYY. Click Apply.", planned_changes: ["Normalize dates to DD/MM/YYYY"], accumulated_instruction: "Update extraction_prompt: all dates must be normalized to DD/MM/YYYY format. Dates currently extracted as YYYY-MM-DD or MM/DD/YYYY should be converted to DD/MM/YYYY." }`

3. User clicks [Apply] → POST `/api/runs/{id}/refine`
   `{ message: "Update extraction_prompt: all dates must be normalized to DD/MM/YYYY format..." }`
   → `{ run: newRun, refine_summary: "..." }` + existing flow, unchanged

**Key:** `/refine/plan` is cheap (8b model, ~50 tokens context). `/refine` is expensive (70b model + full pipeline + re-extraction). Plan Mode means `/refine` gets called once with a clear instruction instead of 3 times with vague ones.

---

### COMPLETE FILE CHANGE SUMMARY

#### New files:

| # | Path | What |
|---|------|------|
| 1 | `app/templates/bank_statement.py` | Bank Statement template |
| 2 | `app/services/pipeline/refine_chat.py` | Plan Mode clarification service |

#### Files to modify:

| # | Path | What changes |
|---|------|--------------|
| 1 | `app/services/extraction/field_extractor.py` | Replace SYSTEM_PROMPT |
| 2 | `app/templates/invoice.py` | Full rewrite |
| 3 | `app/templates/receipt.py` | Full rewrite |
| 4 | `app/templates/contract.py` | Trim 16 → 9 fields |
| 5 | `app/templates/real_estate.py` | Trim 18 → 11 fields |
| 6 | `app/templates/purchase_order.py` | Full rewrite |
| 7 | `app/templates/registry.py` | Register bank_statement_template |
| 8 | `app/services/pipeline/pipeline_refiner.py` | New REFINE_SYSTEM_PROMPT + sample cap 3→10 |
| 9 | `app/services/pipeline/refine_service.py` | Add refinement history chain |
| 10 | `app/agents/handlers/transforms/pipeline_refiner.py` | Pass previous_refinements |
| 11 | `app/models/api/runs.py` | Add RefinePlanRequest, RefinePlanResponse |
| 12 | `app/api/routes/runs.py` | Add POST /{id}/refine/plan endpoint |

---

### BUILD ORDER

1. Step 1: Replace SYSTEM_PROMPT in field_extractor.py
2. Step 2: Replace invoice.py, receipt.py, contract.py, real_estate.py, purchase_order.py
3. Step 3: Create bank_statement.py + register in registry.py
4. Step 4: Replace REFINE_SYSTEM_PROMPT in pipeline_refiner.py + change [:3] to [:10]
5. Step 5: Add refinement history to refine_service.py + pipeline_refiner handler
6. Step 6: Create refine_chat.py (Plan Mode service)
7. Step 7: Add RefinePlanRequest/Response to models/api/runs.py
8. Step 8: Add POST /{id}/refine/plan to api/routes/runs.py
9. Step 9: Test: call /refine/plan with a sample run, verify cheap model responds
10. Step 10: Test: call /refine with accumulated_instruction, verify re-extraction works

---

### CRITICAL RULES

1. **Do NOT change PipelineTemplate model** — only template file contents
2. **Do NOT change field_extractor execution logic** — only SYSTEM_PROMPT string
3. **Do NOT change refine_and_start()** — Plan Mode is a NEW endpoint, not a modification
4. **`/refine/plan` uses `llama-3.1-8b-instant`** (cheap) — `/refine` keeps using the default 70b model
5. **Registry must export bank_statement** — `get_template("bank_statement")` must work
6. **Plan Mode does NOT re-run extraction** — only `/refine` triggers re-extraction

## --- END PROMPT ---

---

*Created: 2026-08-08*
*Covers: Extraction hardening, template rewrites, bank statement, refiner improvements, Plan Mode chat*
*Estimated effort: 6-7 hours*
