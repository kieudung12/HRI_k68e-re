import pytest

from ur3_llm_control.output_format import format_execution, format_plan, format_step


PLAN = [
    {"skill": "pick", "object": "red_cube"},
    {"skill": "place", "object": "red_cube", "zone": "zone_b"},
    {"skill": "home"},
]


def test_format_step_uses_assignment_skill_syntax():
    assert [format_step(step) for step in PLAN] == [
        "pick(red_cube)", "place(red_cube, zone_b)", "home()"]


def test_plan_and_execution_share_human_readable_step_format():
    results = [{"step": step, "status": "SUCCESS"} for step in PLAN]
    assert format_plan(PLAN) == (
        "1. pick(red_cube)\n"
        "2. place(red_cube, zone_b)\n"
        "3. home()")
    assert format_execution(results) == (
        "pick(red_cube) ........ SUCCESS\n"
        "place(red_cube, zone_b) ........ SUCCESS\n"
        "home() ........ SUCCESS")


def test_unknown_skill_cannot_be_formatted_as_a_valid_plan():
    with pytest.raises(ValueError, match="unknown skill"):
        format_step({"skill": "teleport"})
