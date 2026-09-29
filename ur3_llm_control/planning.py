"""One bounded LLM replan on deterministic validator rejection."""
from .task_validator import PlanValidator, ValidationError


def plan_and_validate(planner, command, context, state, required_mapping=None,
                      validator=None):
    """Return a validated LLM plan, retrying generation at most once.

    The rejected plan is never modified or executed. Every replacement goes
    through the same validator, and the original trusted state is reused.
    """
    validator = validator or PlanValidator()
    plan = planner.plan(command, context)
    try:
        return plan, validator.validate(plan, state, required_mapping), False
    except ValidationError as first_error:
        plan = planner.revise_plan(command, context, plan, str(first_error))
    try:
        return plan, validator.validate(plan, state, required_mapping), True
    except ValidationError as second_error:
        raise ValidationError(
            "LLM plan remained invalid after one replan: " + str(second_error)
        ) from None
