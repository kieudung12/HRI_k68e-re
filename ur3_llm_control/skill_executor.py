"""Validate the complete plan against fresh robot state before the first skill."""
from copy import deepcopy
from .task_validator import PlanValidator, WorldState

class SkillExecutor:
    def __init__(self, backend):
        self.backend = backend

    def execute(self, raw_plan, required_mapping=None, progress=None):
        initial = self.backend.state()
        validated = PlanValidator().validate(raw_plan, initial, required_mapping)
        state = initial
        results = []
        for step in validated.steps:
            response = self.backend.skill(step, state.revision)
            results.append({"step": step, "status": response["status"], "message": response.get("message", "")})
            observed = WorldState.from_dict(response["state"])
            if response["status"] == "SUCCESS":
                expected = deepcopy(state)
                if step["skill"] == "pick":
                    expected.held_object = step["object"]
                    expected.object_locations[step["object"]] = "held"
                elif step["skill"] == "place":
                    expected.held_object = None
                    expected.object_locations[step["object"]] = step["zone"]
                if (observed.faulted or observed.held_object != expected.held_object
                        or observed.object_locations != expected.object_locations
                        or observed.revision != state.revision + 1):
                    response["status"] = "STATE_MISMATCH"
                    results[-1]["status"] = "STATE_MISMATCH"
                    results[-1]["message"] = "Robot reported success with an unexpected state; inspect before retrying"
            state = observed
            if progress:
                progress(step, response["status"])
            if response["status"] != "SUCCESS":
                return {"status": "TASK_FAILED", "results": results, "state": state.__dict__}
        return {"status": "TASK_SUCCESS", "results": results, "state": state.__dict__}
