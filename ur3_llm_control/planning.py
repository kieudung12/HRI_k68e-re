"""One bounded LLM replan on deterministic validator rejection."""
from .task_validator import PlanValidator, ValidationError

MAX_REPLANS = 2


def plan_and_validate(planner, command, context, state, required_mapping=None,
                      validator=None):
    """Return a validated LLM plan, with at most two complete replans.

    The rejected plan is never modified or executed. Every replacement goes
    through the same validator, and the original trusted state is reused.
    """
    validator = validator or PlanValidator()
    plan = planner.plan(command, context)
    for replan_count in range(MAX_REPLANS + 1):
        if (type(plan) is dict and type(plan.get("plan")) is list
                and not plan["plan"]):
            raise ValidationError(
                "LLM returned an empty plan; no safe executable plan was proposed"
            )
        try:
            return plan, validator.validate(plan, state, required_mapping), replan_count > 0
        except ValidationError as error:
            if replan_count == MAX_REPLANS:
                raise ValidationError(
                    f"LLM plan remained invalid after {MAX_REPLANS} replans: {error}"
                ) from None
            plan = planner.revise_plan(command, context, plan, str(error))
