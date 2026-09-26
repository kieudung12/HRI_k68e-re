import pytest
from ur3_llm_control.student_task import student_mapping, safe_order
from ur3_llm_control.task_validator import PlanValidator, WorldState, ValidationError

@pytest.mark.parametrize("p,order", enumerate([
 ("red_cube","yellow_cube","blue_cube"),("red_cube","blue_cube","yellow_cube"),
 ("yellow_cube","red_cube","blue_cube"),("yellow_cube","blue_cube","red_cube"),
 ("blue_cube","red_cube","yellow_cube"),("blue_cube","yellow_cube","red_cube")]))
def test_all_mappings(p,order):
    xx,actual,mapping=student_mapping(f"202400{p}")
    assert xx == p and actual == p and tuple(mapping.values()) == order
    PlanValidator().validate(safe_order(mapping,WorldState()),required_mapping=mapping)

def test_modulo():
    assert student_mapping("202499")[:2] == (99,3)
    assert student_mapping("000000")[:2] == (0,0)

@pytest.mark.parametrize("value", ["TODO","", "7", "123x", "12.3", "１２"])
def test_bad_id(value):
    with pytest.raises(ValueError): student_mapping(value)

def test_reordering():
    state=WorldState(object_locations={"red_cube":"zone_b","yellow_cube":"source","blue_cube":"zone_a"})
    mapping=student_mapping("00")[2]
    result=PlanValidator().validate(safe_order(mapping,state),state,mapping)
    assert result.final_state.zone_occupancy == mapping

def test_cycle():
    state=WorldState(object_locations={"red_cube":"zone_b","yellow_cube":"zone_a","blue_cube":"zone_c"})
    with pytest.raises(ValidationError,match="cycle"): safe_order(student_mapping("00")[2],state)

def test_wrong_llm_mapping():
    plan=safe_order(student_mapping("00")[2],WorldState())
    with pytest.raises(ValidationError,match="required student mapping"):
        PlanValidator().validate(plan,required_mapping=student_mapping("01")[2])
