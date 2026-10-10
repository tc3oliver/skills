#!/usr/bin/env python3
"""Backlog v2: dependency-free, Git-friendly persistent tasks for coding agents."""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import json
import os
import stat
from pathlib import Path
import re
import secrets
import sys
import tempfile

ID_RE = re.compile(r"BL-[0-9A-F]{16}\Z")
STATES = ("inbox", "todo", "doing", "blocked", "done", "cancelled")
ACTIVE = set(STATES[:4])
TERMINAL = set(STATES[4:])
PRIORITIES = ("P0", "P1", "P2", "P3")
FIELDS = ("id", "title", "status", "priority", "depends", "created_at", "updated_at")
SECTIONS = ("Goal", "Acceptance Criteria", "References", "Handoff", "Evidence", "History", "Blocker")
MAX_TEXT = 32768


class BacklogError(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def check_text(value: str, name: str, *, multiline: bool = True) -> str:
    if len(value) > MAX_TEXT or '\x00' in value or '\r' in value:
        raise BacklogError(f"invalid {name}")
    if not multiline and ('\n' in value or not value.strip()):
        raise BacklogError(f"{name} must be a non-empty single line")
    if any(line.startswith('## ') for line in value.splitlines()):
        raise BacklogError(f"{name} cannot contain Markdown section headings")
    return value.strip()


def parse_id(value: str) -> str:
    if not ID_RE.fullmatch(value):
        raise BacklogError(f"invalid task ID: {value}")
    return value


def parse_depends(value: str | None) -> list[str]:
    if not value or value.strip() == '-':
        return []
    items = [parse_id(v.strip()) for v in value.split(',')]
    if len(items) != len(set(items)):
        raise BacklogError('duplicate dependencies')
    return items


def read_task(path: Path) -> dict:
    if path.is_symlink():
        raise BacklogError(f"symlink task refused: {path}")
    if path.stat().st_size > 131072:
        raise BacklogError(f'task file exceeds 128 KiB: {path}')
    raw = path.read_text(encoding='utf-8')
    match = re.match(r'\A---\n(.*?)\n---\n(?:\n|\Z)', raw, re.S)
    if not match:
        raise BacklogError(f"invalid frontmatter: {path}")
    meta = {}
    for line in match.group(1).splitlines():
        if ': ' not in line:
            raise BacklogError(f"invalid metadata line: {path}")
        key, val = line.split(': ', 1)
        if key not in FIELDS or key in meta:
            raise BacklogError(f"unknown/duplicate key {key}: {path}")
        meta[key] = val
    if set(meta) != set(FIELDS):
        raise BacklogError(f"missing metadata fields: {path}")
    if not ID_RE.fullmatch(meta['id']) or meta['id'] != path.stem:
        raise BacklogError(f"ID / filename mismatch: {path}")
    try:
        meta['title'] = json.loads(meta['title'])
    except (ValueError, TypeError) as exc:
        raise BacklogError(f"invalid title encoding: {path}") from exc
    if not isinstance(meta['title'], str):
        raise BacklogError(f"invalid title type: {path}")
    check_text(meta['title'], 'title', multiline=False)
    if meta['status'] not in STATES or meta['priority'] not in PRIORITIES:
        raise BacklogError(f"invalid status/priority: {path}")
    meta['depends'] = parse_depends(meta['depends'])
    for field in ('created_at', 'updated_at'):
        try:
            if datetime.fromisoformat(meta[field]).tzinfo is None:
                raise ValueError('missing timezone')
        except ValueError as exc:
            raise BacklogError(f"invalid {field}: {path}") from exc
    remainder = raw[match.end():]
    sections = {}
    current = None
    for line in remainder.splitlines():
        if line.startswith('## '):
            current = line[3:]
            if current not in SECTIONS or current in sections:
                raise BacklogError(f"unknown/duplicate section: {current} in {path}")
            sections[current] = []
        elif current is None:
            if line.strip():
                raise BacklogError(f"content before first section: {path}")
        else:
            sections[current].append(line)
    # v2.0 initially shipped without History: accept that format when reading,
    # but always include History on the next write. No migration side effect.
    required = set(SECTIONS) - {'History'}
    if not required.issubset(sections):
        raise BacklogError(f"missing sections: {path}")
    sections.setdefault('History', [])
    meta['sections'] = {k: '\n'.join(v).strip() for k, v in sections.items()}
    criteria = meta['sections']['Acceptance Criteria'].splitlines()
    for item in criteria:
        if item and not re.fullmatch(r'- \[[ x]\] .+', item):
            raise BacklogError(f"invalid acceptance criterion: {path}")
    meta['path'] = path
    return meta


def serialize(task: dict) -> str:
    lines = ['---']
    for key in FIELDS:
        value = task[key]
        if key == 'title':
            value = json.dumps(value, ensure_ascii=False)
        elif key == 'depends':
            value = ','.join(value) if value else '-'
        lines.append(f'{key}: {value}')
    lines.extend(['---', ''])
    for section in SECTIONS:
        lines.extend([f'## {section}', task['sections'].get(section, ''), ''])
    return '\n'.join(lines).rstrip() + '\n'


def base_dir(root: Path, create: bool = False) -> Path:
    folder = root / '.backlog'
    if folder.is_symlink():
        raise BacklogError('symlink .backlog directory refused')
    if not folder.is_dir():
        if not create:
            raise BacklogError('Backlog not initialized; run init')
        folder.mkdir(parents=True, exist_ok=False)
    for name in ('tasks', 'archive'):
        p = folder / name
        if p.is_symlink():
            raise BacklogError(f'symlink {name} directory refused')
        if create:
            p.mkdir(exist_ok=True)
        if not p.is_dir():
            raise BacklogError(f'missing {name} directory')
    return folder


@contextlib.contextmanager
def locked(folder: Path):
    """Kernel-released interprocess lock for one working tree; no stale PID files."""
    path = folder / '.lock'
    if path.is_symlink():
        raise BacklogError('symlink .lock refused')
    # O_NOFOLLOW prevents a race with replacement by a symlink where supported.
    flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise BacklogError('.lock must be a regular file')
    try:
        if os.name == 'nt':
            import msvcrt
            if os.fstat(fd).st_size == 0:
                os.write(fd, b'0')
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def atomic_write(path: Path, data: str) -> None:
    if path.is_symlink():
        raise BacklogError(f'symlink task refused: {path}')
    # The parent is validated by base_dir/paths/archive_path before mutation.
    # Do not allow an existing task to be replaced through a leaf symlink.
    descriptor, temp = tempfile.mkstemp(prefix='.tmp-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def archive_path(folder: Path, status: str, month: str, ident: str, *, create: bool = False) -> Path:
    """Derive the terminal state from path, without a redundant status index."""
    if status not in TERMINAL or not re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])', month):
        raise BacklogError('invalid archive location')
    current = folder / 'archive'
    for part in (status, month):
        current = current / part
        if current.is_symlink():
            raise BacklogError(f'symlink archive directory refused: {current}')
        if create:
            current.mkdir(exist_ok=True)
        if not current.is_dir():
            raise BacklogError(f'missing archive directory: {current}')
    return current / (parse_id(ident) + '.md')


def paths(folder: Path):
    """Yield active files and archive paths, rejecting symlinked ancestors/leaves."""
    active = folder / 'tasks'
    if active.is_symlink():
        raise BacklogError('symlink tasks directory refused')
    for path in active.iterdir():
        if path.name.startswith('BL-') and path.name.endswith('.md'):
            if path.is_symlink():
                raise BacklogError(f'symlink task refused: {path}')
            yield path, None
    archive = folder / 'archive'
    if archive.is_symlink():
        raise BacklogError('symlink archive directory refused')
    for status_dir in archive.iterdir():
        if status_dir.name in ('.DS_Store',):
            continue
        if status_dir.is_symlink():
            raise BacklogError(f'symlink archive directory refused: {status_dir}')
        if not status_dir.is_dir() or status_dir.name not in TERMINAL:
            raise BacklogError(f'unknown archive layout: {status_dir} (expected done/ or cancelled/)')
        for month_dir in status_dir.iterdir():
            if month_dir.name in ('.DS_Store',):
                continue
            if month_dir.is_symlink():
                raise BacklogError(f'symlink archive directory refused: {month_dir}')
            if not month_dir.is_dir() or not re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])', month_dir.name):
                raise BacklogError(f'invalid archive month: {month_dir}')
            for path in month_dir.iterdir():
                if path.name.startswith('BL-') and path.name.endswith('.md'):
                    if path.is_symlink():
                        raise BacklogError(f'symlink task refused: {path}')
                    yield path, status_dir.name



CACHE_VERSION = 1
CACHE_FILE = '.archive-cache.json'
MONTH_RE = re.compile(r'\d{4}-(?:0[1-9]|1[0-2])\Z')


def archive_signature(folder: Path) -> list:
    """Bounded scan of month *directories*, not every archived task body.

    File additions/deletions rename entries and change the month directory's
    stat timestamps on supported filesystems. Doctor always ignores this cache.
    """
    archive = folder / 'archive'
    if archive.is_symlink():
        raise BacklogError('symlink archive directory refused')
    def fingerprint(p: Path) -> list:
        info = p.stat()
        return [info.st_mtime_ns, info.st_ctime_ns, info.st_size]
    result = [['archive', *fingerprint(archive)]]
    for status_dir in archive.iterdir():
        if status_dir.name == '.DS_Store':
            continue
        if status_dir.is_symlink():
            raise BacklogError(f'symlink archive directory refused: {status_dir}')
        if status_dir.name not in TERMINAL or not status_dir.is_dir():
            raise BacklogError(f'unknown archive layout: {status_dir}')
        result.append([status_dir.name, *fingerprint(status_dir)])
        for month_dir in status_dir.iterdir():
            if month_dir.name == '.DS_Store':
                continue
            if month_dir.is_symlink():
                raise BacklogError(f'symlink archive directory refused: {month_dir}')
            if not MONTH_RE.fullmatch(month_dir.name) or not month_dir.is_dir():
                raise BacklogError(f'invalid archive month: {month_dir}')
            result.append([status_dir.name, month_dir.name, *fingerprint(month_dir)])
    return sorted(result, key=str)


def archive_records(folder: Path) -> list[tuple[Path, str]]:
    """Regenerable ignored cache of archive filenames, never the source of truth."""
    signature = archive_signature(folder)
    cache = folder / CACHE_FILE
    if cache.is_symlink():
        raise BacklogError('symlink archive cache refused')
    records = None
    if cache.is_file():
        try:
            obj = json.loads(cache.read_text(encoding='utf-8'))
            if obj.get('version') == CACHE_VERSION and obj.get('signature') == signature:
                raw = obj.get('records')
                if isinstance(raw, list) and all(
                        isinstance(x, list) and len(x) == 3 and
                        x[0] in TERMINAL and isinstance(x[1], str) and MONTH_RE.fullmatch(x[1]) and
                        isinstance(x[2], str) and ID_RE.fullmatch(x[2]) for x in raw):
                    if len(raw) == len({tuple(x) for x in raw}):
                        records = raw
        except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
            pass
    if records is None:
        records = []
        for p, status in paths(folder):
            if status is None:
                continue
            records.append([status, p.parent.name, parse_id(p.stem)])
        # Recheck to avoid persisting a snapshot from a concurrent filesystem change.
        after = archive_signature(folder)
        if after == signature:
            try:
                atomic_write(cache, json.dumps({'version': CACHE_VERSION, 'signature': signature,
                                                 'records': records}, separators=(',', ':')) + '\n')
            except OSError:
                pass  # No cache permission: queries remain correct but slower.
    return [(folder / 'archive' / status / month / (ident + '.md'), status)
            for status, month, ident in records]

def load_all(folder: Path, *, full_archive: bool = False, tolerate_moves: bool = False) -> dict[str, dict]:
    """Normal queries parse active tasks only; the archive is filename metadata."""
    result = {}
    if full_archive or tolerate_moves:
        files = paths(folder)
    else:
        active = ((p, None) for p in (folder / 'tasks').iterdir()
                  if p.name.startswith('BL-') and p.name.endswith('.md'))
        files = list(active) + archive_records(folder)
    for path, archive_status in files:
        # Active files must always be checked. Archived cache entries are
        # validated by directory signatures; selected leaves are checked
        # again by read_task, and doctor does a full non-cached traversal.
        if archive_status is None and path.is_symlink():
            raise BacklogError(f'symlink task refused: {path}')
        ident = parse_id(path.stem)
        if ident in result:
            raise BacklogError(f'duplicate task ID: {ident}')
        if archive_status is None or full_archive or tolerate_moves:
            task = read_task(path)
            if not tolerate_moves and archive_status is None and task['status'] in TERMINAL:
                raise BacklogError(f'terminal task inside tasks: {ident}; run doctor --repair')
            if not tolerate_moves and archive_status is not None and task['status'] != archive_status:
                raise BacklogError(f'archive status mismatch: {ident}; run doctor --repair')
        else:
            task = {'id': ident, 'status': archive_status, 'path': path, 'depends': [],
                    'title': '', 'priority': 'P3', 'created_at': '', 'updated_at': ''}
        result[ident] = task
    return result


def move_task(folder: Path, task: dict, target: Path) -> None:
    """Move original bytes FIRST, then atomically replace at destination.

    A failed rename leaves the old source untouched. If the later write fails,
    doctor --repair can restore the pre-operation file based on its old status.
    """
    source = task['path']
    if target.is_symlink() or target.exists():
        raise BacklogError('task destination exists; refusing overwrite')
    # Never persist a new status at the old location before moving it. A
    # failed rename leaves the old bytes unchanged. A failed post-move save
    # leaves recoverable old bytes in the new location for doctor --repair.
    os.rename(source, target)
    task['path'] = target
    save(task)


def recovery_moves(folder: Path, tasks: dict[str, dict]):
    """Generate only unambiguous moves where on-disk state contradicts location."""
    fixes = []
    for t in tasks.values():
        p = t['path']
        in_archive = p.parent.parent.parent == folder / 'archive'
        if in_archive and t['status'] in ACTIVE:
            target = folder / 'tasks' / p.name
            fixes.append((p, target, t['id']))
        elif not in_archive and t['status'] in TERMINAL:
            month = t['updated_at'][:7]
            target = folder / 'archive' / t['status'] / month / p.name
            fixes.append((p, target, t['id']))
        elif in_archive and t['status'] != p.parent.parent.name:
            raise BacklogError(f'archive status mismatch cannot be repaired automatically: {t["id"]}')
    return fixes


def doctor(folder: Path, root: Path, repair: bool) -> dict:
    # Scan all bodies: only doctor performs historical full validation.
    if repair:
        with locked(folder):
            tasks = load_all(folder, full_archive=True, tolerate_moves=True)
            fixes = recovery_moves(folder, tasks)
            for source, dest, ident in fixes:
                if dest.is_symlink() or dest.exists():
                    raise BacklogError(f'repair destination exists for {ident}')
            for source, dest, ident in fixes:
                if dest.parent.is_symlink():
                    raise BacklogError(f'symlink repair destination refused: {dest}')
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.rename(source, dest)
            repaired = [ident for _, _, ident in fixes]
            tasks = load_all(folder, full_archive=True)
            verify_dependencies(tasks)
    else:
        tasks = load_all(folder, full_archive=True, tolerate_moves=True)
        fixes = recovery_moves(folder, tasks)
        if fixes:
            raise BacklogError('interrupted task move: ' + ', '.join(t[2] for t in fixes) + '; run doctor --repair')
        verify_dependencies(tasks)
        repaired = []
    return {'ok': True, 'tasks': len(tasks), 'active': sum(t['status'] in ACTIVE for t in tasks.values()),
            'legacy_present': (root / '.agent-workflow').exists(), 'repaired': repaired}


def verify_dependencies(tasks: dict[str, dict]) -> None:
    """Iterative DFS: a long task chain must not overflow Python's call stack."""
    state: dict[str, int] = {}
    for origin in tasks:
        if state.get(origin) == 2:
            continue
        stack = [(origin, 0)]
        while stack:
            ident, index = stack[-1]
            state[ident] = 1
            deps = tasks[ident]['depends']
            if index == len(deps):
                state[ident] = 2
                stack.pop()
                continue
            dep = deps[index]
            stack[-1] = (ident, index + 1)
            if dep not in tasks:
                raise BacklogError(f'missing dependency {dep} (from {ident})')
            if dep == ident:
                raise BacklogError(f'self dependency: {ident}')
            if state.get(dep) == 1:
                raise BacklogError(f'dependency cycle at {dep}')
            if state.get(dep) != 2:
                stack.append((dep, 0))


def dependency_done(task: dict) -> bool:
    if task['status'] != 'done':
        return False
    # Treat ignored cache metadata as a hint, not authority: a finished
    # dependency must have a real, non-symlinked archived task path.
    path = task['path']
    return path.parent.parent.name == 'done' and path.is_file() and not path.is_symlink()


def ready(task: dict, tasks: dict) -> bool:
    return task['status'] == 'todo' and all(dependency_done(tasks[d]) for d in task['depends'])


def compact(t: dict) -> dict:
    return {k: t[k] for k in ('id', 'title', 'status', 'priority', 'depends', 'updated_at')}


def ensure_executable(task: dict) -> None:
    s = task['sections']
    if not s['Goal'].strip():
        raise BacklogError('a ready task requires a Goal')
    if not s['Acceptance Criteria'].strip():
        raise BacklogError('a ready task requires Acceptance Criteria')
    if any(not v.startswith('- [') for v in s['Acceptance Criteria'].splitlines()):
        raise BacklogError('invalid Acceptance Criteria')


def save(task: dict) -> None:
    task['updated_at'] = now()
    atomic_write(task['path'], serialize(task))


def initialize(root: Path) -> dict:
    folder = base_dir(root, create=True)
    gitignore = folder / '.gitignore'
    if not gitignore.exists():
        atomic_write(gitignore, '.lock\n.tmp-*\n.archive-cache.json\n')
    return {'root': str(folder.relative_to(root)), 'initialized': True}


def new_task(folder: Path, args) -> dict:
    tasks = load_all(folder)
    verify_dependencies(tasks)
    title = check_text(args.title, 'title', multiline=False)
    goal = check_text(args.goal or '', 'goal')
    ac = [check_text(item, 'criterion', multiline=False) for item in (args.ac or [])]
    deps = parse_depends(args.depends)
    for d in deps:
        if d not in tasks:
            raise BacklogError(f'unknown dependency {d}')
    if goal and ac:
        status = 'todo'
    else:
        status = 'inbox'
    if args.priority not in PRIORITIES:
        raise BacklogError('invalid priority')
    for _ in range(5):
        ident = 'BL-' + secrets.token_hex(8).upper()
        if ident not in tasks:
            break
    else:
        raise BacklogError('ID allocation failed')
    t = dict(id=ident, title=title, status=status, priority=args.priority,
             depends=deps, created_at=now(), updated_at=now(),
             sections={name: '' for name in SECTIONS}, path=folder/'tasks'/f'{ident}.md')
    t['sections']['Goal'] = goal
    t['sections']['Acceptance Criteria'] = '\n'.join('- [ ] '+v for v in ac)
    t['sections']['References'] = '\n'.join('- '+check_text(v, 'reference', multiline=False) for v in (args.ref or []))
    atomic_write(t['path'], serialize(t))
    return compact(t)


def select_task(tasks, ident):
    ident = parse_id(ident)
    if ident not in tasks:
        raise BacklogError(f'task not found: {ident}')
    return tasks[ident]


def move_to_archive(task: dict, folder: Path) -> None:
    dest = archive_path(folder, task['status'], now()[:7], task['id'], create=True)
    move_task(folder, task, dest)


def mutate(folder, args):
    tasks = load_all(folder)
    verify_dependencies(tasks)
    task = select_task(tasks, args.id)
    if task['status'] in TERMINAL:
        task = read_task(task['path'])
        expected_status = task['path'].parent.parent.name
        if task['status'] != expected_status:
            raise BacklogError(f'archive status mismatch: {task["id"]}; run doctor')
    action = args.command
    state = task['status']
    s = task['sections']
    if action == 'edit':
        if state in TERMINAL:
            raise BacklogError('reopen before editing terminal task')
        if args.title is not None:
            task['title'] = check_text(args.title, 'title', multiline=False)
        if args.goal is not None:
            s['Goal'] = check_text(args.goal, 'goal')
        if args.priority is not None:
            task['priority'] = args.priority
        if args.depends is not None:
            task['depends'] = parse_depends(args.depends)
        old_checked = sum(line.startswith('- [x] ') for line in s['Acceptance Criteria'].splitlines())
        if args.ac:
            if old_checked and not args.confirm_ac_reset:
                raise BacklogError(f'{old_checked} checked acceptance criteria would be reset; pass --confirm-ac-reset')
            s['Acceptance Criteria'] = '\n'.join('- [ ] '+check_text(v, 'criterion', multiline=False) for v in args.ac)
        if args.ref:
            s['References'] = '\n'.join('- '+check_text(v, 'reference', multiline=False) for v in args.ref)
        tasks[task['id']] = task
        verify_dependencies(tasks)
        if state == 'inbox' and s['Goal'] and s['Acceptance Criteria']:
            task['status'] = 'todo'
        if task['status'] != 'inbox':
            ensure_executable(task)
    elif action == 'start':
        if not ready(task, tasks):
            raise BacklogError('task is not ready (status or dependencies)')
        ensure_executable(task)
        task['status'] = 'doing'
    elif action == 'block':
        if state not in ('todo', 'doing'):
            raise BacklogError('only todo/doing can be blocked')
        reason = check_text(args.reason, 'reason')
        if not reason:
            raise BacklogError('block reason required')
        s['Blocker'] = reason
        task['status'] = 'blocked'
    elif action == 'unblock':
        if state != 'blocked':
            raise BacklogError('task is not blocked')
        s['Blocker'] = ''
        task['status'] = 'todo'
        ensure_executable(task)
    elif action == 'note':
        if state in TERMINAL:
            raise BacklogError('cannot update closed task')
        s['Handoff'] = check_text(args.text, 'handoff')
    elif action == 'check':
        if state != 'doing':
            raise BacklogError('start task before checking criteria')
        lines = s['Acceptance Criteria'].splitlines()
        idx = args.index
        if idx < 1 or idx > len(lines):
            raise BacklogError('criterion index out of range')
        lines[idx-1] = re.sub(r'^- \[[ x]\]', '- [x]' if not args.undo else '- [ ]', lines[idx-1])
        s['Acceptance Criteria'] = '\n'.join(lines)
    elif action == 'close':
        if state != 'doing':
            raise BacklogError('only doing tasks may be closed')
        ensure_executable(task)
        if any(not v.startswith('- [x] ') for v in s['Acceptance Criteria'].splitlines()):
            raise BacklogError('all acceptance criteria must be checked')
        if any(not dependency_done(tasks[d]) for d in task['depends']):
            raise BacklogError('dependencies are not complete')
        evidence = check_text(args.evidence, 'evidence')
        if not evidence:
            raise BacklogError('validation evidence required')
        s['Evidence'] = (s['Evidence'] + '\n' if s['Evidence'] else '') + '- '+now()+': '+evidence
        task['status'] = 'done'
        move_to_archive(task, folder)
        return compact(task)
    elif action == 'cancel':
        if state in TERMINAL:
            raise BacklogError('task already closed')
        reason = check_text(args.reason, 'reason')
        if not reason:
            raise BacklogError('cancellation reason required')
        s['Evidence'] = (s['Evidence'] + '\n' if s['Evidence'] else '') + '- Cancelled: '+reason
        task['status'] = 'cancelled'
        move_to_archive(task, folder)
        return compact(task)
    elif action == 'reopen':
        if state not in TERMINAL:
            raise BacklogError('task is not closed')
        dest = folder / 'tasks' / task['path'].name
        if dest.is_symlink() or dest.exists():
            raise BacklogError('active task destination exists')
        task['status'] = 'todo' if s['Goal'] and s['Acceptance Criteria'] else 'inbox'
        if task['status'] == 'todo':
            s['Acceptance Criteria'] = '\n'.join(re.sub(r'^- \[x\]', '- [ ]', v) for v in s['Acceptance Criteria'].splitlines())
        if s['Evidence']:
            s['History'] = (s['History'] + '\n' if s['History'] else '') + (
                'Reopened ' + now() + ' (previous validation is historical):\n' + s['Evidence'])
            s['Evidence'] = ''
        move_task(folder, task, dest)
        return compact(task)
    else:
        raise BacklogError(f'unsupported action {action}')
    save(task)
    result = compact(task)
    if action == 'edit' and args.ac:
        result['acceptance_reset'] = old_checked
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Git-friendly persistent backlog; JSON output')
    parser.add_argument('--root', type=Path, default=Path('.'), help='project root')
    parser.add_argument('--json', action='store_true', help='output is always JSON')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    add = sub.add_parser('add')
    add.add_argument('title')
    add.add_argument('--goal', default='')
    add.add_argument('--ac', action='append')
    add.add_argument('--ref', action='append')
    add.add_argument('--priority', choices=PRIORITIES, default='P2')
    add.add_argument('--depends', default='-')
    listing = sub.add_parser('list')
    listing.add_argument('--status', choices=STATES)
    listing.add_argument('--limit', type=int, default=10)
    nxt = sub.add_parser('next')
    nxt.add_argument('--limit', type=int, default=5)
    sub.add_parser('status')
    show = sub.add_parser('show')
    show.add_argument('id')
    edit = sub.add_parser('edit')
    edit.add_argument('id')
    edit.add_argument('--title')
    edit.add_argument('--goal')
    edit.add_argument('--priority', choices=PRIORITIES)
    edit.add_argument('--ac', action='append')
    edit.add_argument('--ref', action='append')
    edit.add_argument('--depends')
    edit.add_argument('--confirm-ac-reset', action='store_true', help='acknowledge replacing checked AC')
    for action in ('start', 'unblock', 'reopen'):
        command = sub.add_parser(action)
        command.add_argument('id')
    for action in ('block', 'cancel'):
        command = sub.add_parser(action)
        command.add_argument('id')
        command.add_argument('--reason', required=True)
    note = sub.add_parser('note')
    note.add_argument('id')
    note.add_argument('--text', required=True)
    check = sub.add_parser('check')
    check.add_argument('id')
    check.add_argument('index', type=int)
    check.add_argument('--undo', action='store_true')
    close = sub.add_parser('close')
    close.add_argument('id')
    close.add_argument('--evidence', required=True)
    doc = sub.add_parser('doctor')
    doc.add_argument('--repair', action='store_true', help='repair only unambiguous interrupted moves')
    # Accept --json both before and after the subcommand (output is always JSON).
    for command in sub.choices.values():
        command.add_argument('--json', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if args.command == 'init':
            result = initialize(root)
        else:
            folder = base_dir(root)
            if args.command in ('add', 'edit', 'start', 'block', 'unblock', 'note', 'check', 'close', 'cancel', 'reopen'):
                with locked(folder):
                    result = new_task(folder, args) if args.command == 'add' else mutate(folder, args)
            elif args.command == 'doctor':
                result = doctor(folder, root, args.repair)
            else:
                tasks = load_all(folder)
                verify_dependencies(tasks)
                if args.command == 'show':
                    t = select_task(tasks, args.id)
                    if t['status'] in TERMINAL:
                        t = read_task(t['path'])
                        if t['status'] != t['path'].parent.parent.name:
                            raise BacklogError(f'archive status mismatch: {t["id"]}; run doctor')
                    result = {'task': compact(t), 'markdown': serialize(t), 'archived': t['status'] in TERMINAL}
                elif args.command in ('list', 'next'):
                    limit = args.limit
                    if not 1 <= limit <= 100:
                        raise BacklogError('limit must be 1..100')
                    filtered = [t for t in tasks.values() if ((t['status'] == args.status) if args.command == 'list' and args.status else (t['status'] in ACTIVE if args.command == 'list' else ready(t, tasks)))]
                    if args.command == 'list' and args.status in TERMINAL:
                        # Terminal listings are explicit historical queries.
                        # Sort using paths without parsing the archive; only
                        # read the selected page's Markdown bodies.
                        filtered.sort(key=lambda t: (t['path'].parent.name, t['id']), reverse=True)
                        page = [read_task(t['path']) for t in filtered[:limit]]
                    else:
                        filtered.sort(key=lambda t: (PRIORITIES.index(t['priority']), t['created_at'], t['id']))
                        page = filtered[:limit]
                    result = {'tasks': [compact(t) for t in page], 'total': len(filtered), 'has_more': len(filtered) > limit}
                elif args.command == 'status':
                    doing = sorted((t for t in tasks.values() if t['status'] == 'doing'),
                                   key=lambda t: (PRIORITIES.index(t['priority']), t['created_at'], t['id']))
                    result = {'counts': {status: sum(t['status']==status for t in tasks.values()) for status in STATES},
                              'ready': sum(ready(t, tasks) for t in tasks.values()),
                              'doing': [compact(t) for t in doing[:10]]}
                else:
                    raise BacklogError('unsupported command')
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (BacklogError, OSError, UnicodeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
