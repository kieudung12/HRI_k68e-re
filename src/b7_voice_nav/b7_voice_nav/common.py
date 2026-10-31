import math
import re
import unicodedata

import yaml


def load_regions(path):
    with open(path, encoding='utf-8') as f:
        regions = yaml.safe_load(f)['regions']
    if not regions or len({r['id'] for r in regions}) != len(regions):
        raise ValueError('Danh sách vùng rỗng hoặc ID bị trùng')
    return regions


def normalize(text):
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return ' '.join(re.findall(r'[a-z0-9]+', text))


def parse_command(text, regions):
    """Return ordered regions; reject unrecognized destination clauses entirely."""
    s = normalize(text)
    s = re.sub(r'^(?:(?:hay|vui long|robot)\s+)+', '', s)
    # Strip polite endings before splitting: "tôi" and "tới" both normalize
    # to "toi", so "cho tôi" must not be read as another route connector.
    # Bare "ạ" also becomes "a": strip it only after a polite phrase,
    # otherwise we would remove the actual destination A.
    s = re.sub(r'(?:\s+(?:nhe|nha|voi)(?:\s+a)?)+$', '', s)
    s = re.sub(r'\s+(?:cho|giup)\s+(?:toi|minh|em)(?:\s+a)?$', '', s)
    # Remove the request verb, then the optional first route preposition.
    match = re.match(r'^(?:di chuyen|di|den|toi|sang)\b\s*', s)
    if not match:
        raise ValueError('Không nhận ra lệnh điều hướng')
    route_text = re.sub(r'^(?:tu|qua|den|toi|sang)\b\s*', '', s[match.end():])
    # Keep every destination, including A in "đi khu A rồi sang khu B".
    names = re.split(r'\b(?:(?:roi|sau do)\s+)?(?:qua|den|toi|sang)\b', route_text)
    names = [name.strip() for name in names]
    if any(not name for name in names):
        raise ValueError('Thiếu tên khu vực')
    result = []
    for name in names:
        candidates = []
        for region in regions:
            aliases = {normalize(alias) for alias in
                       [region['id'], region['name'], *region.get('aliases', [])]}
            # "khu A" is the short form of a configured "khu vực A" alias.
            aliases |= {'khu ' + alias[len('khu vuc '):]
                        for alias in aliases if alias.startswith('khu vuc ')}
            if name in aliases:
                candidates.append(region)
        if len(candidates) != 1:
            raise ValueError(f'Khu vực không tồn tại hoặc không rõ: {name}')
        result.append(candidates[0])
    return result


def world_to_pixel(x, y, metadata, height):
    ox, oy, yaw = metadata['origin']
    dx, dy = x - ox, y - oy
    mx = (math.cos(yaw) * dx + math.sin(yaw) * dy) / metadata['resolution']
    my = (-math.sin(yaw) * dx + math.cos(yaw) * dy) / metadata['resolution']
    return int(math.floor(mx + 1e-9)), height - 1 - int(math.floor(my + 1e-9))
