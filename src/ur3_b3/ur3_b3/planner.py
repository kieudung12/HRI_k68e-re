"""A small JSON LLM planner and preflight validator for tabletop skills."""

import json
import os
import getpass
from pathlib import Path

import requests

from .perception import HUE_RANGES, ZONES


SYSTEM_PROMPT = """You plan a UR3e tabletop sorting task. Read the user's command and the
camera environment state. Return ONLY a JSON object with one key, "plan", whose
value is a list of skill objects. Allowed forms are exactly:
{"skill":"clear_zone","zone":"zone_a|zone_b|zone_c"}
{"skill":"pick","object":"red_cube|yellow_cube|blue_cube|green_cube|purple_cube"}
{"skill":"place","object":"red_cube|yellow_cube|blue_cube|green_cube|purple_cube","target":"zone_a|zone_b|zone_c"}
{"skill":"home"}
If a target zone holds another cube, clear it first. clear_zone moves its
occupant to a free table position chosen by robot code. End with home.
Never output coordinates, joint values, trajectories, commentary, or markdown.
Do not infer object locations: use the camera state supplied below."""


def _key_file():
    """Return the per-user key file without putting secrets in the workspace."""
    configured = os.environ.get('NINEROUTER_KEY_FILE')
    if configured:
        return Path(configured).expanduser()
    return Path.home() / '.config' / 'ur3_b3' / '9router_api_key'


def _load_saved_key():
    try:
        value = _key_file().read_text(encoding='utf-8').strip()
    except (OSError, UnicodeError):
        return None
    return value or None


def _save_key(key):
    path = _key_file()
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text(key.strip() + '\n', encoding='utf-8')
        path.chmod(0o600)
    except OSError as exc:
        # A read-only home directory should not prevent an otherwise valid run.
        print(f'Warning: could not save 9Router key to {path}: {exc}', flush=True)


def request_plan(command, state):
    """Call the same OpenAI-compatible 9Router endpoint used in Bài 2."""
    base_url = os.environ.get('NINEROUTER_BASE_URL', 'http://localhost:20128/v1')
    model = os.environ.get('NINEROUTER_MODEL', 'ag/gemini-3.8-flash-medium')
    key = os.environ.get('NINEROUTER_API_KEY') or _load_saved_key()
    if not key:
        if not os.isatty(0):
            raise RuntimeError(
                'NINEROUTER_API_KEY is unset; run interactively or export the key')
        key = getpass.getpass('9Router API key (saved locally after success): ')
    if not key:
        raise RuntimeError('An empty 9Router API key was entered')
    if not command.strip() or len(command) > 1000:
        raise ValueError('Command must contain 1–1000 characters')
    url = base_url.rstrip('/') + '/chat/completions'
    body = {
        'model': model, 'stream': False,
        'temperature': 0, 'max_tokens': 300,
        'response_format': {'type': 'json_object'},
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': json.dumps({
                'command': command, 'environment_state': state
            })},
        ],
    }
    try:
        response = requests.post(
            url, headers={'Authorization': 'Bearer ' + key},
            json=body, timeout=(5, 60))
        if response.status_code == 401:
            if not os.isatty(0):
                raise RuntimeError(
                    '9Router returned 401; NINEROUTER_API_KEY is missing or invalid')
            key = getpass.getpass('9Router API key (retry, saved after success): ')
            if not key:
                raise RuntimeError('An empty 9Router API key was entered')
            response = requests.post(
                url, headers={'Authorization': 'Bearer ' + key},
                json=body, timeout=(5, 60))
        response.raise_for_status()
        if not os.environ.get('NINEROUTER_API_KEY'):
            _save_key(key)
        content = response.json()['choices'][0]['message']['content']
        return json.loads(content)
    except RuntimeError:
        raise
    except (requests.RequestException, KeyError, IndexError, TypeError,
            ValueError) as exc:
        if isinstance(exc, requests.HTTPError) and exc.response is not None \
                and exc.response.status_code == 401:
            raise RuntimeError(
                '9Router rejected the API key (401 Unauthorized). Enter a valid key '
                'from 9Router or export NINEROUTER_API_KEY again') from exc
        raise RuntimeError(f'LLM request or JSON response failed: {exc}') from exc


def validate_plan(document, state):
    """Check the complete skill order before moving the robot."""
    if not isinstance(document, dict) or set(document) != {'plan'}:
        raise ValueError('Plan must have exactly one key: plan')
    steps = document['plan']
    if not isinstance(steps, list) or not 1 <= len(steps) <= 12:
        raise ValueError('Plan must contain 1–12 steps')
    if set(state.get('objects', {})) != set(HUE_RANGES) or not state.get('complete'):
        raise ValueError('Camera state is incomplete')
    zones = dict(state['zones'])
    locations = {name: item['location'] for name, item in state['objects'].items()}
    held = None
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or not isinstance(step.get('skill'), str):
            raise ValueError(f'Invalid step {index + 1}')
        skill = step['skill']
        required = {
            'clear_zone': {'skill', 'zone'}, 'pick': {'skill', 'object'},
            'place': {'skill', 'object', 'target'}, 'home': {'skill'},
        }.get(skill)
        if required is None or set(step) != required:
            raise ValueError(f'Unknown skill or parameters at step {index + 1}')
        if skill == 'clear_zone':
            zone = step['zone']
            if zone not in ZONES or held is not None:
                raise ValueError('Cannot clear this zone now')
            occupant = zones[zone]
            if occupant is not None:
                locations[occupant] = 'table'
                zones[zone] = None
        elif skill == 'pick':
            name = step['object']
            if name not in HUE_RANGES or held is not None or name not in locations:
                raise ValueError('Cannot pick this object now')
            if locations[name] in ZONES:
                zones[locations[name]] = None
            locations[name] = 'held'
            held = name
        elif skill == 'place':
            name, zone = step['object'], step['target']
            if name not in HUE_RANGES or zone not in ZONES or held != name:
                raise ValueError('Cannot place this object now')
            if zones[zone] is not None:
                raise ValueError(f'{zone} is occupied; clear it first')
            locations[name] = zone
            zones[zone] = name
            held = None
        elif held is not None or index != len(steps) - 1:
            raise ValueError('home must be last, with no cube held')
    if steps[-1]['skill'] != 'home':
        raise ValueError('Plan must end with home')
    return steps


def execute_plan(robot, steps):
    for step in steps:
        skill = step['skill']
        robot.get_logger().info('skill: ' + json.dumps(step, sort_keys=True))
        if skill == 'clear_zone':
            robot.clear_zone(step['zone'])
        elif skill == 'pick':
            robot.pick(step['object'])
        elif skill == 'place':
            robot.place(step['object'], step['target'])
        else:
            robot.home()
