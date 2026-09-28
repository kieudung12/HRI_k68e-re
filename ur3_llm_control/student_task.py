"""Student-ID arithmetic belongs here, never in the LLM."""
import re
from itertools import permutations
from .task_validator import OBJECTS, ZONES, ValidationError

MAPPINGS = tuple(dict(zip(ZONES, order)) for order in permutations(OBJECTS))

def build_trusted_context(state, student=None):
    """Expose authoritative state and optional mapping, never a skill sequence."""
    context = {
        "held_object": state.held_object,
        "object_locations": dict(state.object_locations),
        "zone_occupancy": dict(state.zone_occupancy),
    }
    if student is not None:
        xx, permutation, mapping = student
        context["student"] = {
            "XX": xx,
            "P": permutation,
            "required_mapping": dict(mapping),
        }
    return context

def student_mapping(student_id):
    value = str(student_id).strip()
    if not re.fullmatch(r"[0-9]{2,}", value):
        raise ValueError("Fill student_id with at least two decimal digits in student_config.yaml")
    xx = int(value[-2:])
    return xx, xx % 6, dict(MAPPINGS[xx % 6])

def safe_order(mapping, state):
    """Trusted feasible ordering; reject cycles without a free zone before any motion."""
    locations = dict(state.object_locations)
    result = []
    pending = {obj: zone for zone, obj in mapping.items() if locations[obj] != zone}
    while pending:
        ready = [(obj, zone) for obj, zone in pending.items() if zone not in locations.values()]
        if not ready:
            raise ValidationError("Occupied-zone cycle: reset the scene; no staging skill is exposed")
        for obj, zone in ready:
            result.extend([{"skill": "pick", "object": obj},
                           {"skill": "place", "object": obj, "zone": zone}])
            locations[obj] = zone
            del pending[obj]
    return {"plan": result + [{"skill": "home"}]}
