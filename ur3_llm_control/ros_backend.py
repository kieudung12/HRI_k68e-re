import json
import threading
from .task_validator import WorldState
from ur3_llm_control.srv import GetState, ExecuteSkill

class ROSBackend:
    def __init__(self, node, callback_group):
        self.node=node
        self.get=node.create_client(GetState,"/robot_skills/state",callback_group=callback_group)
        self.run=node.create_client(ExecuteSkill,"/robot_skills/execute",callback_group=callback_group)

    @staticmethod
    def call(client, request, timeout):
        if not client.wait_for_service(timeout_sec=10):
            raise RuntimeError("Robot service unavailable; launch simulation first")
        done=threading.Event()
        future=client.call_async(request)
        future.add_done_callback(lambda _:done.set())
        if not done.wait(timeout):
            # A service has no cancellation. Do not retry or send another skill.
            raise RuntimeError("Robot response timed out; execution state unknown. Stop and inspect simulation; do not retry")
        return future.result()

    def state(self):
        return WorldState.from_dict(json.loads(self.call(self.get,GetState.Request(),15).state_json))

    def skill(self, step, revision):
        req=ExecuteSkill.Request(skill=step["skill"],object=step.get("object",""),zone=step.get("zone",""),
                                 check_revision=True,expected_revision=revision)
        response=self.call(self.run,req,240)
        return {"status":response.status,"message":response.message,"state":json.loads(response.state_json)}
