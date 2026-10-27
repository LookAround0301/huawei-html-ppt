"""Mocked orchestration contracts only: no design agent, renderer or visual QA.

The independent drawing repository owns brief/delivery schemas. Minimal fixture
objects below deliberately do not implement or certify those external schemas.
"""
from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/huawei-html-ppt/scripts'))
import diagram_adapter as api
from diagram_adapter import workflow
import ppt


class DiagramWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mocked-diagram-workflow-')
        self.path = Path(self.temp.name)
        self.counter = 0

    def tearDown(self):
        self.temp.cleanup()

    def next_directory(self):
        self.counter += 1
        path = self.path / str(self.counter)
        path.mkdir()
        return path

    def fixture(self):
        directory = self.next_directory()
        artifacts = directory / 'artifacts'; artifacts.mkdir()
        # Different bytes exercise selection only, not substantive design diversity.
        svgs = []
        for number in range(1, 4):
            svg = artifacts / f'variant-{number}.svg'
            svg.write_text(f'<svg xmlns="http://www.w3.org/2000/svg"><rect width="{number * 10}" height="10"/></svg>')
            svgs.append(svg)
        pdf = artifacts / 'all-variants.pdf'
        pdf.write_bytes(b'Synthetic mock archive bytes: NOT a real PDF or page-count proof.\n')
        variants = [{'id': f'variant-{number}', 'rendered_artifact_ids': [f'svg-{number}']}
                    for number in range(1, 4)]
        brief = directory / 'brief.json'
        api.save(brief, {'theme': api.theme(), 'synthetic_fixture': 'not a validated external brief'})
        record = directory / 'task-record.json'
        api.save(record, {'synthetic_fixture': 'No actual agent was dispatched by this test.'})
        dispatch = directory / 'dispatch.json'
        api.save(dispatch, {'status': 'completed', 'mechanism': 'independent_agent',
            'host_agent_id': 'synthetic-host', 'drawing_agent_id': 'synthetic-drawing-agent',
            'brief_sha256': api.sha(brief), 'task_record': str(record),
            'task_record_sha256': api.sha(record)})
        delivery = directory / 'delivery.json'
        api.save(delivery, {'status': 'completed', 'synthetic_fixture': 'not a validated external delivery',
            'variants': variants, 'archive_pdf_artifact_id': 'archive-pdf',
            'artifacts': [{'id': f'svg-{number}', 'kind': 'rendered', 'path': svg.name, 'sha256': api.sha(svg)}
                          for number, svg in enumerate(svgs, 1)] +
                         [{'id': 'archive-pdf', 'kind': 'rendered', 'path': pdf.name, 'sha256': api.sha(pdf)}]})
        return {'directory': directory, 'artifacts': artifacts, 'svg': svgs[0], 'svgs': svgs,
                'pdf': pdf, 'variants': variants, 'brief': brief,
                'record': record, 'dispatch': dispatch, 'delivery': delivery,
                'output': directory / 'accepted'}

    def request(self, fixture):
        return {'brief': str(fixture['brief']), 'delivery': str(fixture['delivery']),
                'dispatch': str(fixture['dispatch']), 'artifact_root': str(fixture['artifacts']),
                'selected_variant_id': 'variant-1',
                'alt': 'Synthetic independently drawn fixture'}

    def accept(self, fixture, qa=None, failure=None, request=None):
        default_qa = {'status': 'pass', 'contract_status': 'pass', 'errors': [],
                      'semantic_visual_status': 'not_verified',
                      'brief_sha256': api.sha(fixture['brief']),
                      'delivery_sha256': api.sha(fixture['delivery'])}
        if qa is None: qa = default_qa
        elif isinstance(qa, dict): qa = {**default_qa, **qa}
        def execute(bridge, root, tool, args, output):
            self.assertEqual(tool, 'check_diagram_delivery.py')
            self.assertEqual(Path(args[args.index('--brief') + 1]), fixture['brief'])
            self.assertEqual(Path(args[args.index('--delivery') + 1]), fixture['delivery'])
            if failure is not None: raise failure
            api.save(Path(args[args.index('--output') + 1]), qa)
        with patch.object(api, 'dependency', return_value=self.path / 'synthetic-dependency'), \
                patch.object(workflow, 'execute', side_effect=execute):
            return api.accept_delivery(self.request(fixture) if request is None else request, fixture['output'])

    def test_prepare_reports_blocked_without_actual_dispatch_capability(self):
        for available in (None, False, 1, 'yes'):
            with self.subTest(available=available):
                directory = self.next_directory()
                request = {'brief': {'synthetic_fixture': 'facts/constraints placeholder'},
                           'agent_dispatch_available': available}
                def prepare_tool(bridge, root, tool, args, output):
                    self.assertEqual(tool, 'prepare_diagram_brief.py')
                    handoff = Path(args[args.index('--out-dir') + 1]); handoff.mkdir()
                    api.save(handoff / 'brief.json', request['brief'])
                    (handoff / 'agent-task.md').write_text('Synthetic handoff; no agent has run.')
                with patch.object(api, 'dependency', return_value=self.path), \
                        patch.object(workflow, 'execute', side_effect=prepare_tool) as external:
                    result = api.prepare_brief(request, directory / 'output')
                self.assertEqual(result['status'], 'blocked_no_agent_dispatch')
                self.assertEqual(external.call_count, 1)
                self.assertNotIn('blocks', result)
                self.assertEqual(result['brief_sha256'], api.sha(result['brief']))
                self.assertEqual(result['agent_task_sha256'], api.sha(result['agent_task']))

    def test_prepare_available_means_awaiting_not_executed(self):
        output = self.path / 'prepare'
        def prepare_tool(bridge, root, tool, args, directory):
            handoff = directory / 'handoff'; handoff.mkdir()
            api.save(handoff / 'brief.json', {'synthetic_fixture': True})
            (handoff / 'agent-task.md').write_text('Synthetic task only.')
        with patch.object(api, 'dependency', return_value=self.path), \
                patch.object(workflow, 'execute', side_effect=prepare_tool):
            result = api.prepare_brief({'brief': {}, 'agent_dispatch_available': True}, output)
        self.assertEqual(result['status'], 'awaiting_drawing_agent')
        self.assertIn('no design or rendering has run', result['dispatch'])
        self.assertNotIn('blocks', result)

    def test_prepare_propagates_external_contract_failure(self):
        with patch.object(api, 'dependency', return_value=self.path), \
                patch.object(workflow, 'execute', side_effect=ValueError('synthetic external schema failure')):
            with self.assertRaisesRegex(ValueError, 'external schema failure'):
                api.prepare_brief({'brief': {}}, self.path / 'failure')
        self.assertFalse((self.path / 'failure/handoff.json').exists())

    def test_prepare_requires_external_handoff_files(self):
        with patch.object(api, 'dependency', return_value=self.path), patch.object(workflow, 'execute'):
            with self.assertRaisesRegex(ValueError, 'did not produce a handoff'):
                api.prepare_brief({'brief': {}}, self.path / 'missing')

    def test_prepare_preserves_previous_output(self):
        output = self.path / 'existing'; output.mkdir()
        marker = output / 'keep.txt'; marker.write_text('preserve this evidence')
        with patch.object(api, 'dependency', return_value=self.path), patch.object(workflow, 'execute') as external:
            with self.assertRaises(ValueError): api.prepare_brief({'brief': {}}, output)
            external.assert_not_called()
        self.assertEqual(marker.read_text(), 'preserve this evidence')

    def test_dispatch_must_be_completed_independent_and_different_agent(self):
        replacements = ({'status': 'running'}, {'mechanism': 'host_inline'},
                        {'drawing_agent_id': 'synthetic-host'}, {'drawing_agent_id': ''},
                        {'drawing_agent_id': ' synthetic-host '},
                        {'host_agent_id': ' '}, {'brief_sha256': 'wrong'},
                        {'task_record_sha256': 'wrong'}, {'task_record': 'missing-record.json'})
        for replacement in replacements:
            with self.subTest(replacement=replacement):
                fixture = self.fixture(); evidence = api.read(fixture['dispatch'])
                evidence.update(replacement); api.save(fixture['dispatch'], evidence)
                with self.assertRaises(ValueError): self.accept(fixture)
                self.assertFalse((fixture['output'] / 'acceptance.json').exists())
                self.assertFalse((fixture['output'] / 'delivery-qa.json').exists())

    def test_dispatch_rejects_changed_brief_and_task_record(self):
        for field in ('brief', 'record'):
            with self.subTest(field=field):
                fixture = self.fixture(); fixture[field].write_text('tampered synthetic evidence')
                with self.assertRaises(ValueError): self.accept(fixture)

    def test_dispatch_relative_task_record_is_resolved_against_dispatch(self):
        fixture = self.fixture(); evidence = api.read(fixture['dispatch'])
        evidence['task_record'] = fixture['record'].name; api.save(fixture['dispatch'], evidence)
        result = self.accept(fixture)
        self.assertEqual(result['status'], 'accepted_contract_not_aesthetic_approval')

    def test_delivery_checker_failure_or_blocked_contract_cannot_accept(self):
        for status in ('fail', 'blocked', None):
            with self.subTest(status=status):
                fixture = self.fixture()
                with self.assertRaises(ValueError): self.accept(fixture, qa={'contract_status': status})
                self.assertFalse((fixture['output'] / 'acceptance.json').exists())
        fixture = self.fixture()
        with self.assertRaisesRegex(ValueError, 'synthetic checker failed'):
            self.accept(fixture, failure=ValueError('synthetic checker failed'))

    def test_blocked_delivery_is_not_complete_even_if_checker_says_pass(self):
        fixture = self.fixture(); delivery = api.read(fixture['delivery'])
        delivery['status'] = 'blocked'; api.save(fixture['delivery'], delivery)
        with self.assertRaisesRegex(ValueError, 'blocked'): self.accept(fixture)

    def test_malformed_external_objects_fail_cleanly(self):
        fixture = self.fixture()
        with self.assertRaises(ValueError): self.accept(fixture, qa=[])
        fixture = self.fixture(); api.save(fixture['delivery'], [])
        with self.assertRaises(ValueError): self.accept(fixture)

    def test_delivery_qa_must_bind_checked_brief_and_delivery(self):
        for field in ('brief_sha256', 'delivery_sha256'):
            with self.subTest(field=field):
                fixture = self.fixture()
                with self.assertRaises(ValueError): self.accept(fixture, qa={field: 'mismatched input'})
                self.assertFalse((fixture['output'] / 'acceptance.json').exists())

    def test_accept_rejects_unsafe_svg(self):
        for content in ('<svg><script/></svg>', '<svg><foreignObject/></svg>',
                        '<svg><use href="https://example.invalid/external.svg#x"/></svg>'):
            with self.subTest(content=content):
                fixture = self.fixture(); fixture['svg'].write_text(content)
                delivery = api.read(fixture['delivery']); delivery['artifacts'][0]['sha256'] = api.sha(fixture['svg'])
                api.save(fixture['delivery'], delivery)
                with self.assertRaises(ValueError): self.accept(fixture)

    def test_accept_rejects_changed_or_escaping_svg(self):
        fixture = self.fixture(); fixture['svg'].write_text('<svg><rect/></svg>')
        with self.assertRaises(ValueError): self.accept(fixture)
        for absolute in (False, True):
            fixture = self.fixture(); outside = fixture['directory'] / 'outside.svg'; outside.write_text('<svg/>')
            delivery = api.read(fixture['delivery'])
            delivery['artifacts'][0].update(path=str(outside) if absolute else '../outside.svg', sha256=api.sha(outside))
            api.save(fixture['delivery'], delivery)
            with self.assertRaises(ValueError): self.accept(fixture)

    def test_accept_requires_safe_rendered_svg(self):
        fixture = self.fixture(); delivery = api.read(fixture['delivery'])
        delivery['artifacts'][0]['kind'] = 'editable_source'; api.save(fixture['delivery'], delivery)
        with self.assertRaisesRegex(ValueError, 'No safe rendered SVG'): self.accept(fixture)

    def test_accepted_receipt_roundtrip_is_not_aesthetic_approval(self):
        fixture = self.fixture(); result = self.accept(fixture)
        self.assertEqual(result['status'], 'accepted_contract_not_aesthetic_approval')
        receipt = api.read(result['receipt']); self.assertEqual(len(receipt['bindings']), 5)
        self.assertIn('not automated aesthetic proof', receipt['review_boundary'])
        block = result['blocks'][0]
        self.assertEqual(api.read_generated(block, api.theme()), fixture['svg'].read_bytes())
        self.assertIn('data:image/svg+xml;base64,', api.generated_html(block))

    def test_high_level_theme_affinity_does_not_require_exact_colors(self):
        fixture = self.fixture(); result = self.accept(fixture); block = result['blocks'][0]
        receipt = api.read(result['receipt'])
        self.assertEqual(receipt['theme_policy'], 'affinity_not_exact_colors')
        self.assertEqual(api.read_generated(block, api.theme({'accent': '#336699', 'panel': '#EEEEEE'})),
                         fixture['svg'].read_bytes())
        # Existing low-level adapter tests retain their exact-theme contract.

    def test_readback_rejects_changed_svg(self):
        fixture = self.fixture(); result = self.accept(fixture); block = result['blocks'][0]
        fixture['svg'].write_text('<svg><rect/></svg>')
        with self.assertRaisesRegex(ValueError, 'SVG changed'): api.read_generated(block)

    def test_only_selected_variant_is_embedded_and_archive_is_returned(self):
        fixture = self.fixture(); request = self.request(fixture)
        request['selected_variant_id'] = 'variant-2'
        result = self.accept(fixture, request=request)
        self.assertEqual(result['selected_variant_id'], 'variant-2')
        self.assertEqual(result['variants'], fixture['variants'])
        self.assertEqual(len(result['blocks']), 1)
        block = result['blocks'][0]
        self.assertEqual(block['variant_id'], 'variant-2')
        self.assertEqual(Path(block['path']), fixture['svgs'][1])
        self.assertEqual(api.read_generated(block), fixture['svgs'][1].read_bytes())
        self.assertEqual(result['archive_pdf'], {'path': str(fixture['pdf']), 'sha256': api.sha(fixture['pdf'])})
        receipt = api.read(result['receipt'])
        self.assertEqual(receipt['archive_pdf'], result['archive_pdf'])
        self.assertEqual([item['path'] for item in receipt['artifacts']], [str(fixture['svgs'][1])])
        for unselected in (fixture['svgs'][0], fixture['svgs'][2]):
            with self.assertRaisesRegex(ValueError, 'SVG changed'):
                api.read_generated({**block, 'path': str(unselected)})

    def test_selection_is_explicit_existing_and_unambiguous(self):
        for selected in (None, '', ' ', 'unknown', 1):
            with self.subTest(selected=selected):
                fixture = self.fixture(); request = self.request(fixture)
                request['selected_variant_id'] = selected
                with self.assertRaises(ValueError): self.accept(fixture, request=request)
                self.assertFalse((fixture['output'] / 'acceptance.json').exists())
        fixture = self.fixture(); request = self.request(fixture); request.pop('selected_variant_id')
        with self.assertRaises(ValueError): self.accept(fixture, request=request)
        fixture = self.fixture(); delivery = api.read(fixture['delivery'])
        delivery['variants'].append(dict(delivery['variants'][0])); api.save(fixture['delivery'], delivery)
        with self.assertRaisesRegex(ValueError, 'duplicate'): self.accept(fixture)

    def test_selected_variant_cannot_fall_back_to_other_rendered_svg(self):
        for rendered_ids in ([], ['missing'], ['archive-pdf']):
            with self.subTest(rendered_ids=rendered_ids):
                fixture = self.fixture(); delivery = api.read(fixture['delivery'])
                delivery['variants'][0]['rendered_artifact_ids'] = rendered_ids
                api.save(fixture['delivery'], delivery)
                with self.assertRaisesRegex(ValueError, 'No safe rendered SVG'): self.accept(fixture)

    def test_archive_reference_and_hash_are_required_at_acceptance(self):
        for mode in ('missing-reference', 'unknown-reference', 'not-pdf', 'duplicate-reference', 'changed-bytes', 'missing-file'):
            with self.subTest(mode=mode):
                fixture = self.fixture(); delivery = api.read(fixture['delivery'])
                if mode == 'missing-reference': delivery.pop('archive_pdf_artifact_id')
                elif mode == 'unknown-reference': delivery['archive_pdf_artifact_id'] = 'missing'
                elif mode == 'not-pdf': delivery['archive_pdf_artifact_id'] = 'svg-1'
                elif mode == 'duplicate-reference': delivery['artifacts'].append(dict(delivery['artifacts'][-1]))
                elif mode == 'missing-file': fixture['pdf'].unlink()
                else: fixture['pdf'].write_bytes(b'Tampered mock archive bytes.')
                api.save(fixture['delivery'], delivery)
                with self.assertRaises((ValueError, OSError)): self.accept(fixture)

    def test_archive_path_cannot_escape_delivery_directory(self):
        fixture = self.fixture(); delivery = api.read(fixture['delivery'])
        outside = fixture['directory'] / 'outside.pdf'; outside.write_bytes(b'Outside mock archive.')
        delivery['artifacts'][-1].update(path='../outside.pdf', sha256=api.sha(outside))
        api.save(fixture['delivery'], delivery)
        with self.assertRaises(ValueError): self.accept(fixture)

    def test_readback_rejects_variant_and_archive_tampering(self):
        fixture = self.fixture(); result = self.accept(fixture); block = result['blocks'][0]
        for variant_id in (None, '', 'variant-2'):
            with self.subTest(variant_id=variant_id):
                with self.assertRaisesRegex(ValueError, 'variant differs'):
                    api.read_generated({**block, 'variant_id': variant_id})
        fixture['pdf'].write_bytes(b'Changed mock archive after acceptance.')
        with self.assertRaisesRegex(ValueError, 'PDF archive changed'): api.read_generated(block)
        fixture = self.fixture(); result = self.accept(fixture)
        receipt = api.read(result['receipt']); receipt.pop('archive_pdf'); api.save(result['receipt'], receipt)
        with self.assertRaisesRegex(ValueError, 'PDF archive changed'): api.read_generated(result['blocks'][0])
        fixture = self.fixture(); result = self.accept(fixture); fixture['pdf'].unlink()
        with self.assertRaises((ValueError, OSError)): api.read_generated(result['blocks'][0])

    def test_readback_rejects_every_bound_evidence_file_tamper(self):
        for index in range(5):
            with self.subTest(binding=index):
                fixture = self.fixture(); result = self.accept(fixture)
                receipt = api.read(result['receipt'])
                Path(receipt['bindings'][index]['path']).write_text('changed synthetic evidence')
                with self.assertRaisesRegex(ValueError, 'evidence changed'):
                    api.read_generated(result['blocks'][0])

    def test_readback_rejects_dependency_and_receipt_mismatch(self):
        for replacement in ({'schema_version': 99}, {'status': 'approved'}, {'dependency': {}}, {'bindings': []},
                            {'theme_policy': 'exact_colors'}, {'selected_variant_id': None}, {'archive_pdf': {}}):
            with self.subTest(replacement=replacement):
                fixture = self.fixture(); result = self.accept(fixture)
                receipt = api.read(result['receipt']); receipt.update(replacement); api.save(result['receipt'], receipt)
                with self.assertRaises(ValueError): api.read_generated(result['blocks'][0])

    def test_delivery_blocks_keep_absolute_path_and_alt_requirements(self):
        fixture = self.fixture(); result = self.accept(fixture); block = result['blocks'][0]
        for replacement in ({'path': 'relative.svg'}, {'delivery_receipt': 'relative.json'}, {'alt': ''}, {'alt': ' '}, {'alt': None}):
            with self.subTest(replacement=replacement):
                with self.assertRaises(ValueError): api.read_generated({**block, **replacement})

    def test_readback_rejects_malformed_artifact_field_types(self):
        for replacement in ({'path': None}, {'path': {}}, {'path': 3}, {'sha256': None}):
            with self.subTest(replacement=replacement):
                fixture = self.fixture(); result = self.accept(fixture)
                receipt = api.read(result['receipt']); receipt['artifacts'][0].update(replacement)
                api.save(result['receipt'], receipt)
                with self.assertRaises(ValueError): api.read_generated(result['blocks'][0])

    def test_main_cli_only_delegates_high_level_operations(self):
        request = {'synthetic_fixture': 'Not a real design or accepted delivery.'}
        source = self.path / 'cli-request.json'; api.save(source, request)
        for operation, method in (('diagram-brief', 'prepare_brief'), ('diagram-accept', 'accept_delivery')):
            with self.subTest(operation=operation):
                output = self.path / operation
                result = {'status': 'synthetic_mock_only'}
                stdout = io.StringIO()
                with patch.object(api, method, return_value=result) as adapter, \
                        patch.object(sys, 'argv', ['ppt.py', operation, str(source), str(output)]), \
                        redirect_stdout(stdout):
                    code = ppt.main()
                self.assertEqual(code, 0)
                adapter.assert_called_once_with(request, str(output))
                self.assertEqual(json.loads(stdout.getvalue()), result)
                self.assertFalse(output.exists())

    def tool_fixture(self):
        directory = self.next_directory(); root = directory / 'dependency'
        tools = root / 'tools'; tools.mkdir(parents=True)
        script = tools / 'prepare_diagram_brief.py'
        script.write_text('# Synthetic fixture. This file must never be executed.\n')
        output = directory / 'output'; output.mkdir()
        return root, script, output

    def test_execute_calls_only_tracked_tool_and_preserves_local_log(self):
        root, script, output = self.tool_fixture()
        completed = [subprocess.CompletedProcess([], 0, 'tools/' + script.name, ''),
                     subprocess.CompletedProcess([], 0, 'synthetic stdout', 'synthetic stderr')]
        with patch.dict('os.environ', {'PYTHONPATH': '/untrusted', 'PYTHONHOME': '/untrusted'}), \
                patch.object(workflow.subprocess, 'run', side_effect=completed) as run:
            workflow.execute(api, root, script.name, ['--input', 'fixture.json'], output)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0][:3], ['git', '-C', str(root)])
        self.assertEqual(run.call_args_list[1].args[0][:2], [sys.executable, str(script)])
        env = run.call_args_list[1].kwargs['env']
        self.assertNotIn('PYTHONPATH', env); self.assertNotIn('PYTHONHOME', env)
        self.assertEqual(env['PYTHONDONTWRITEBYTECODE'], '1')
        self.assertIn('synthetic stderr', (output / (script.name + '.log')).read_text())

    def test_execute_rejects_untracked_tool_without_running_it(self):
        root, script, output = self.tool_fixture()
        with patch.object(workflow.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'untracked')) as run:
            with self.assertRaises(ValueError): workflow.execute(api, root, script.name, [], output)
        self.assertEqual(run.call_count, 1)

    def test_execute_git_and_tool_failures_have_clean_error_boundary(self):
        for failure in (OSError('synthetic unavailable git'), subprocess.TimeoutExpired('git', 15)):
            with self.subTest(failure=type(failure).__name__):
                root, script, output = self.tool_fixture()
                with patch.object(workflow.subprocess, 'run', side_effect=failure):
                    with self.assertRaises(ValueError): workflow.execute(api, root, script.name, [], output)
        root, script, output = self.tool_fixture()
        with patch.object(workflow.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, '', ''),
                          subprocess.TimeoutExpired('synthetic drawing tool', 60)]):
            with self.assertRaises(ValueError): workflow.execute(api, root, script.name, [], output)

    def test_execute_nonzero_contract_result_keeps_diagnostics(self):
        root, script, output = self.tool_fixture()
        with patch.object(workflow.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, '', ''),
                          subprocess.CompletedProcess([], 2, 'synthetic rejection', 'reason')]):
            with self.assertRaises(ValueError): workflow.execute(api, root, script.name, [], output)
        self.assertIn('synthetic rejection', (output / (script.name + '.log')).read_text())


if __name__ == '__main__':
    unittest.main()
