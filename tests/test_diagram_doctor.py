"""Read-only doctor contracts with mocked inventories and probes.

No dependency is installed, downloaded, launched, or authorized by these tests.
Temporary files are synthetic package/runtime metadata, never real renderers.
"""
from pathlib import Path
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/huawei-html-ppt/scripts'))
import diagram_adapter as api
from diagram_adapter import doctor
import ppt


class DiagramDoctorTests(unittest.TestCase):
    BINARIES = {'git', 'pdfinfo', 'pdftotext', 'inkscape', 'node', 'chromium',
                'xelatex', 'kpsewhich', 'pdftocairo', 'pdftoppm'}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='readonly-doctor-fixture-')
        self.path = Path(self.temp.name)
        self.root = self.path / 'checkout'; self.root.mkdir()
        (self.root / 'requirements.txt').write_text('synthetic-diagram-package==1.2.3\n')
        self.bin = self.path / 'bin'; self.bin.mkdir()
        for name in self.BINARIES:
            executable = self.bin / name
            executable.write_text('Synthetic executable fixture: must never run.\n')
            executable.chmod(0o755)
        package = self.root / 'node_modules/playwright/package.json'
        package.parent.mkdir(parents=True)
        package.write_text(json.dumps({'name': 'playwright', 'version': '1.62.1'}))
        bundle = self.root / 'third_party/drawio/app.min.js'
        bundle.parent.mkdir(parents=True); bundle.write_bytes(b'Synthetic bundle, not executable JavaScript.')
        manifest = self.root / 'skills/technical-architecture-diagrams/scripts/drawio_runtime/graph-runtime.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'version': 'synthetic-fixture',
            'sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
            'download_url': 'https://example.invalid/synthetic-bundle'}))
        self.probe_calls = []

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self):
        return {str(p.relative_to(self.path)): (p.read_bytes(), p.stat().st_mode)
                for p in self.path.rglob('*') if p.is_file()}

    def inspect(self, request=None, missing=(), head=None, dirty='', git_error=False,
                versions=None, node_result=None, tex_missing=(), configured=True, env_extra=None):
        request = {'agent_dispatch_available': True, **(request or {})}
        installed = self.BINARIES - set(missing)
        versions = {'synthetic-diagram-package': '1.2.3'} if versions is None else versions
        self.probe_calls = []
        def which(name):
            return str(self.bin / name) if name in installed else None
        def package_version(name):
            if name not in versions: raise doctor.importlib.metadata.PackageNotFoundError(name)
            return versions[name]
        def probe(command, timeout=15):
            self.probe_calls.append(list(command))
            name = Path(command[0]).name
            if name == 'git':
                self.assertEqual(command[1:3], ['-c', 'core.fsmonitor=false'])
                self.assertIn('-C', command)
                if git_error: return {'ok': False, 'output': '', 'error': 'synthetic unreadable checkout'}
                if command[-2:] == ['rev-parse', 'HEAD']:
                    return {'ok': True, 'output': api.PIN if head is None else head, 'error': ''}
                self.assertEqual(command[-3:], ['status', '--porcelain', '--untracked-files=normal'])
                return {'ok': True, 'output': dirty, 'error': ''}
            if name == 'node':
                self.assertEqual(command[1:], ['--version'])
                return node_result if node_result is not None else {'ok': True, 'output': 'v22.0.0', 'error': ''}
            if name == 'kpsewhich':
                self.assertEqual(len(command), 2)
                available = command[1] not in tex_missing
                return {'ok': available, 'output': '/synthetic-tex/' + command[1] if available else '', 'error': ''}
            self.fail('Unexpected probe (possibly mutating): ' + repr(command))
        environment = {'INFRA_IO_ROOT': str(self.root)} if configured else {}
        environment.update(env_extra or {})
        before = self.snapshot()
        with patch.dict(os.environ, environment, clear=True), \
                patch.object(doctor.shutil, 'which', side_effect=which), \
                patch.object(doctor.importlib.metadata, 'version', side_effect=package_version), \
                patch.object(doctor, 'probe', side_effect=probe), \
                patch.object(doctor.subprocess, 'run', side_effect=AssertionError('Unmocked process launch is forbidden')):
            result = api.preflight(request)
        self.assertEqual(self.snapshot(), before, 'Doctor must not modify inventory or checkout files')
        self.assertTrue(result['read_only'])
        self.assertFalse(result['installation_executed'])
        self.assertTrue(result['configuration_is_not_consent'])
        return result

    @staticmethod
    def components(result):
        return {item['component']: item for item in result['checks']}

    def test_ready_common_does_not_repeat_installation_question(self):
        first = self.inspect(); second = self.inspect()
        self.assertEqual(first, second)
        self.assertEqual(first['status'], 'ready_for_workflow')
        self.assertFalse(first['consent_required']); self.assertEqual(first['install_plan'], [])
        self.assertIn('Continue workflow', first['next_action'])
        self.assertEqual(first['dependency'], {'repository': api.REPOSITORY, 'commit': api.PIN})

    def test_no_dispatch_stays_blocked_even_when_software_is_ready(self):
        for available in (False, None, 'yes', 1):
            with self.subTest(available=available):
                result = self.inspect({'agent_dispatch_available': available})
                self.assertEqual(result['status'], 'blocked_no_agent_dispatch')
                self.assertEqual(result['install_plan'], [])
                self.assertFalse(result['consent_required'])
                self.assertNotIn('ask for explicit installation confirmation', result['next_action'].lower())

    def test_install_flags_are_not_consent_and_never_execute_installation(self):
        baseline = self.inspect({'backend': 'report'}, missing={'inkscape'})
        for value in (True, False, 'approved', {'confirmed': True}):
            with self.subTest(value=value):
                result = self.inspect({'backend': 'report', 'install': value}, missing={'inkscape'})
                self.assertEqual(result, baseline)
                self.assertEqual(result['status'], 'needs_installation_review')
                self.assertTrue(result['consent_required'])

    def test_declined_installation_stays_blocked_without_repeating_question(self):
        request = {'backend': 'report', 'installation_decision': 'declined', 'install': True}
        first = self.inspect(request, missing={'inkscape'})
        self.assertEqual(first, self.inspect(request, missing={'inkscape'}))
        self.assertEqual(first['status'], 'blocked_installation_declined')
        self.assertTrue(first['installation_declined'])
        self.assertIn('do not repeat', first['next_action'])
        self.assertNotIn('ask for explicit installation confirmation', first['next_action'].lower())

    def test_prior_decline_does_not_block_available_software_or_grant_consent(self):
        result = self.inspect({'installation_decision': 'declined'})
        self.assertEqual(result['status'], 'ready_for_workflow')
        self.assertEqual(result['install_plan'], [])
        self.assertFalse(result['consent_required'])
        self.assertIn('Continue workflow', result['next_action'])
        for flag in ('approved', 'accepted', True):
            result = self.inspect({'backend': 'report', 'installation_decision': flag}, missing={'inkscape'})
            self.assertEqual(result['status'], 'needs_installation_review')
            self.assertTrue(result['consent_required'])
            self.assertFalse(result['installation_executed'])

    def test_missing_components_disclose_source_pin_location_and_impact(self):
        result = self.inspect({'backend': 'report'}, missing={'inkscape'}, versions={})
        self.assertEqual({x['component'] for x in result['install_plan']}, {'inkscape', 'python:synthetic-diagram-package'})
        for item in result['install_plan']:
            for field in ('required_version', 'source', 'install_location', 'impact'):
                self.assertIsInstance(item[field], str); self.assertTrue(item[field].strip())
        package = self.components(result)['python:synthetic-diagram-package']
        self.assertEqual(package['required_version'], '1.2.3')
        self.assertIn('/1.2.3/', package['source'])

    def test_dirty_and_wrong_pin_are_preserved_not_repaired_or_overwritten(self):
        for arguments, state in (({'dirty': ' M user-work.drawio'}, 'dirty'),
                                 ({'dirty': '?? user-notes.txt'}, 'dirty'),
                                 ({'head': '0' * 40}, 'version_mismatch')):
            with self.subTest(state=state, arguments=arguments):
                result = self.inspect(**arguments)
                self.assertEqual(result['checkout_state'], state)
                self.assertEqual(result['status'], 'needs_installation_review')
                components = self.components(result)
                self.assertNotIn('python:synthetic-diagram-package', components)
                self.assertEqual(components['infra_io_checkout']['required_version'], api.PIN)
                self.assertIn('python_dependencies', components)
                self.assertTrue(all(Path(c[0]).name == 'git' for c in self.probe_calls))

    def test_unreadable_checkout_and_missing_git_fail_closed(self):
        result = self.inspect(git_error=True)
        self.assertEqual(result['checkout_state'], 'unreadable')
        self.assertEqual(result['status'], 'needs_installation_review')
        result = self.inspect(missing={'git'})
        self.assertEqual(self.probe_calls, [])
        self.assertEqual(self.components(result)['infra_io_checkout']['status'], 'missing_or_incompatible')

    def test_unconfigured_checkout_asks_for_pinned_location_not_a_download(self):
        result = self.inspect(configured=False)
        self.assertEqual(result['checkout_state'], 'not_configured')
        self.assertEqual(self.probe_calls, [])
        self.assertEqual(result['status'], 'needs_installation_review')
        checkout = self.components(result)['infra_io_checkout']
        self.assertEqual(checkout['source'], api.REPOSITORY)
        self.assertEqual(checkout['required_version'], api.PIN)
        self.assertIn('confirmed', checkout['install_location'])

    def test_request_checkout_path_takes_precedence_over_environment(self):
        other = self.path / 'not-present'
        result = self.inspect({'infra_root': str(other)})
        self.assertEqual(self.probe_calls, [])
        self.assertEqual(self.components(result)['infra_io_checkout']['install_location'], str(other))

    def test_missing_requirements_manifest_is_not_ready(self):
        (self.root / 'requirements.txt').unlink()
        result = self.inspect()
        self.assertEqual(result['status'], 'needs_installation_review')
        self.assertEqual(self.components(result)['python_requirements_manifest']['status'], 'missing_or_incompatible')

    def test_empty_or_unpinned_requirement_manifest_is_not_silently_ready(self):
        for text in ('', '# No actual dependency declarations\n', 'synthetic-diagram-package>=1.2.3\n'):
            with self.subTest(text=text):
                (self.root / 'requirements.txt').write_text(text)
                result = self.inspect()
                self.assertEqual(result['status'], 'needs_installation_review')
                self.assertIn('python_requirements_manifest', self.components(result))

    def test_python_version_mismatch_is_disclosed_not_uninstalled(self):
        result = self.inspect(versions={'synthetic-diagram-package': '9.9.9'})
        package = self.components(result)['python:synthetic-diagram-package']
        self.assertEqual(package['status'], 'missing_or_incompatible')
        self.assertEqual(package['detail'], '9.9.9')
        self.assertIn('Do not uninstall', package['impact'])

    def test_backend_specific_checks_do_not_launch_renderers(self):
        common = self.components(self.inspect())
        report = self.components(self.inspect({'backend': 'report'}))
        drawio = self.components(self.inspect({'backend': 'drawio'}))
        tikz = self.components(self.inspect({'backend': 'tikz'}))
        self.assertNotIn('inkscape', common); self.assertIn('inkscape', report)
        self.assertNotIn('node', report); self.assertNotIn('xelatex', report)
        self.assertTrue({'node', 'playwright', 'chromium', 'drawio_bundle'} <= set(drawio))
        self.assertNotIn('xelatex', drawio)
        self.assertTrue({'xelatex', 'kpsewhich', 'pdftocairo', 'pdftoppm', 'tex:tikz.sty'} <= set(tikz))
        self.assertNotIn('node', tikz); self.assertNotIn('playwright', tikz)
        self.assertTrue(all(Path(c[0]).name in {'git', 'kpsewhich'} for c in self.probe_calls))

    def test_node_probe_requires_success_and_supported_version(self):
        for probe_result in ({'ok': False, 'output': 'v22.0.0', 'error': 'synthetic process failure'},
                             {'ok': True, 'output': 'v18.0.0', 'error': ''},
                             {'ok': True, 'output': 'not a version', 'error': ''}):
            with self.subTest(probe_result=probe_result):
                result = self.inspect({'backend': 'drawio'}, node_result=probe_result)
                self.assertEqual(self.components(result)['node']['status'], 'missing_or_incompatible')

    def test_drawio_checks_package_version_and_bundle_hash_without_execution(self):
        package = self.root / 'node_modules/playwright/package.json'
        package.write_text(json.dumps({'version': '0.0.0'}))
        result = self.inspect({'backend': 'drawio'})
        self.assertEqual(self.components(result)['playwright']['status'], 'missing_or_incompatible')
        bundle = self.root / 'third_party/drawio/app.min.js'; bundle.write_bytes(b'tampered synthetic bundle')
        result = self.inspect({'backend': 'drawio'})
        self.assertEqual(self.components(result)['drawio_bundle']['status'], 'missing_or_incompatible')

    def test_malformed_playwright_metadata_is_reported_not_executed(self):
        package = self.root / 'node_modules/playwright/package.json'
        for value in ('[]', 'null', '{broken', '{"version": 123}'):
            with self.subTest(value=value):
                package.write_text(value)
                result = self.inspect({'backend': 'drawio'})
                self.assertEqual(self.components(result)['playwright']['status'], 'missing_or_incompatible')

    def test_malformed_graph_metadata_is_reported_not_downloaded(self):
        manifest = self.root / 'skills/technical-architecture-diagrams/scripts/drawio_runtime/graph-runtime.json'
        for value in ('[]', 'null', '{broken', '{"version": 123, "sha256": "wrong"}',
                      '{"version": "fixture", "sha256": []}'):
            with self.subTest(value=value):
                manifest.write_text(value)
                result = self.inspect({'backend': 'drawio'})
                self.assertEqual(self.components(result)['drawio_bundle']['status'], 'missing_or_incompatible')

    def test_nonexecutable_chrome_override_is_not_reported_available(self):
        browser = self.bin / 'chromium'; browser.chmod(0o644)
        result = self.inspect({'backend': 'drawio'}, env_extra={'CHROME_BINARY': str(browser)})
        self.assertEqual(self.components(result)['chromium']['status'], 'missing_or_incompatible')

    def test_missing_tex_format_is_reported_without_cache_regeneration(self):
        result = self.inspect({'backend': 'tikz'}, tex_missing={'xelatex.fmt', 'tikz.sty'})
        self.assertEqual(result['status'], 'needs_installation_review')
        components = self.components(result)
        self.assertEqual(components['tex:xelatex.fmt']['status'], 'missing_or_incompatible')
        self.assertEqual(components['tex:tikz.sty']['status'], 'missing_or_incompatible')
        self.assertNotIn('node', components)

    def test_missing_software_cannot_make_unavailable_dispatch_ready(self):
        result = self.inspect({'backend': 'tikz', 'agent_dispatch_available': False, 'install': True}, missing={'xelatex'})
        self.assertEqual(result['status'], 'blocked_no_agent_dispatch')
        self.assertNotIn('independent_agent_dispatch', {x['component'] for x in result['install_plan']})
        self.assertTrue(result['consent_required'])

    def test_invalid_requests_do_not_run_any_probe(self):
        with patch.object(doctor, 'probe') as probe:
            for request in ([], None, {'backend': 'install'}, {'backend': 'shell'}):
                with self.subTest(request=request):
                    with self.assertRaises(ValueError): api.preflight(request)
            probe.assert_not_called()

    def test_probe_is_read_only_and_returns_nonzero_timeout_errors(self):
        command = ['/synthetic/git', '-c', 'core.fsmonitor=false', 'status', '--porcelain']
        for returncode in (0, 1):
            completed = subprocess.CompletedProcess(command, returncode, '  output\n', '  diagnostic\n')
            with patch.object(doctor.subprocess, 'run', return_value=completed) as run:
                result = doctor.probe(command)
            self.assertEqual(result['ok'], returncode == 0)
            self.assertEqual(result['output'], 'output'); self.assertEqual(result['error'], 'diagnostic')
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0], command)
            self.assertEqual(run.call_args.kwargs['env']['GIT_OPTIONAL_LOCKS'], '0')
            self.assertNotIn('shell', run.call_args.kwargs)
        for failure in (OSError('synthetic missing command'), subprocess.TimeoutExpired('synthetic probe', 15)):
            with patch.object(doctor.subprocess, 'run', side_effect=failure):
                self.assertFalse(doctor.probe(command)['ok'])

    def test_cli_doctor_only_delegates_and_does_not_create_output(self):
        source = self.path / 'doctor-request.json'; api.save(source, {'backend': 'report', 'install': True})
        result = {'status': 'synthetic_mock_only', 'installation_executed': False}
        stdout = io.StringIO()
        with patch.object(api, 'preflight', return_value=result) as preflight, \
                patch.object(sys, 'argv', ['ppt.py', 'diagram-doctor', str(source)]), redirect_stdout(stdout):
            code = ppt.main()
        self.assertEqual(code, 0); self.assertEqual(json.loads(stdout.getvalue()), result)
        preflight.assert_called_once_with({'backend': 'report', 'install': True})


if __name__ == '__main__':
    unittest.main()
