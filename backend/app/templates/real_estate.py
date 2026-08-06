"""Real estate / lease extraction template."""

from app.models.domain.template import PipelineTemplate

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
        "property_address",
        "property_type",
        "landlord_name",
        "tenant_name",
        "lease_start_date",
        "lease_end_date",
        "lease_duration_months",
        "monthly_rent",
        "security_deposit",
        "currency",
        "rent_escalation",
        "late_fee",
        "utilities_included",
        "maintenance_responsibility",
        "pet_policy",
        "subletting_allowed",
        "early_termination_fee",
        "renewal_terms",
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
        {
            "field": "monthly_rent",
            "operator": "gt",
            "value": 100000,
            "flag_name": "high_rent",
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
