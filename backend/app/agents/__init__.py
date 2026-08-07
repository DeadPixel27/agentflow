"""
Agents — pipeline step plugin system.

  core/       StepHandler interface, WorkflowContext, registry
  handlers/   one file per agent, grouped by stage:
                processors/   processor.ocr, processor.text_extract
                transforms/   transform.field_extractor, transform.rules,
                              transform.pipeline_refiner
                output/       output.formatter
"""
