from pathlib import Path
import yaml
import pytest
from ur3_llm_control.student_task import student_mapping, safe_order, build_trusted_context
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


def test_real_student_identity_mapping():
    config_path=Path(__file__).resolve().parents[1]/"config/student_config.yaml"
    config=yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["student_name"] == "Kieu Minh Dung"
    assert config["student_id"] == "23020729"
    xx,p,mapping=student_mapping(config["student_id"])
    assert xx == 29
    assert p == 5
    assert mapping == {"zone_a":"blue_cube","zone_b":"yellow_cube","zone_c":"red_cube"}
    PlanValidator().validate(safe_order(mapping,WorldState()),required_mapping=mapping)


def test_llm_trusted_context_has_mapping_but_no_precomputed_order():
    state=WorldState()
    mapping={"zone_a":"blue_cube","zone_b":"yellow_cube","zone_c":"red_cube"}
    context=build_trusted_context(state,(29,5,mapping))
    assert context == {
        "held_object":None,
        "object_locations":{"red_cube":"source","yellow_cube":"source","blue_cube":"source"},
        "zone_occupancy":{"zone_a":None,"zone_b":None,"zone_c":None},
        "student":{"XX":29,"P":5,"required_mapping":mapping},
    }
    assert "feasible_skill_order" not in context
    assert "plan" not in context
