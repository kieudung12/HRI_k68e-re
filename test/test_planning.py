import pytest

from ur3_llm_control.planning import plan_and_validate
from ur3_llm_control.task_validator import ValidationError, WorldState


VALID = {"plan": [
    {"skill": "pick", "object": "red_cube"},
    {"skill": "place", "object": "red_cube", "zone": "zone_b"},
    {"skill": "home"},
]}
MISSING_HOME = {"plan": VALID["plan"][:-1]}


class FakePlanner:
    def __init__(self, first, replacement=None):
        self.first = first
        self.replacement = replacement
        self.calls = 0
        self.revision = None

    def plan(self, command, context):
        self.calls += 1
        return self.first

    def revise_plan(self, command, context, rejected_plan, validation_error):
        self.calls += 1
        self.revision = (command, context, rejected_plan, validation_error)
        return self.replacement


def test_valid_first_plan_does_not_call_retry():
    planner = FakePlanner(VALID)
    plan, validated, retried = plan_and_validate(
        planner, "move red", {}, WorldState())
    assert plan == VALID
    assert validated.final_state.object_locations["red_cube"] == "zone_b"
    assert retried is False
    assert planner.calls == 1


def test_missing_home_gets_one_full_llm_replan_then_validation():
    planner = FakePlanner(MISSING_HOME, VALID)
    plan, validated, retried = plan_and_validate(
        planner, "move red", {"state": "trusted"}, WorldState())
    assert plan == VALID
    assert validated.final_state.object_locations["red_cube"] == "zone_b"
    assert retried is True
    assert planner.calls == 2
    assert planner.revision[2] == MISSING_HOME
    assert "end with exactly home()" in planner.revision[3]
    # The rejected candidate itself is not mutated or silently repaired.
    assert MISSING_HOME["plan"] == VALID["plan"][:-1]


def test_invalid_replacement_is_rejected_after_exactly_one_retry():
    planner = FakePlanner(MISSING_HOME, MISSING_HOME)
    with pytest.raises(ValidationError, match="after one replan.*home"):
        plan_and_validate(planner, "move red", {}, WorldState())
    assert planner.calls == 2
