"""Legal contract extraction template."""

from app.models.domain.template import PipelineTemplate

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
        "contract_type",
        "effective_date",
        "expiration_date",
        "party_a_name",
        "party_a_role",
        "party_b_name",
        "party_b_role",
        "contract_value",
        "payment_schedule",
        "auto_renewal",
        "termination_notice_days",
        "governing_law",
        "key_obligations",
        "confidentiality_clause",
        "non_compete_clause",
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
        {
            "field": "auto_renewal",
            "operator": "eq",
            "value": True,
            "flag_name": "has_auto_renewal",
        },
    ],
    output_format="json",
    suggested_steps=[
        "processor.text_extract",
        "transform.field_extractor",
        "transform.rules",
        "output.formatter",
    ],
    sort_order=3,
)
