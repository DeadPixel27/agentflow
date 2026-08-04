"""Apply flag/filter rules to extracted rows."""

from typing import Any

from app.agents.core.base import StepHandler, StepResult
from app.agents.core.context import WorkflowContext
from app.agents.core.registry import register_agent

_OPERATORS = {
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}


class RulesHandler(StepHandler):
    async def execute(
        self,
        ctx: WorkflowContext,
        config: dict[str, Any],
    ) -> StepResult:
        rules = config.get("rules", [])
        rows = ctx.data.get("rows", [])
        if not rows:
            raise ValueError("No rows available — run field_extractor first")

        flagged_count = 0
        for row in rows:
            flags: dict[str, bool] = {}
            for rule in rules:
                field = rule.get("field")
                operator = rule.get("operator", "gt")
                value = rule.get("value")
                flag_name = rule.get("flag_name", f"{field}_{operator}")

                field_value = row.get(field)
                if field_value is None:
                    continue

                try:
                    compare_fn = _OPERATORS.get(operator)
                    if compare_fn and compare_fn(field_value, value):
                        flags[flag_name] = True
                        flagged_count += 1
                except TypeError:
                    continue

            row["flags"] = flags

        ctx.data["rows"] = rows
        return StepResult(
            output={"rules_applied": len(rules), "flags_raised": flagged_count}
        )


register_agent(
    "transform.rules",
    name="Rules Agent",
    description=(
        "Apply conditions to extracted data — flag rows, filter, or validate. "
        "Example: flag when amount exceeds a threshold."
    ),
    example_config={
        "rules": [
            {
                "field": "amount",
                "operator": "gt",
                "value": 50000,
                "flag_name": "high_value",
            }
        ]
    },
    handler=RulesHandler(),
)
