"""Pure, fail-closed schema and state validation; no ROS or network dependencies."""
from copy import deepcopy
from dataclasses import dataclass, field

OBJECTS = ("red_cube", "yellow_cube", "blue_cube")
ZONES = ("zone_a", "zone_b", "zone_c")

class ValidationError(ValueError):
    pass

@dataclass
class WorldState:
    held_object: str | None = None
    object_locations: dict = field(default_factory=lambda: {o: "source" for o in OBJECTS})
    revision: int = 0
    faulted: bool = False

    @property
    def zone_occupancy(self):
        return {z: next((o for o, loc in self.object_locations.items() if loc == z), None)
                for z in ZONES}

    @classmethod
    def from_dict(cls, data):
        return cls(data.get("held_object") or None, dict(data["object_locations"]),
                   data.get("revision", 0), data.get("faulted", False))

@dataclass(frozen=True)
class ValidatedPlan:
    steps: tuple
    initial_state: WorldState
    final_state: WorldState

class PlanValidator:
    def validate(self, data, state=None, required_mapping=None):
        state = deepcopy(state or WorldState())
        initial = deepcopy(state)
        if state.faulted:
            raise ValidationError("Robot is faulted; inspect and restart the simulation before retrying")
        if set(state.object_locations) != set(OBJECTS):
            raise ValidationError("Incomplete robot object state")
        if state.held_object is not None and state.held_object not in OBJECTS:
            raise ValidationError("Unknown held object in robot state")
        for obj, loc in state.object_locations.items():
            if loc not in ("source", "held", *ZONES):
                raise ValidationError("Unknown object location in robot state")
            if (loc == "held") != (obj == state.held_object):
                raise ValidationError("Inconsistent held-object state")
        occupied = [loc for loc in state.object_locations.values() if loc in ZONES]
        if len(occupied) != len(set(occupied)):
            raise ValidationError("Inconsistent zone occupancy")
        if type(data) is not dict or set(data) != {"plan"}:
            raise ValidationError("Top level must contain exactly 'plan'")
        steps = data["plan"]
        if type(steps) is not list or not 1 <= len(steps) <= 40:
            raise ValidationError("plan must be a nonempty list of at most 40 steps")
        for i, step in enumerate(steps, 1):
            def reject(message):
                raise ValidationError(f"Step {i}: {message}")
            if type(step) is not dict:
                reject("step must be an object")
            skill = step.get("skill")
            if not isinstance(skill, str) or skill not in ("pick", "place", "home"):
                reject("unknown skill")
            fields = {"skill"} | ({"object"} if skill != "home" else set()) | ({"zone"} if skill == "place" else set())
            if set(step) != fields:
                reject("missing or unexpected arguments")
            obj = step.get("object")
            if skill != "home" and obj not in OBJECTS:
                reject("unknown object")
            if skill == "pick":
                if state.held_object:
                    reject("already holding an object")
                state.held_object = obj
                state.object_locations[obj] = "held"
            elif skill == "place":
                zone = step["zone"]
                if zone not in ZONES:
                    reject("unknown zone")
                if state.held_object != obj:
                    reject("place requires the same object to be held")
                if state.zone_occupancy[zone]:
                    reject(f"{zone} is occupied")
                state.object_locations[obj] = zone
                state.held_object = None
            elif state.held_object:
                reject("home while holding an object is not allowed")
        if state.held_object:
            raise ValidationError("Plan leaves an object held")
        if required_mapping is not None:
            if set(required_mapping) != set(ZONES) or set(required_mapping.values()) != set(OBJECTS):
                raise ValidationError("Invalid trusted student mapping")
            if any(state.object_locations[obj] != zone for zone, obj in required_mapping.items()):
                raise ValidationError("Plan does not achieve the required student mapping")
        return ValidatedPlan(tuple(deepcopy(steps)), initial, state)
