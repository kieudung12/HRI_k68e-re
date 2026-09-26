from copy import deepcopy
import pytest
from ur3_llm_control.skill_executor import SkillExecutor
from ur3_llm_control.task_validator import WorldState, ValidationError
from test_validator import GOOD

class Backend:
    def __init__(self, fail=False): self.calls=[]; self.fail=fail; self.current=WorldState()
    def state(self): return deepcopy(self.current)
    def skill(self,step,revision):
        self.calls.append(deepcopy(step))
        if not self.fail:
            if step["skill"] == "pick":
                self.current.held_object=step["object"]
                self.current.object_locations[step["object"]]="held"
            elif step["skill"] == "place":
                self.current.held_object=None
                self.current.object_locations[step["object"]]=step["zone"]
        self.current.revision=revision+1
        return {"status":"PLANNING_FAILED" if self.fail else "SUCCESS", "state":deepcopy(self.current.__dict__)}

def test_all_or_nothing_validation():
    b=Backend()
    bad=deepcopy(GOOD); bad["plan"].append({"skill":"hack"})
    with pytest.raises(ValidationError): SkillExecutor(b).execute(bad)
    assert b.calls == []

def test_stop_first_failure():
    b=Backend(True)
    assert SkillExecutor(b).execute(GOOD)["status"] == "TASK_FAILED"
    assert len(b.calls) == 1

def test_success_order():
    b=Backend()
    assert SkillExecutor(b).execute(GOOD)["status"] == "TASK_SUCCESS"
    assert b.calls == GOOD["plan"]


def test_wrong_success_state_stops():
    class Inconsistent(Backend):
        def skill(self,step,revision):
            self.calls.append(step)
            return {"status":"SUCCESS","state":WorldState(revision=revision+1).__dict__}
    b=Inconsistent()
    result=SkillExecutor(b).execute(GOOD)
    assert result["status"] == "TASK_FAILED"
    assert result["results"][0]["status"] == "STATE_MISMATCH"
    assert len(b.calls) == 1
