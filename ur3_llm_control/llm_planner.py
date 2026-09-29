"""9Router planner and semantic intent classifier; no robot execution capability."""
import json
import os
from pathlib import Path
import requests

class PlannerError(RuntimeError):
    pass


# Gemini behind 9Router sometimes treats JSON mode as a formatting hint and
# answers with prose.  A function call gives it a typed output channel while
# keeping the final plan subject to the independent Python validator.
PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "emit_plan",
        "description": "Return the UR3 skill plan as exact skill objects.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "array",
                    "minItems": 0,
                    "maxItems": 40,
                    "items": {
                        "type": "object",
                        "properties": {
                            "skill": {"type": "string", "enum": ["pick", "place", "home"]},
                            "object": {"type": "string", "enum": ["red_cube", "yellow_cube", "blue_cube"]},
                            "zone": {"type": "string", "enum": ["zone_a", "zone_b", "zone_c"]},
                        },
                        "required": ["skill"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["plan"],
            "additionalProperties": False,
        },
    },
}

def strict_json(content):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("non-finite JSON number")
    return json.loads(content, object_pairs_hook=pairs, parse_constant=constant)

class LLMPlanner:
    INTENT_PROMPT = """Classify only whether the user wants the complete assignment mapping selected from their student ID (for example, an arrangement according to their student ID or student assignment). Understand the intent semantically in any language; do not match one exact sentence. A request for one named object in one named zone is not a student-specific arrangement. Do not create a robot plan. Return exactly JSON: {\"student_specific\":true} or {\"student_specific\":false}."""

    def __init__(self, prompt_path, env=None, session=None):
        env = os.environ if env is None else env
        names = ("NINEROUTER_BASE_URL", "NINEROUTER_API_KEY", "NINEROUTER_MODEL")
        missing = [name for name in names if not env.get(name)]
        if missing:
            raise PlannerError("Missing environment variables: " + ", ".join(missing))
        self.base_url, self.key, self.model = (env[name] for name in names)
        self.prompt = Path(prompt_path).read_text(encoding="utf-8")
        self.session = session or requests.Session()

    def _request_json(self, messages, tool=None, max_tokens=256):
        # Keep responses compact: planner output is a tiny structured skill list.
        request = {"model": self.model, "stream": False, "messages": messages,
                   "max_tokens": max_tokens}
        if tool is None:
            request["response_format"] = {"type": "json_object"}
        else:
            request["tools"] = [tool]
            request["tool_choice"] = {"type": "function", "function": {"name": tool["function"]["name"]}}
        try:
            response = self.session.post(self.base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + self.key},
                json=request, timeout=(5, 60))
            response.raise_for_status()
        except requests.Timeout:
            raise PlannerError("9Router timeout") from None
        except requests.ConnectionError:
            raise PlannerError("Cannot connect to 9Router") from None
        except requests.HTTPError as exc:
            raise PlannerError(f"9Router HTTP error {exc.response.status_code}") from None
        except requests.RequestException:
            raise PlannerError("9Router request failed; check endpoint configuration") from None
        try:
            data = response.json()
        except ValueError:
            raise PlannerError("9Router response is not JSON") from None
        if not isinstance(data, dict) or not isinstance(data.get("choices"), list) or not data["choices"]:
            raise PlannerError("9Router response has no choices")
        choice = data["choices"][0]
        if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
            raise PlannerError("9Router response has no message")
        message = choice["message"]
        tool_calls = message.get("tool_calls")
        if tool is not None and isinstance(tool_calls, list) and tool_calls:
            call = tool_calls[0]
            function = call.get("function") if isinstance(call, dict) else None
            content = function.get("arguments") if isinstance(function, dict) else None
        else:
            content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise PlannerError("9Router response has no content")
        try:
            return strict_json(content)
        except ValueError:
            raise PlannerError("LLM content is malformed JSON (JSON only required)") from None

    def classify_student_task(self, command):
        if not isinstance(command, str) or not command.strip() or len(command) > 4000:
            raise PlannerError("Command must contain 1–4000 characters")
        result = self._request_json([
            {"role": "system", "content": self.INTENT_PROMPT},
            {"role": "user", "content": command},
        ], max_tokens=32)
        if type(result) is not dict or set(result) != {"student_specific"} or type(result["student_specific"]) is not bool:
            raise PlannerError("Intent response must contain exactly a boolean student_specific")
        return result["student_specific"]

    def plan(self, command, context=None):
        if not isinstance(command, str) or not command.strip() or len(command) > 4000:
            raise PlannerError("Command must contain 1–4000 characters")
        messages = [{"role": "system", "content": self.prompt}]
        if context:
            messages.append({"role": "system", "content": "Trusted context: " + json.dumps(context)})
        messages.append({"role": "user", "content": command})
        # Preserve the LLM's structured plan exactly. Schema and task semantics
        # belong to PlanValidator; never infer or append robot skills here.
        return self._request_json(messages, PLAN_TOOL)

    def revise_plan(self, command, context, rejected_plan, validation_error):
        """Ask the model once for a complete replacement after validator rejection."""
        messages = [{"role": "system", "content": self.prompt}]
        if context:
            messages.append({"role": "system", "content": "Trusted context: " + json.dumps(context)})
        messages.extend([
            {"role": "user", "content": command},
            {"role": "assistant", "content": json.dumps(rejected_plan, ensure_ascii=False)},
            {"role": "user", "content": (
                "A deterministic plan validator rejected your previous plan with this error: "
                + validation_error + ". Return a complete replacement plan for the original "
                "request and trusted state. Follow every planning rule, including exactly one "
                "final home() step. Do not explain the error, do not return the rejected plan "
                "unchanged, and do not assume any skill has executed.")},
        ])
        return self._request_json(messages, PLAN_TOOL)
