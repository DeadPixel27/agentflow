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
        "end_date should be 'Present' if currently employed. "
        "years_of_experience must be total professional work years only — sum all roles "
        "in work_experience (including internships). Do NOT use education dates. "
        "Calculate from the earliest job start_date to today (or the latest end_date). "
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
