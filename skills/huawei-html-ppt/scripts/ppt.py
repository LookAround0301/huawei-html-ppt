"""Local presentation API. No network, model runner, or material code execution."""
from pathlib import Path
from contextlib import contextmanager
import argparse
import copy
import hashlib
import json
import math
import os
import re
import sys
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
import route_request
import render_style_deck
import diagram_audit
import source_images
import diagram_adapter


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def filehash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, path)
    finally:
        if temp.exists(): temp.unlink()


def state_path(value):
    if not value: raise ValueError('state_dir is required for feedback operations')
    path = Path(value).resolve()
    if path == ROOT or ROOT in path.parents: raise ValueError('Keep state outside the skill package')
    return path / 'state.json'


def seed():
    return read(ROOT / 'knowledge/units.json')['units']


def load_state(value=None):
    base = seed()
    value = value or (Path.cwd() / '.ppt-skill/state')
    if value and state_path(value).exists():
        data = read(state_path(value))
        if data['seed_hash'] != digest(base):
            raise ValueError('Installed seed changed; migrate/review state before reuse')
        return data
    return {'version': 1, 'seed_hash': digest(base), 'units': base, 'candidates': {}, 'events': []}


@contextmanager
def mutate(value):
    path = state_path(value); path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError('State is busy; inspect the existing lock before retrying')
    try:
        os.close(fd); data = load_state(value); yield data; save(path, data)
    finally:
        lock.unlink(missing_ok=True)


def applicable(unit, style, context):
    return style in unit['styles'] and all(context.get(k) == v for k, v in unit.get('when', {}).items())


def plan(request, units=None):
    request = copy.deepcopy(request)
    deck = request.get('deck', {})
    if deck.get('style'):
        if request.get('style') and route_request.choose(request['style']) != deck['style']:
            raise ValueError('Request style conflicts with deck.style')
        request.setdefault('style', deck['style'])
    result = route_request.from_request(request)
    if not result['style']: return {'route': result, 'units': [], 'components': []}
    units = units if units is not None else load_state(request.get('state_dir'))['units']
    context = request.get('context', {})
    active = [u for u in units if applicable(u, result['style'], context)]
    catalog = read(ROOT / 'assets/units/catalog.json')
    return {'route': result, 'units': active,
            'unit_refs': [f"{u['id']}@{u['revision']}" for u in active],
            'components': [u for u in catalog['units'] if result['style'] in u['styles']],
            'diagram_tools': diagram_adapter.tool_contract(),
            'component_builders': [u for u in read(ROOT / 'assets/components/catalog.json')['components'] if result['style'] in u['styles']]}


def resolved_deck(request, planning):
    if not planning['route']['style']: raise ValueError('Presentation purpose needs context')
    deck = copy.deepcopy(request.get('deck'))
    if not deck: raise ValueError('render requires a structured deck; the host writes content using plan guidance')
    deck['style'] = planning['route']['style']
    for slide in deck.get('slides', []):
        if slide.get('layout'): continue
        preferred = [u['rule']['preferred_layout'] for u in planning['units'] if u['rule'].get('preferred_layout')]
        if preferred: slide['layout'] = preferred[-1]
        elif deck['style'] == 'insight-analysis':
            slide['layout'] = {'overview': 'insight-backbone-callouts', 'zoom': 'insight-overview-zoom',
                               'evidence': 'insight-evidence'}.get(slide.get('page_kind'), 'insight-mechanism')
        else:
            slide['layout'] = {'portfolio': 'project-portfolio', 'landscape': 'project-landscape',
                               'coordination': 'project-coordination', 'appendix': 'project-explainer',
                               'figure-overview': 'project-figure-overview',
                               'figure-evidence': 'project-figure-evidence',
                               'figure-full': 'project-figure-full',
                               'proposal': 'project-solution'}.get(slide.get('page_kind'), 'project-progress')
    deck['generation'] = {'api_version': 1, 'style': deck['style'], 'unit_refs': planning['unit_refs']}
    return deck


def diagrams(slide):
    for p in slide.get('panels', []):
        for b in p.get('blocks', []):
            if b.get('type') == 'diagram': yield b['data']
    for t in slide.get('topics', []):
        if 'diagram' in t: yield t['diagram']


def validate(deck):
    errors, warnings = [], []
    try: diagram_adapter.theme(deck.get('theme'))
    except ValueError as exc: errors.append(str(exc))
    title = deck.get('title', '')
    if not title or title.strip() in ('.', '..') or re.search(r'[\\/:*?"<>|\x00-\x1f]', title):
        errors.append('title must be a safe nonempty filename')
    catalog = read(ROOT / 'assets/two-style/layouts.json')['layouts']
    style = deck.get('style'); slides = deck.get('slides', [])
    if style not in route_request.STYLES: errors.append('Unknown style')
    if not slides: errors.append('No slides')
    for n, s in enumerate(slides, 1):
        prefix = f'slide {n}: '
        layout = s.get('layout')
        if layout not in catalog or catalog[layout]['style'] != style:
            errors.append(prefix + 'layout does not match style'); continue
        if not s.get('title'): errors.append(prefix + 'missing title')
        formal = catalog[layout].get('class') == 'project-report'
        if style == 'insight-analysis' and not s.get('conclusion'): errors.append(prefix + 'missing explicit conclusion')
        if not formal:
            if style == 'technical-project' and (s.get('labels', catalog[layout].get('header')) not in [['挑战', '目标'], ['目标', '进展']] or len(s.get('summary', [])) != 2):
                errors.append(prefix + 'single-topic project requires paired summary')
            panels = s.get('panels', [])
            if not panels: errors.append(prefix + 'no content panels')
            if layout in ('project-figure-overview', 'project-figure-evidence', 'project-figure-full'):
                expected = 1 if layout == 'project-figure-full' else 2
                if len(panels) != expected: errors.append(prefix + f'{layout} needs {expected} panels')
                if not any(b.get('type') == 'image' for p in panels for b in p.get('blocks', [])):
                    errors.append(prefix + 'source-figure layout needs a local image')
            for p in panels:
                if 'title' not in p: errors.append(prefix + 'panel needs title')
                for b in p.get('blocks', []):
                    kind = b.get('type')
                    if kind not in ('text', 'heading', 'bullets', 'table', 'diagram', 'chart', 'image', 'generated-diagram'): errors.append(prefix + 'unsupported block')
                    if kind == 'generated-diagram':
                        try: diagram_adapter.read_generated(b, diagram_adapter.theme(deck.get('theme')))
                        except (ValueError, OSError) as exc: errors.append(prefix + str(exc))
                    if kind == 'image':
                        try: source_images.read_image(b)
                        except (ValueError, OSError) as exc: errors.append(prefix + str(exc))
                    if kind == 'table':
                        width = len(b.get('headers', []))
                        if not width or any(len(r) != width for r in b.get('rows', [])): errors.append(prefix + 'table dimensions differ')
                    if kind == 'chart':
                        d = b.get('data', {}); series = d.get('series', []); xs = d.get('x', [])
                        if d.get('kind') not in ('line', 'bar') or not 1 <= len(series) <= 3 or not xs:
                            errors.append(prefix + 'chart must be a simple line/bar with 1-3 series')
                        if d.get('kind') == 'line' and len(xs)>1 and all(isinstance(x,(int,float)) for x in xs):
                            if any(not math.isfinite(x) for x in xs) or any(a>=b for a,b in zip(xs,xs[1:])):
                                errors.append(prefix + 'numeric line-chart x values must be finite and strictly increasing')
                        for v in series:
                            values = v.get('values', [])
                            if len(values) != len(xs) or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in values):
                                errors.append(prefix + 'chart values must be finite and align with labels')
                        if any(x < 0 for v in series for x in v.get('values', []) if isinstance(x, (int, float))):
                            errors.append(prefix + 'negative chart values require a different renderer')
        elif layout == 'project-portfolio':
            if not s.get('targets') or not s.get('milestones') or not s.get('topics'): errors.append(prefix + 'portfolio needs targets, milestones and topics')
            for t in s.get('topics', []):
                if not t.get('summary') or not 1 <= len(t.get('progress_columns', [])) <= 3: errors.append(prefix + 'topic needs summary and 1-3 progress columns')
                if ('image' in t) == ('diagram' in t): errors.append(prefix + 'topic needs exactly one image or diagram')
                if 'image' in t:
                    try: source_images.read_image(t['image'])
                    except (ValueError, OSError) as exc: errors.append(prefix + str(exc))
        elif layout == 'project-landscape' and not s.get('projects'): errors.append(prefix + 'missing projects')
        elif layout == 'project-coordination' and not s.get('stages'): errors.append(prefix + 'missing stages')
        elif layout == 'project-explainer' and any(len(r) != 3 for r in s.get('rows', [])): errors.append(prefix + 'explainer has three columns')
        for d in diagrams(s):
            if d.get('width', 0) <= 0 or d.get('height', 0) <= 0: errors.append(prefix + 'invalid diagram dimensions')
            for e in d.get('elements', []):
                if e.get('type') not in ('rect', 'ellipse', 'line', 'polygon', 'text'): errors.append(prefix + 'unsupported diagram element')
                if e.get('type') == 'text' and not e.get('text', '').strip(): errors.append(prefix + 'empty diagram label')
            if d.get('acceptance') or deck.get('diagram_contract') == 1:
                checked = diagram_audit.audit(d, required=deck.get('diagram_contract') == 1)
                errors.extend(prefix + value for value in checked['errors'])
                warnings.extend(prefix + value for value in checked['warnings'])
        if len(s.get('title', '')) > 60: warnings.append(prefix + 'check title wrapping visually')
    return {'ok': not errors, 'errors': errors, 'warnings': warnings, 'visual_review_required': True}


def render(request, output, units=None):
    planning = plan(request, units); deck = resolved_deck(request, planning); result = validate(deck)
    if not result['ok']: raise ValueError('; '.join(result['errors']))
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=True)
    html = render_style_deck.render(deck, output)
    save(output / 'diagram-audit.json', diagram_audit.deck_audit(deck))
    save(output / 'plan.json', planning); save(output / 'validation.json', result)
    return {'html': html, 'deck': str(output / 'deck-model.json'), 'plan': str(output / 'plan.json'), 'validation': result}


def check_unit(unit, base_revision):
    if not re.fullmatch(r'[a-z][a-z0-9.-]{2,80}', unit.get('id', '')): raise ValueError('Invalid unit id')
    if unit.get('revision') != base_revision + 1: raise ValueError('revision must increase by one')
    if unit.get('kind') not in ('preference', 'layout', 'diagram', 'content'): raise ValueError('Unknown unit kind')
    if not unit.get('styles') or not set(unit['styles']) <= set(route_request.STYLES): raise ValueError('Invalid style scope')
    if not isinstance(unit.get('when', {}), dict): raise ValueError('when must be an exact-match context object')
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in unit.get('when', {}).items()): raise ValueError('when values must be strings')
    rule = unit.get('rule', {})
    if not rule or set(rule) - {'guidance', 'preferred_layout', 'preferred_chart'}: raise ValueError('Only declarative rules are supported')
    if not isinstance(rule.get('guidance'), str) or not rule['guidance'].strip(): raise ValueError('Explain the rule')
    if rule.get('preferred_layout'):
        layout = read(ROOT / 'assets/two-style/layouts.json')['layouts'].get(rule['preferred_layout'])
        if not layout or set(unit['styles']) != {layout['style']}: raise ValueError('Preferred layout must match the scoped style')
    if rule.get('preferred_chart') and rule['preferred_chart'] not in ('line', 'bar', 'table', 'structure'): raise ValueError('Unknown preferred chart')


def evidence_snapshot(items):
    if not items: raise ValueError('Feedback needs traceable evidence')
    output = []
    for item in items:
        if item.get('kind') == 'user-feedback' and item.get('text', '').strip():
            output.append(copy.deepcopy(item))
        elif item.get('kind') == 'local-artifact':
            p = Path(item['path']).resolve()
            output.append({'kind': 'local-artifact', 'path': str(p), 'sha256': filehash(p)})
        else: raise ValueError('Evidence must be actual user feedback or a local artifact')
    return output


def feedback(req):
    if req.get('task_state') not in ('completed', 'verified_milestone'): raise ValueError('Distill only a verified milestone or completed task')
    unit = copy.deepcopy(req['unit']); base = req['base_revision']; check_unit(unit, base)
    evidence = evidence_snapshot(req.get('evidence', []))
    with mutate(req['state_dir']) as state:
        old = next((u for u in state['units'] if u['id'] == unit['id']), None)
        if (old['revision'] if old else 0) != base: raise ValueError('Base revision changed')
        if not old and any(u['rule'] == unit['rule'] and u['styles'] == unit['styles'] and u.get('when', {}) == unit.get('when', {}) for u in state['units']):
            raise ValueError('Equivalent rule exists; revise that unit instead')
        unit['provenance'] = unit.get('provenance', []) + evidence
        candidate_id = uuid.uuid4().hex[:16]
        state['candidates'][candidate_id] = {'unit': unit, 'base_revision': base, 'state': 'candidate', 'evidence': evidence}
    return {'candidate_id': candidate_id, 'state': 'candidate', 'unit_ref': f"{unit['id']}@{unit['revision']}"}


def candidate_units(state, c):
    return [u for u in state['units'] if u['id'] != c['unit']['id']] + [c['unit']]


def evaluate(req):
    state = load_state(req['state_dir']); c = state['candidates'][req['candidate_id']]
    if c['state'] == 'promoted': raise ValueError('Candidate already promoted')
    cases = req.get('cases', [])
    if not cases: raise ValueError('Provide an applicable replay case')
    output = Path(req['output_dir']).resolve()
    if output == ROOT or ROOT in output.parents: raise ValueError('Evaluation output must be outside the core skill')
    results, covered = [], set()
    for n, path in enumerate(cases, 1):
        request = read(path); planning = plan(request, candidate_units(state, c))
        if not applicable(c['unit'], planning['route']['style'], request.get('context', {})): raise ValueError('Replay case is outside candidate scope')
        result = render(request, output / f'case-{n:02d}', candidate_units(state, c))
        files = list((output / f'case-{n:02d}').rglob('*'))
        result['files'] = {str(p): filehash(p) for p in files if p.is_file()}
        result['input'] = {'path': str(Path(path).resolve()), 'sha256': filehash(path)}
        results.append(result); covered.add(planning['route']['style'])
    with mutate(req['state_dir']) as latest:
        current = latest['candidates'][req['candidate_id']]
        if digest(current['unit']) != digest(c['unit']): raise ValueError('Candidate changed during evaluation')
        current.update(state='evaluated', evaluation={'cases': results, 'covered_styles': sorted(covered), 'unit_hash': digest(c['unit'])})
        current.pop('review', None)
    return {'candidate_id': req['candidate_id'], 'state': 'evaluated', 'cases': results, 'visual_review_required': True}


def check_evaluation(c):
    ev = c.get('evaluation')
    if not ev or ev['unit_hash'] != digest(c['unit']): raise ValueError('Evaluate this candidate first')
    if set(ev['covered_styles']) != set(c['unit']['styles']): raise ValueError('Replay must cover all scoped styles')
    for case in ev['cases']:
        for path, expected in case['files'].items():
            if filehash(path) != expected: raise ValueError('Replay artifact changed; evaluate again')
        if filehash(case['input']['path']) != case['input']['sha256']: raise ValueError('Replay input changed')
    for item in c['evidence']:
        if item['kind'] == 'local-artifact' and filehash(item['path']) != item['sha256']: raise ValueError('Source evidence changed')


def review(req):
    if req.get('reviewer') not in ('agent', 'user') or req.get('result') not in ('pass', 'fail') or not req.get('rationale', '').strip():
        raise ValueError('Record actual reviewer, result and rationale')
    if req['result'] == 'pass' and req.get('visual_checked') is not True: raise ValueError('A passing replay needs actual visual review')
    with mutate(req['state_dir']) as state:
        c = state['candidates'][req['candidate_id']]; check_evaluation(c)
        if c['state'] == 'promoted': raise ValueError('Candidate already promoted')
        c['review'] = {k: req[k] for k in ('reviewer', 'result', 'visual_checked', 'rationale')}
        c['state'] = 'reviewed'
    return {'candidate_id': req['candidate_id'], 'state': 'reviewed', 'result': req['result']}


def promote(req):
    with mutate(req['state_dir']) as state:
        c = state['candidates'][req['candidate_id']]; check_evaluation(c)
        if c['state'] != 'reviewed' or c.get('review', {}).get('result') != 'pass': raise ValueError('A passing review is required')
        old = next((u for u in state['units'] if u['id'] == c['unit']['id']), None)
        if (old['revision'] if old else 0) != c['base_revision']: raise ValueError('Base revision changed; revise and replay')
        before = copy.deepcopy(state['units']); state['units'] = candidate_units(state, c)
        event = {'id': uuid.uuid4().hex[:16], 'kind': 'promote', 'candidate_id': req['candidate_id'],
                 'before': before, 'after_hash': digest(state['units'])}
        state['events'].append(event); c['state'] = 'promoted'
    return {'event_id': event['id'], 'state': 'promoted', 'unit_ref': f"{c['unit']['id']}@{c['unit']['revision']}"}


def rollback(req):
    with mutate(req['state_dir']) as state:
        if not state['events']: raise ValueError('No event to roll back')
        event = state['events'][-1]
        if event['kind'] != 'promote' or event['id'] != req['event_id'] or digest(state['units']) != event['after_hash']:
            raise ValueError('Only the current last promotion can be rolled back')
        state['units'] = event['before']
        state['events'].append({'id': uuid.uuid4().hex[:16], 'kind': 'rollback', 'target': event['id']})
        state['candidates'][event['candidate_id']]['state'] = 'rolled-back'
    return {'rolled_back': event['id']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['route', 'plan', 'render', 'validate', 'catalog', 'feedback', 'evaluate', 'review', 'promote', 'rollback', 'diagram-plan', 'diagram-render', 'diagram-brief', 'diagram-accept', 'diagram-doctor'])
    parser.add_argument('input', nargs='?'); parser.add_argument('output', nargs='?')
    args = parser.parse_args()
    try:
        req = read(args.input) if args.input else {}
        operations = {'route': route_request.from_request, 'plan': plan, 'validate': validate, 'diagram-plan': diagram_adapter.plan, 'diagram-doctor': diagram_adapter.preflight,
                      'feedback': feedback, 'evaluate': evaluate, 'review': review, 'promote': promote, 'rollback': rollback}
        if args.operation == 'catalog': result = read(ROOT / 'assets/units/catalog.json')
        elif args.operation in ('diagram-brief','diagram-accept'):
            if not args.output: raise ValueError(args.operation+' requires output directory')
            result = (diagram_adapter.prepare_brief if args.operation=='diagram-brief' else diagram_adapter.accept_delivery)(req,args.output)
        elif args.operation == 'diagram-render':
            if not args.output: raise ValueError('diagram-render requires output directory')
            result = diagram_adapter.render(req, args.output)
        elif args.operation == 'render':
            if not args.output: raise ValueError('render requires output directory')
            result = render(req, args.output)
        else: result = operations[args.operation](req)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.operation == 'validate' and not result['ok']: return 1
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'error': str(exc), 'operation': args.operation}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
