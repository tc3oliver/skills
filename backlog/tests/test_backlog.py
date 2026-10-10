import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import importlib.util
import subprocess
import os
import time
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
        archived = self.root / '.backlog/archive/done/2026-10'
        archived.mkdir(parents=True)
        original = (self.root / '.backlog/tasks' / (item+'.md')).read_text()
        (archived / (item+'.md')).write_text(original)
        self.assertIn('duplicate task ID', self.call('doctor', fail=True))

    def test_symlink_task_rejected(self):
        item = self.task()
        path = self.root / '.backlog/tasks' / (item+'.md')
        path.unlink()
        try:
            path.symlink_to(self.root / 'missing')
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f'cannot create symlink on this platform: {exc}')
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


    def test_symlinked_archive_ancestors_never_touch_external_data(self):
        item = self.task()
        self.call('start', item)
        self.call('check', item, 1)
        self.call('close', item, '--evidence', 'smoke succeeded')
        folder = self.root / '.backlog/archive/done'
        month = next(p for p in folder.iterdir() if p.is_dir())
        original = (month / (item + '.md')).read_bytes()
        external = self.root / 'external'
        external.mkdir()
        (external / (item + '.md')).write_bytes(original)
        (month / (item + '.md')).unlink()
        month.rmdir()
        try:
            month.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f'cannot create directory symlink on this platform: {exc}')
        self.assertIn('symlink archive directory', self.call('show', item, fail=True))
        self.assertIn('symlink archive directory', self.call('reopen', item, fail=True))
        self.assertIn('symlink archive directory', self.call('doctor', '--repair', fail=True))
        self.assertEqual((external / (item + '.md')).read_bytes(), original)

    def test_symlink_archive_status_directory_rejected(self):
        status = self.root / '.backlog/archive/done'
        external = self.root / 'external'
        external.mkdir()
        try:
            status.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f'cannot create directory symlink on this platform: {exc}')
        self.assertIn('symlink archive directory', self.call('next', fail=True))

    def test_close_rename_failure_is_atomic_at_source(self):
        item = self.task()
        self.call('start', item)
        self.call('check', item, 1)
        source = self.root / '.backlog/tasks' / (item+'.md')
        old = source.read_bytes()
        with patch.object(app.os, 'rename', side_effect=OSError('rename rejected')):
            self.assertIn('rename rejected', self.call('close', item, '--evidence', 'check success', fail=True))
        self.assertEqual(source.read_bytes(), old)
        self.assertEqual(self.call('show', item)['task']['status'], 'doing')
        self.assertTrue(self.call('doctor')['ok'])

    def test_close_write_failure_repaired_without_data_loss(self):
        item = self.task()
        self.call('start', item)
        self.call('check', item, 1)
        original = self.root / '.backlog/tasks' / (item + '.md')
        prior = original.read_bytes()
        with patch.object(app, 'atomic_write', side_effect=OSError('write rejected')):
            self.assertIn('write rejected', self.call('close', item, '--evidence', 'pass', fail=True))
        self.assertIn('run doctor --repair', self.call('doctor', fail=True))
        result = self.call('doctor', '--repair')
        self.assertEqual(result['repaired'], [item])
        self.assertEqual(original.read_bytes(), prior)
        self.assertEqual(self.call('show', item)['task']['status'], 'doing')
        self.call('close', item, '--evidence', 'pass')
        self.assertTrue(self.call('doctor')['ok'])

    def test_reopen_rename_failure_preserves_archive(self):
        item = self.task()
        self.call('start', item)
        self.call('check', item, 1)
        self.call('close', item, '--evidence', 'pass')
        with patch.object(app.os, 'rename', side_effect=OSError('cannot rename')):
            self.assertIn('cannot rename', self.call('reopen', item, fail=True))
        self.assertTrue(self.call('show', item)['archived'])
        self.assertTrue(self.call('doctor')['ok'])

    def test_reopen_write_failure_repair_retains_prior_evidence(self):
        item = self.task()
        self.call('start', item)
        self.call('check', item, 1)
        self.call('close', item, '--evidence', 'pytest: 3 passed')
        with patch.object(app, 'atomic_write', side_effect=OSError('write rejected')):
            self.assertIn('write rejected', self.call('reopen', item, fail=True))
        self.assertIn('run doctor --repair', self.call('doctor', fail=True))
        self.assertEqual(self.call('doctor', '--repair')['repaired'], [item])
        self.assertTrue(self.call('show', item)['archived'])
        self.assertIn('pytest: 3 passed', self.call('show', item)['markdown'])
        self.call('reopen', item)
        markdown = self.call('show', item)['markdown']
        self.assertIn('previous validation is historical', markdown)
        self.assertIn('pytest: 3 passed', markdown)
        self.assertIn('## Evidence\n\n', markdown)
        self.assertEqual(self.call('show', item)['task']['status'], 'todo')

    def test_archive_metadata_not_parsed_except_doctor_and_explicit_show(self):
        item = self.task()
        self.call('start', item)
        self.call('check', item, 1)
        self.call('close', item, '--evidence', 'pass')
        with patch.object(app, 'read_task', wraps=app.read_task) as reader:
            self.call('next')
            self.call('status')
            self.assertEqual(reader.call_count, 0)
            result = self.call('list', '--status', 'done', '--limit', 1)
            self.assertEqual(result['tasks'][0]['title'], 'Example')
            self.assertEqual(reader.call_count, 1)
            self.assertTrue(self.call('show', item)['archived'])
            self.assertEqual(reader.call_count, 2)
            self.call('doctor')
            self.assertEqual(reader.call_count, 3)

    def test_archive_directory_status_and_cancelled_dependency(self):
        first = self.task('first')
        second = self.task('second', '--depends', first)
        self.call('cancel', first, '--reason', 'no longer wanted')
        self.assertEqual(self.call('next')['total'], 0)
        self.assertEqual(self.call('list', '--status', 'cancelled')['tasks'][0]['title'], 'first')
        self.assertTrue(self.call('doctor')['ok'])
        self.call('reopen', first)
        self.assertEqual(self.call('next')['total'], 1)
        self.call('start', first)
        self.call('check', first, 1)
        self.call('close', first, '--evidence', 'passed')
        self.assertEqual(self.call('next')['tasks'][0]['id'], second)

    def test_ac_reset_requires_confirmation_and_reports_reset(self):
        item = self.task()
        self.call('start', item)
        self.call('check', item, 1)
        self.assertIn('checked acceptance criteria', self.call('edit', item, '--ac', 'New behavior', fail=True))
        self.assertIn('- [x] Works', self.call('show', item)['markdown'])
        result = self.call('edit', item, '--ac', 'New behavior', '--confirm-ac-reset')
        self.assertEqual(result['acceptance_reset'], 1)
        self.assertIn('- [ ] New behavior', self.call('show', item)['markdown'])
        self.assertIn('all acceptance criteria', self.call('close', item, '--evidence', 'pass', fail=True))

    def test_doing_status_is_priority_sorted(self):
        low = self.task('low')
        high = self.task('high', '--priority', 'P0')
        self.call('start', low)
        self.call('start', high)
        self.assertEqual([x['id'] for x in self.call('status')['doing']], [high, low])

    def test_read_accepts_pre_history_task_files(self):
        item = self.task()
        path = self.root / '.backlog/tasks' / (item + '.md')
        data = path.read_text()
        data = data.replace('## History\n\n', '')
        path.write_text(data)
        self.assertEqual(self.call('show', item)['task']['status'], 'todo')
        self.call('note', item, '--text', 'updated')
        self.assertIn('## History', path.read_text())

    def test_many_archived_tasks_do_not_expand_context_or_parse_bodies(self):
        # Stress read path without asserting a machine-dependent timing limit.
        folder = self.root / '.backlog/archive/done/2026-10'
        folder.mkdir(parents=True)
        count = 1200
        for i in range(count):
            ident = f'BL-{i:016X}'
            (folder / f'{ident}.md').write_text('not parsed for next/status')
        started = time.perf_counter()
        summary = self.call('status')
        next_tasks = self.call('next')
        elapsed = time.perf_counter() - started
        self.assertEqual(summary['counts']['done'], count)
        self.assertEqual(next_tasks['total'], 0)
        self.assertLess(len(json.dumps(summary)), 4096)
        self.assertLess(len(json.dumps(next_tasks)), 4096)
        self.assertLess(elapsed, 5, f'archive metadata-only query took {elapsed:.2f}s')


    def test_archive_cache_invalidation_and_rebuild(self):
        self.assertIn('.archive-cache.json', (self.root / '.backlog/.gitignore').read_text())
        a = self.task('first')
        self.call('start', a)
        self.call('check', a, 1)
        self.call('close', a, '--evidence', 'pass')
        self.call('status')
        cache = self.root / '.backlog/.archive-cache.json'
        self.assertTrue(cache.is_file())
        self.assertEqual(self.call('status')['counts']['done'], 1)
        b = self.task('second')
        self.call('start', b)
        self.call('check', b, 1)
        self.call('close', b, '--evidence', 'pass')
        self.assertEqual(self.call('status')['counts']['done'], 2)
        cache.write_text('{malformed')
        self.assertEqual(self.call('status')['counts']['done'], 2)
        self.assertTrue(self.call('doctor')['ok'])
        self.call('reopen', b)
        self.assertEqual(self.call('status')['counts']['done'], 1)

    def test_forged_cache_entry_does_not_unblock_dependency(self):
        missing = 'BL-' + 'F'*16
        first = self.task('first')
        dependent = self.task('dependent', '--depends', first)
        self.call('start', first)
        self.call('check', first, 1)
        self.call('close', first, '--evidence', 'pass')
        self.call('status')
        cache = self.root / '.backlog/.archive-cache.json'
        index = json.loads(cache.read_text())
        index['records'] = [r for r in index['records'] if r[2] != first]
        index['records'].append(['done', '2026-10', missing])
        cache.write_text(json.dumps(index))
        self.assertIn('missing dependency', self.call('next', fail=True))
        # Removing the cache restores the actual task's status from the archive.
        cache.unlink()
        self.assertEqual(self.call('next')['tasks'][0]['id'], dependent)

    def test_archive_file_symlink_detected_after_cache_is_warm(self):
        item = self.task()
        self.call('start', item)
        self.call('check', item, 1)
        self.call('close', item, '--evidence', 'pass')
        self.call('status')
        path = next((self.root / '.backlog/archive/done').glob('*/' + item + '.md'))
        external = self.root / 'external.md'
        before = path.read_bytes()
        external.write_bytes(before)
        path.unlink()
        try:
            path.symlink_to(external)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f'cannot create file symlink on this platform: {exc}')
        self.assertIn('symlink task', self.call('next', fail=True))
        self.assertEqual(external.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
