# AgentFlow — Pipeline Templates

*Pre-built templates with optimized prompts, curated fields, and domain-specific rules.*

---

## Current Extraction Prompt (Generic)

> "You are a document field extraction assistant. Extract values for given field names. Use null for missing. Normalize dates to ISO."

This works, but use-case specific templates with **optimized prompts, curated fields, smart rules, and domain-specific instructions** will significantly improve accuracy.

---

## Template Architecture

```
backend/app/templates/
├── __init__.py
├── registry.py          # Template registry + API
├── invoice.py           # Invoice template
├── resume.py            # Resume/CV template
├── contract.py          # Legal contract template
├── receipt.py           # Receipt/expense template
├── purchase_order.py    # PO template
├── real_estate.py       # Lease/property template
└── medical_bill.py      # Medical/insurance template
```

Each template defines:

- `template_id` – unique key
- `name` – display name
- `description` – what it does (shown in frontend picker)
- `icon` – emoji or icon key for frontend
- `category` – "finance", "legal", "hr", "real_estate", "medical"
- `task_description` – optimized prompt the planner uses
- `fields` – curated field list for the extractor
- `extraction_instructions` – domain-specific instructions injected into extractor prompt
- `rules` – pre-configured rules (flags, validations)
- `output_format` – default output (csv/json)

---

## Template Definitions

### 1. Invoice Parser

```python
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
        "invoice_number", "vendor_name", "vendor_address",
        "invoice_date", "due_date", "subtotal", "tax_amount",
        "total_amount", "currency", "payment_terms",
        "line_items",  # array of {description, quantity, unit_price, amount}
    ],
    extraction_instructions=(
        "For line_items, return an array of objects with keys: "
        "description, quantity, unit_price, amount. "
        "If tax is not explicitly stated, set tax_amount to null. "
        "payment_terms examples: 'Net 30', 'Due on receipt', 'Net 60'. "
        "If multiple currencies appear, use the one on the total line."
    ),
    rules=[
        {"field": "total_amount", "operator": "gt", "value": 50000, "flag_name": "high_value_invoice"},
        {"field": "due_date", "operator": "lt", "value": "today", "flag_name": "overdue"},
    ],
    output_format="csv",
)
```

### 2. Resume Screener

```python
RESUME_TEMPLATE = PipelineTemplate(
    template_id="resume",
    name="Resume Screener",
    description="Extract candidate info, skills, experience, education from resumes/CVs.",
    icon="user",
    category="hr",
    task_description=(
        "Extract structured candidate information from these resumes. "
        "Capture all work experience entries and education details. "
        "List technical skills separately from soft skills."
    ),
    fields=[
        "full_name", "email", "phone", "location",
        "linkedin_url", "years_of_experience",
        "current_title", "current_company",
        "technical_skills", "soft_skills",
        "work_experience",  # array of {company, title, start_date, end_date, description}
        "education",  # array of {institution, degree, field, graduation_year}
        "certifications",
    ],
    extraction_instructions=(
        "For work_experience, return array of objects: "
        "{company, title, start_date, end_date, description}. "
        "end_date should be 'Present' if currently employed. "
        "years_of_experience should be a number calculated from earliest work start date. "
        "technical_skills and soft_skills should be arrays of strings. "
        "certifications should be an array of strings."
    ),
    rules=[
        {"field": "years_of_experience", "operator": "gte", "value": 5, "flag_name": "senior_candidate"},
    ],
    output_format="json",
)
```

### 3. Legal Contract Analyzer ⚖️

```python
CONTRACT_TEMPLATE = PipelineTemplate(
    template_id="contract",
    name="Contract Analyzer",
    description="Extract parties, dates, clauses, obligations from legal contracts.",
    icon="scale",
    category="legal",
    task_description=(
        "Analyze these legal contracts/agreements. "
        "Extract all parties, key dates, financial terms, and important clauses. "
        "Flag any auto-renewal or termination clauses."
    ),
    fields=[
        "contract_type", "effective_date", "expiration_date",
        "party_a_name", "party_a_role",
        "party_b_name", "party_b_role",
        "contract_value", "payment_schedule",
        "auto_renewal", "termination_notice_days",
        "governing_law", "key_obligations",
        "confidentiality_clause", "non_compete_clause",
        "liability_cap",
    ],
    extraction_instructions=(
        "contract_type examples: 'NDA', 'MSA', 'SaaS Agreement', 'Employment Contract', 'Lease'. "
        "auto_renewal should be true/false. "
        "key_obligations should be a short array of the most important obligations. "
        "confidentiality_clause and non_compete_clause should be true/false "
        "(whether they exist in the contract). "
        "liability_cap should be the dollar/currency amount if specified, else null."
    ),
    rules=[
        {"field": "auto_renewal", "operator": "eq", "value": True, "flag_name": "has_auto_renewal"},
    ],
    output_format="json",
)
```

### 4. Receipt / Expense Scanner 🧾

```python
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
        "merchant_name", "merchant_address",
        "receipt_date", "receipt_number",
        "subtotal", "tax_amount", "tip_amount", "total_amount",
        "payment_method", "card_last_four",
        "line_items",  # array of {item, quantity, price}
        "expense_category",  # auto-classify: meals, travel, supplies, etc.
    ],
    extraction_instructions=(
        "For line_items, return array of {item, quantity, price}. "
        "expense_category should be one of: meals, travel, office_supplies, "
        "software, equipment, entertainment, utilities, other. "
        "Infer category from merchant name and items. "
        "If tip is not present, set tip_amount to 0."
    ),
    rules=[
        {"field": "total_amount", "operator": "gt", "value": 5000, "flag_name": "needs_approval"},
    ],
    output_format="csv",
)
```

### 5. Purchase Order Extractor 📦

```python
PO_TEMPLATE = PipelineTemplate(
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
        "po_number", "po_date", "vendor_name", "vendor_contact",
        "ship_to_name", "ship_to_address",
        "line_items",  # array of {sku, description, quantity, unit_price, total}
        "subtotal", "shipping_cost", "tax", "grand_total",
        "delivery_date", "payment_terms",
    ],
    extraction_instructions=(
        "For line_items, return array of {sku, description, quantity, unit_price, total}. "
        "If SKU is not present, use 'N/A'. "
        "shipping_cost should be 0 if free shipping."
    ),
    rules=[
        {"field": "grand_total", "operator": "gt", "value": 100000, "flag_name": "large_order"},
    ],
    output_format="csv",
)
```

### 6. Real Estate / Lease Analyzer 🏠

```python
LEASE_TEMPLATE = PipelineTemplate(
    template_id="lease",
    name="Lease Analyzer",
    description="Extract rent, terms, clauses from property leases and rental agreements.",
    icon="home",
    category="real_estate",
    task_description=(
        "Analyze these property lease/rental agreements. "
        "Extract all financial terms, dates, and important clauses."
    ),
    fields=[
        "property_address", "property_type",
        "landlord_name", "tenant_name",
        "lease_start_date", "lease_end_date", "lease_duration_months",
        "monthly_rent", "security_deposit", "currency",
        "rent_escalation", "late_fee",
        "utilities_included", "maintenance_responsibility",
        "pet_policy", "subletting_allowed",
        "early_termination_fee", "renewal_terms",
    ],
    extraction_instructions=(
        "property_type: 'residential', 'commercial', 'industrial'. "
        "rent_escalation: annual percentage increase if mentioned, else null. "
        "utilities_included: array of strings like ['water', 'electricity'] or empty array. "
        "maintenance_responsibility: 'landlord', 'tenant', or 'shared'. "
        "pet_policy: 'allowed', 'not_allowed', 'allowed_with_deposit'. "
        "subletting_allowed: true/false."
    ),
    rules=[
        {"field": "monthly_rent", "operator": "gt", "value": 100000, "flag_name": "high_rent"},
    ],
    output_format="json",
)
```

### 7. Medical Bill / Insurance Claim 📄

```python
MEDICAL_TEMPLATE = PipelineTemplate(
    template_id="medical_bill",
    name="Medical Bill Parser",
    description="Extract charges, procedure codes, insurance info from medical bills/EOBs.",
    icon="heart-pulse",
    category="medical",
    task_description=(
        "Extract billing data from these medical bills or Explanation of Benefits (EOB). "
        "Capture procedure codes, charges, insurance coverage, and patient responsibility."
    ),
    fields=[
        "patient_name", "patient_id", "date_of_service",
        "provider_name", "provider_npi",
        "insurance_name", "insurance_id",
        "procedures",  # array of {cpt_code, description, charge, allowed, insurance_paid, patient_owes}
        "total_charges", "total_insurance_paid",
        "total_patient_responsibility", "deductible_remaining",
    ],
    extraction_instructions=(
        "For procedures, return array of: "
        "{cpt_code, description, charge, allowed, insurance_paid, patient_owes}. "
        "cpt_code is the 5-digit procedure code (e.g., 99213). "
        "If EOB, 'allowed' is the insurance-approved amount. "
        "patient_owes = charge - insurance_paid (or as stated on the bill)."
    ),
    rules=[
        {"field": "total_patient_responsibility", "operator": "gt", "value": 1000, "flag_name": "high_patient_cost"},
    ],
    output_format="csv",
)
```

---

## Template API

```python
# GET /api/templates - list all templates
[
    {
        "template_id": "invoice",
        "name": "Invoice Parser",
        "description": "Extract vendor, amounts, dates, line items from invoices.",
        "icon": "receipt",
        "category": "finance"
    },
    ...
]

# POST /api/runs/template - run a template on uploaded docs
{
    "upload_id": "abc-123",
    "template_id": "invoice"
}
# -> creates plan from template, starts run, returns RunResponse
```

---

## Frontend Template Picker

Grid of template cards on the landing page:

- Each card: icon + name + description + category badge
- Click → opens upload zone with task pre-filled
- "Or describe your own task" link below for custom pipelines

---

*Used by [FEATURE-ROADMAP.md](./FEATURE-ROADMAP.md) Feature 1.*

**Implementation status:** ✅ Code modules in `backend/app/templates/`, `POST /api/runs/template`, extraction instructions injected via field extractor config. DB table `pipeline_templates` mirrors code via bootstrap + `seed_templates.sql`.
