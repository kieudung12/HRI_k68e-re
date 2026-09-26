import pytest
from ur3_llm_control.task_validator import PlanValidator, ValidationError, WorldState

GOOD = {"plan":[{"skill":"pick","object":"red_cube"},
                 {"skill":"place","object":"red_cube","zone":"zone_b"},{"skill":"home"}]}
def test_valid_basic():
    result=PlanValidator().validate(GOOD)
    assert result.final_state.held_object is None
    assert result.final_state.zone_occupancy["zone_b"] == "red_cube"
    assert result.initial_state.object_locations["red_cube"] == "source"

@pytest.mark.parametrize("data", [
 {}, {"plan":{}}, {"plan":[]}, {"plan":[3]}, {"plan":[{"skill":"hack"}]},
 {"plan":[{"skill":"pick","object":"bad"}]}, {"plan":[{"skill":"pick"}]},
 {"plan":[{"skill":"place","zone":"zone_a"}]}, {"plan":[{"skill":"place","object":"red_cube"}]},
 {"plan":[{"skill":"place","object":"red_cube","zone":"zone_a"}]},
 {"plan":[{"skill":"pick","object":"red_cube"},{"skill":"pick","object":"blue_cube"}]},
 {"plan":[{"skill":"pick","object":"red_cube"},{"skill":"place","object":"blue_cube","zone":"zone_a"}]},
 {"plan":[{"skill":"pick","object":"red_cube"},{"skill":"place","object":"red_cube","zone":"bad"}]},
 {"plan":[{"skill":"home","joints":[0]*6}]}, {"plan":[{"skill":"home","object":"red_cube"}]},
 {"plan":[{"skill":["pick"]}]}, {"plan":[{"skill":"pick","object":{}}]},
 {"plan":[{"skill":"pick","object":"red_cube"}]},
 {"plan":[{"skill":"home"}],"code":"bad"},
 {"plan":[{"skill":"pick","object":"red_cube"},{"skill":"home"}]},
])
def test_invalid(data):
    with pytest.raises(ValidationError): PlanValidator().validate(data)

def test_occupied_zone():
    state=WorldState(object_locations={"red_cube":"source","yellow_cube":"zone_b","blue_cube":"source"})
    with pytest.raises(ValidationError,match="occupied"): PlanValidator().validate(GOOD,state)

def test_free_old_zone_on_pick():
    state=WorldState(object_locations={"red_cube":"zone_a","yellow_cube":"source","blue_cube":"source"})
    result=PlanValidator().validate(GOOD,state)
    assert result.final_state.zone_occupancy["zone_a"] is None

def test_faulted():
    with pytest.raises(ValidationError,match="faulted"): PlanValidator().validate(GOOD,WorldState(faulted=True))


@pytest.mark.parametrize("state", [
    WorldState(held_object="red_cube"),
    WorldState(object_locations={"red_cube":"held","yellow_cube":"source","blue_cube":"source"}),
    WorldState(object_locations={"red_cube":"unknown","yellow_cube":"source","blue_cube":"source"}),
    WorldState(object_locations={"red_cube":"zone_a","yellow_cube":"zone_a","blue_cube":"source"}),
])
def test_inconsistent_state(state):
    with pytest.raises(ValidationError):PlanValidator().validate(GOOD,state)
