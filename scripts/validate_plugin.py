#!/usr/bin/env python3
"""Validate standalone Claude Plugin metadata without workflow coupling."""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")


def validate_plugin_version(plugin: dict) -> str:
    version = plugin.get('version')
    assert isinstance(version, str) and VERSION_PATTERN.fullmatch(version), 'plugin version must be a stable semantic version'
    return version


def validate_plugin(root: Path = ROOT) -> None:
    plugin = json.loads((root / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
    validate_plugin_version(plugin)
    skills = plugin['skills']
    assert isinstance(skills, list) and skills and len(skills) == len(set(skills)), 'invalid/duplicate plugin skills'
    for item in skills:
        assert item.startswith('./') and '..' not in Path(item).parts, f'bad Skill path {item}'
        assert (root / item / 'SKILL.md').is_file(), f'missing Skill {item}'
    assert './backlog' in skills and './backlog-workflow' not in skills, 'legacy workflow still registered'
    forbidden = {'tests', 'test', 'evals', 'experiments', 'research', 'media', 'assets', 'node_modules', '__pycache__'}
    for item in skills:
        folder = root / item
        for path in folder.rglob('*'):
            rel = path.relative_to(folder)
            if '__pycache__' in rel.parts or path.suffix in {'.pyc', '.pyo'}:
                continue
            assert not forbidden.intersection(rel.parts), f'non-runtime Skill payload: {item}/{rel}'
            if path.is_file():
                assert path.suffix.lower() not in {'.mp4', '.gif', '.png', '.zip', '.mov'}, f'media in Skill: {item}/{rel}'
    assert sorted(p.name for p in (root / 'betfirst').iterdir()) == ['SKILL.md'], 'BetFirst must stay minimal'


if __name__ == '__main__':
    validate_plugin()
    print('Claude plugin metadata and Skill paths valid')
