#!/usr/bin/env python3
"""Package B7 source without generated builds or local validation material."""
import argparse
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--without-model', action='store_true', help='Download the model with setup.sh on the receiving machine')
p.add_argument('--output', default=str(root / 'b7_submission.zip'))
a = p.parse_args()
output = Path(a.output).resolve()
excluded = {'build', 'install', 'log', '.venv', '.runtime', '__pycache__', '.git', '.cache',
            'tests', 'evidence'}
if a.without_model:
    excluded.add('models')
with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if (path.is_file() and path.resolve() != output and
                not excluded.intersection(relative.parts) and
                relative != Path('tools/transcribe_audio.py')):
            if path.suffix not in {'.pyc', '.zip'}:
                archive.write(path, Path('b7') / relative)
print(output)
