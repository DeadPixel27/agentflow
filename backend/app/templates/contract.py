"""Contract Analyzer — key term extraction from legal agreements."""

from app.models.domain.template import PipelineTemplate

CONTRACT_TEMPLATE = PipelineTemplate(
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
        "processor.text_extract",
        "transform.field_extractor",
        "transform.rules",
        "output.formatter",
    ],
    sort_order=3,
)
