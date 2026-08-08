"""Lease Analyzer — extraction from rental and lease agreements."""

from app.models.domain.template import PipelineTemplate

LEASE_TEMPLATE = PipelineTemplate(
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
        "processor.text_extract",
        "transform.field_extractor",
        "transform.rules",
        "output.formatter",
    ],
    sort_order=6,
)
