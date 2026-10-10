import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import importlib.util
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'backlog.py'
spec = importlib.util.spec_from_file_location('backlog_cli', SCRIPT)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class BacklogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.call('init')

    def call(self, *args, fail=False):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = app.main(['--root', str(self.root), *map(str, args)])
        if not fail and rc:
            self.fail(err.getvalue())
        if fail:
            self.assertEqual(rc, 1)
            return json.loads(err.getvalue())['error']
        self.assertEqual(rc, 0)
        return json.loads(out.getvalue())

    def task(self, title='Example', *extras):
        return self.call('add', title, '--goal', 'Do it', '--ac', 'Works', *extras)['id']

    def test_init_creates_store_not_installer(self):
        self.assertTrue((self.root / '.backlog/tasks').is_dir())
        self.assertTrue((self.root / '.backlog/archive').is_dir())
        self.assertIn('.lock', (self.root / '.backlog/.gitignore').read_text())
        self.assertTrue(self.call('doctor')['ok'])

    def test_inbox_promote_and_handoff(self):
        item = self.call('add', 'Future thing')['id']
        self.assertEqual(self.call('show', item)['task']['status'], 'inbox')
        self.call('edit', item, '--goal', 'Deliver feature', '--ac', 'passes')
        self.assertEqual(self.call('next')['total'], 1)
        self.call('start', item)
        self.call('note', item, '--text', 'Next: tests. Files: src/main.py')
        self.assertIn('Next: tests', self.call('show', item)['markdown'])

    def test_dependency_and_close(self):
        first = self.task('first')
        second = self.task('second', '--depends', first)
        self.assertEqual([t['id'] for t in self.call('next')['tasks']], [first])
        self.call('start', first)
        self.assertIn('all acceptance', self.call('close', first, '--evidence', 'tests passed', fail=True))
        self.call('check', first, 1)
        self.call('close', first, '--evidence', 'pytest tests/test_api.py -q: 4 passed')
        self.assertEqual([t['id'] for t in self.call('next')['tasks']], [second])
        self.assertFalse((self.root / '.backlog/tasks' / (first+'.md')).exists())
        self.assertTrue(self.call('show', first)['archived'])
        self.assertEqual(self.call('doctor')['tasks'], 2)
        self.call('start', second)
        self.call('check', second, 1)
        self.call('close', second, '--evidence', 'smoke test passed')
        self.assertEqual(self.call('next')['total'], 0)

    def test_cancelled_dependency_does_not_unblock(self):
        first = self.task('first')
        second = self.task('second', '--depends', first)
        self.call('cancel', first, '--reason', 'not needed')
        self.assertEqual(self.call('next')['total'], 0)
        self.assertIn('not ready', self.call('start', second, fail=True))

    def test_cycle_and_missing_dependency_rejected(self):
        first = self.task('first')
        second = self.task('second', '--depends', first)
        self.assertIn('cycle', self.call('edit', first, '--depends', second, fail=True))
        self.assertEqual(self.call('show', first)['task']['depends'], [])
        missing = 'BL-'+'1'*16
        self.assertIn('missing dependency', self.call('edit', first, '--depends', missing, fail=True))

    def test_close_requires_valid_evidence_and_check(self):
        item = self.task()
        self.assertIn('only doing', self.call('close', item, '--evidence', 'pass', fail=True))
        self.call('start', item)
        self.assertIn('acceptance criteria', self.call('close', item, '--evidence', 'pass', fail=True))
        self.call('check', item, 1)
        self.assertIn('evidence required', self.call('close', item, '--evidence', '', fail=True))
        self.call('close', item, '--evidence', 'unit test observed pass')
        self.assertIn('not ready', self.call('start', item, fail=True))

    def test_block_unblock(self):
        item = self.task()
        self.call('start', item)
        self.call('block', item, '--reason', 'needs SSO credentials')
        self.assertEqual(self.call('next')['total'], 0)
        self.assertIn('needs SSO', self.call('show', item)['markdown'])
        self.call('unblock', item)
        self.assertEqual(self.call('next')['total'], 1)

    def test_reopen_resets_checks_and_keeps_id(self):
        item = self.task()
        self.call('start', item)
        self.call('check', item, 1)
        self.call('close', item, '--evidence', 'passes')
        self.call('reopen', item)
        self.assertIn('- [ ] Works', self.call('show', item)['markdown'])
        self.assertFalse(self.call('show', item)['archived'])
        self.assertEqual(self.call('next')['total'], 1)

    def test_ready_order_and_bounded_outputs(self):
        p2 = self.task('later')
        p1 = self.task('urgent', '--priority', 'P1')
        self.assertEqual(self.call('next', '--limit', 1)['tasks'][0]['id'], p1)
        self.assertTrue(self.call('next', '--limit', 1)['has_more'])
        self.assertIn('limit', self.call('next', '--limit', 101, fail=True))
        self.assertEqual(self.call('list', '--status', 'todo')['total'], 2)
        self.assertIn(p2, [v['id'] for v in self.call('list')['tasks']])

    def test_atomic_write_preserves_previous_on_replace_error(self):
        item = self.task()
        path = self.root / '.backlog/tasks' / (item+'.md')
        previous = path.read_bytes()
        with patch.object(app.os, 'replace', side_effect=OSError('simulated crash')):
            self.assertIn('simulated crash', self.call('note', item, '--text', 'progress', fail=True))
        self.assertEqual(path.read_bytes(), previous)
        self.assertEqual(list(path.parent.glob('.tmp-*')), [])

    def test_duplicate_across_archive_detected(self):
        item = self.task()
        archived = self.root / '.backlog/archive/2026-10'
        archived.mkdir()
        original = (self.root / '.backlog/tasks' / (item+'.md')).read_text()
        (archived / (item+'.md')).write_text(original)
        self.assertIn('duplicate task ID', self.call('doctor', fail=True))

    def test_symlink_task_rejected(self):
        item = self.task()
        path = self.root / '.backlog/tasks' / (item+'.md')
        path.unlink()
        path.symlink_to(self.root / 'missing')
        self.assertIn('symlink task', self.call('doctor', fail=True))

    def test_format_rejects_heading_injection(self):
        self.assertIn('headings', self.call('add', 'bad', '--goal', 'Do it\n## Evidence', '--ac', 'Works', fail=True))

    def test_concurrent_process_adds_are_serialized(self):
        def create(i):
            cmd = [sys.executable, str(SCRIPT), '--root', str(self.root), 'add', f'concurrent-{i}', '--goal', 'G', '--ac', 'A']
            return subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(create, range(12)))
        self.assertTrue(all(r.returncode == 0 for r in results), [r.stderr for r in results])
        self.assertEqual(self.call('list', '--limit', 100)['total'], 12)
        self.assertEqual(self.call('doctor')['tasks'], 12)

    def test_task_references_survive_resume(self):
        item = self.call('add', 'Feature', '--goal', 'G', '--ac', 'works', '--ref', 'docs/feature.md')['id']
        self.call('start', item)
        self.call('note', item, '--text', 'Next: implement. Source: docs/feature.md')
        info = self.call('show', item)['markdown']
        self.assertIn('docs/feature.md', info)
        self.assertIn('Next: implement', info)

    def test_deep_dependency_chain_does_not_overflow(self):
        folder = self.root / '.backlog/tasks'
        previous = None
        for i in range(1250):
            ident = 'BL-' + f'{i:016X}'
            t = dict(id=ident, title=f'Task {i}', status='todo', priority='P2',
                     depends=[previous] if previous else [], created_at=app.now(), updated_at=app.now(),
                     sections={name: '' for name in app.SECTIONS})
            t['sections']['Goal'] = 'G'
            t['sections']['Acceptance Criteria'] = '- [ ] A'
            (folder / f'{ident}.md').write_text(app.serialize(t))
            previous = ident
        self.assertEqual(self.call('doctor')['tasks'], 1250)
        self.assertEqual(self.call('next')['total'], 1)

    def test_no_external_dependencies_and_legacy_warning(self):
        (self.root / '.agent-workflow').mkdir()
        self.assertTrue(self.call('doctor')['legacy_present'])
        self.assertNotIn('backlog.md', SCRIPT.read_text())


if __name__ == '__main__':
    unittest.main()
