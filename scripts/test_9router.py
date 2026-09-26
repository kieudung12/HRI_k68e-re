import os
import json
import requests

BASE_URL = os.environ["NINEROUTER_BASE_URL"]
API_KEY = os.environ["NINEROUTER_API_KEY"]
MODEL = os.environ["NINEROUTER_MODEL"]

prompt = """
You are a UR3 task planner.

Return ONLY valid JSON.
Do not use Markdown.
Do not explain.

Allowed skills:
- pick(object)
- place(object, zone)
- home()

Valid objects:
- red_cube
- yellow_cube
- blue_cube

Valid zones:
- zone_a
- zone_b
- zone_c

Each plan step must be a JSON object.

Example:
{
  "plan": [
    {
      "skill": "pick",
      "object": "red_cube"
    },
    {
      "skill": "place",
      "object": "red_cube",
      "zone": "zone_b"
    },
    {
      "skill": "home"
    }
  ]
}

Never generate joint commands or trajectories.
"""

user_command = input("USER COMMAND: ")

response = requests.post(
    f"{BASE_URL}/chat/completions",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": MODEL,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": user_command,
            },
        ],
    },
    timeout=60,
)

response.raise_for_status()

data = response.json()

content = data["choices"][0]["message"]["content"]

plan = json.loads(content)

print("\nLLM PLAN:")
print(json.dumps(plan, indent=2))

