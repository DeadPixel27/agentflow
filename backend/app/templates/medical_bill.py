"""Medical bill / EOB extraction template."""

from app.models.domain.template import PipelineTemplate

MEDICAL_BILL_TEMPLATE = PipelineTemplate(
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
        "patient_name",
        "patient_id",
        "date_of_service",
        "provider_name",
        "provider_npi",
        "insurance_name",
        "insurance_id",
        "procedures",
        "total_charges",
        "total_insurance_paid",
        "total_patient_responsibility",
        "deductible_remaining",
    ],
    extraction_instructions=(
        "For procedures, return array of: "
        "{cpt_code, description, charge, allowed, insurance_paid, patient_owes}. "
        "cpt_code is the 5-digit procedure code (e.g., 99213). "
        "If EOB, 'allowed' is the insurance-approved amount. "
        "patient_owes = charge - insurance_paid (or as stated on the bill)."
    ),
    rules=[
        {
            "field": "total_patient_responsibility",
            "operator": "gt",
            "value": 1000,
            "flag_name": "high_patient_cost",
        },
    ],
    output_format="csv",
    suggested_steps=[
        "processor.ocr",
        "transform.field_extractor",
        "transform.rules",
        "output.formatter",
    ],
    sort_order=7,
)
