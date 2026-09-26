"""9Router planner. Returns data; has no robot execution capability."""
import json
import os
from pathlib import Path
import requests

class PlannerError(RuntimeError):
    pass

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
    def __init__(self, prompt_path, env=None, session=None):
        env = os.environ if env is None else env
        names = ("NINEROUTER_BASE_URL", "NINEROUTER_API_KEY", "NINEROUTER_MODEL")
        missing = [name for name in names if not env.get(name)]
        if missing:
            raise PlannerError("Missing environment variables: " + ", ".join(missing))
        self.base_url, self.key, self.model = (env[name] for name in names)
        self.prompt = Path(prompt_path).read_text(encoding="utf-8")
        self.session = session or requests.Session()

    def plan(self, command, context=None):
        if not isinstance(command, str) or not command.strip() or len(command) > 4000:
            raise PlannerError("Command must contain 1–4000 characters")
        messages = [{"role": "system", "content": self.prompt}]
        if context:
            messages.append({"role": "system", "content": "Trusted context: " + json.dumps(context)})
        messages.append({"role": "user", "content": command})
        try:
            response = self.session.post(self.base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + self.key},
                json={"model": self.model, "stream": False, "messages": messages}, timeout=(5, 60))
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
        content = choice["message"].get("content")
        if not isinstance(content, str) or not content.strip():
            raise PlannerError("9Router response has no content")
        try:
            return strict_json(content)
        except ValueError:
            raise PlannerError("LLM content is malformed JSON (JSON only required)") from None
