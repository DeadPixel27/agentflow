"""Resume / CV extraction template."""

from app.models.domain.template import PipelineTemplate

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
        "full_name",
        "email",
        "phone",
        "location",
        "linkedin_url",
        "years_of_experience",
        "current_title",
        "current_company",
        "technical_skills",
        "soft_skills",
        "work_experience",
        "education",
        "certifications",
    ],
    extraction_instructions=(
        "For work_experience, return array of objects: "
        "{company, title, start_date, end_date, description}. "
        "Use ISO dates when possible (YYYY-MM-DD); end_date should be 'Present' if currently employed. "
        "years_of_experience: sum the duration of EVERY role in work_experience "
        "(including internships), as fractional years rounded to 2 decimals. "
        "For each role: duration_years = (end_date - start_date) / 365.25; "
        "if end_date is Present/current, use today's date. "
        "Add all role durations together — do NOT use calendar span from earliest start "
        "to latest end (that over-counts gaps), and do NOT use education dates. "
        "Example: July 2024–Present (~2.08y) + May 2023–Aug 2023 (~0.25y) ≈ 2.33. "
        "technical_skills and soft_skills should be arrays of strings. "
        "certifications should be an array of strings."
    ),
    rules=[
        {
            "field": "years_of_experience",
            "operator": "gte",
            "value": 5,
            "flag_name": "senior_candidate",
        },
    ],
    output_format="json",
    suggested_steps=[
        "processor.text_extract",
        "transform.field_extractor",
        "transform.rules",
        "output.formatter",
    ],
    sort_order=2,
)
