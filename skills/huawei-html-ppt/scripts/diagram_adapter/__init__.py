"""Optional, local tool adapter for pinned infra-io-generator. Never installs dependencies."""
from pathlib import Path
import base64
import copy
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

LOCK = json.loads((Path(__file__).parent/'dependency-lock.json').read_text())
if LOCK.get('adapter_api') != 1 or not re.fullmatch(r'[0-9a-f]{40}', LOCK.get('commit','')):
    raise ValueError('Invalid diagram adapter dependency lock')
PIN = LOCK['commit']
REPOSITORY = LOCK['repository']
DEFAULT_THEME = dict(accent='#C00000', text='#1D1D1A', muted='#666666',
                     background='#FFFFFF', panel='#F2F4F6', line='#AEB8C0')
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')


def tool_contract():
    """Stable host-facing discovery; dependency details remain inside the adapter."""
    return {'api_version':1, 'brief':'diagram-brief', 'accept':'diagram-accept', 'doctor':'diagram-doctor',
            'plan':'diagram-plan', 'render':'diagram-render', 'low_level_only':['diagram-plan','diagram-render'],
            'generation_runtime':'independent_agent_required',
            'intents':['model','report','mixed'], 'low_level_default_palette':'huawei-plain',
            'high_level_theme_policy':'Drawing agent interprets host theme without flattening all functional fills',
            'language_profile':LOCK['language_profile'],
            'dependency':dict(LOCK)}


def preflight(req):
    from .doctor import inspect
    return inspect(sys.modules[__name__],req)


def prepare_brief(req, output):
    from . import workflow
    return workflow.prepare(sys.modules[__name__],req,output)


def accept_delivery(req, output):
    from . import workflow
    return workflow.accept(sys.modules[__name__],req,output)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def theme(value=None):
    if value is not None and (not isinstance(value, dict) or set(value)-set(DEFAULT_THEME)):
        raise ValueError('Unknown theme token')
    result = dict(DEFAULT_THEME, **(value or {}))
    if any(not isinstance(v, str) or not HEX.fullmatch(v) for v in result.values()):
        raise ValueError('Theme colors must be six-digit hex')
    return {k: v.upper() for k, v in result.items()}


def theme_css(value=None):
    t = theme(value)
    return ':root{' + ';'.join('--'+k+':'+v for k,v in {
        'brand':t['accent'], 'ink':t['text'], 'muted':t['muted'],
        'line':t['line'], 'panel':t['panel'], 'pr-red':t['accent'], 'pr-ink':t['text'],
        'pr-gray':t['muted'], 'pr-line':t['line'], 'pr-panel':t['panel']}.items()) + '}\n.slide,.project-report.slide,.frame h2,.project-report .corner-frame>h2{background:'+t['background']+'}'


def plan(req, resolve_guidance=True):
    if not isinstance(req,dict): raise ValueError('Diagram request must be an object')
    intent = req.get('intent')
    if intent not in ('model', 'report'):
        raise ValueError('Choose explicit intent=model|report after semantic review; split mixed requests')
    palette = req.get('palette', 'huawei-plain')
    if palette not in ('huawei-plain','blue-neutral','paper-clear','paper-vivid'):
        raise ValueError('Unknown explicit palette')
    backend=req.get('model_backend','drawio')
    if backend not in ('drawio','tikz'): raise ValueError('Unknown explicit model_backend')
    if intent=='report' and 'model_backend' in req: raise ValueError('model_backend applies only to model intent')
    language_profile=req.get('language_profile',LOCK['language_profile'])
    if language_profile!=LOCK['language_profile']: raise ValueError('Unsupported language_profile for this integration lock')
    result = {'schema_version':1, 'language_profile':language_profile, 'model_backend':backend if intent=='model' else None, 'intent':intent, 'target':'ppt', 'palette':palette,
            'theme':theme(req.get('theme')), 'package':('technical-architecture-diagrams' if intent=='model' else 'technical-diagram-options'),
            'dependency':{'repository':REPOSITORY,'commit':PIN},
            'required_inputs':((['input: uncompressed drawio', 'color_map: cell/property to token']+(['chrome: executable'] if backend=='drawio' else ['tex: reviewed native source', 'tex_manifest: source/theme review binding', 'trusted_tex: true'])) if intent=='model'
                               else ['input: authored diagram IR', 'task: relational task JSON']),
            'status':'planned_not_rendered', 'authoring_required':True,
            'guidance':'Read the selected Skill; author source-backed geometry first. This tool does not infer model facts.'}
    if resolve_guidance and (req.get('infra_root') or os.environ.get('INFRA_IO_ROOT')):
        root=dependency(req)
        script=root/'skills/technical-architecture-diagrams/scripts/route_request.py'
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
        try:
            done=subprocess.run([sys.executable,str(script),'--request',req.get('request','PPT diagram'),'--intent',intent,'--target','ppt','--palette',palette],check=True,capture_output=True,text=True,timeout=30,env=env)
        except (subprocess.SubprocessError,OSError) as exc:
            raise ValueError('Drawing Skill route unavailable; no layout preference inferred') from exc
        result['layout_preferences']=route_layout_preferences(json.loads(done.stdout))
        result['layout_guidance_status']='from_pinned_skill'
    else:
        result['layout_guidance_status']='requires_pinned_dependency'
    return result


def route_layout_preferences(route):
    if not isinstance(route,dict) or not isinstance(route.get('parts'),list) or not route['parts']: raise ValueError('Invalid drawing Skill route contract')
    preferences=[]
    for part in route['parts']:
        if not isinstance(part,dict) or not isinstance(part.get('layout_preference'),dict): raise ValueError('Drawing Skill route has no layout preference')
        preferences.append(part['layout_preference'])
    return preferences


def dependency(req):
    value = req.get('infra_root') or os.environ.get('INFRA_IO_ROOT')
    if not value: raise ValueError('Set infra_root or INFRA_IO_ROOT to the pinned local checkout; see diagram-integration.md')
    root = Path(value).resolve()
    try:
        actual = subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],check=True,capture_output=True,text=True,timeout=15).stdout.strip()
        changed = subprocess.run(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],check=True,capture_output=True,text=True,timeout=15).stdout
    except (subprocess.SubprocessError, OSError) as exc:
        raise ValueError('Dependency must be a readable pinned Git checkout') from exc
    if actual != PIN or changed.strip(): raise ValueError('Dependency revision mismatch or tracked modifications; use a clean pinned checkout')
    tracked=set(subprocess.run(['git','-C',str(root),'ls-files'],check=True,capture_output=True,text=True,timeout=15).stdout.splitlines())
    for directory in ('skills','tools'):
        for file in (root/directory).rglob('*.py'):
            if file.relative_to(root).as_posix() not in tracked:
                raise ValueError('Untracked Python modules in dependency execution directories are not allowed')
    if req.get('model_backend')=='tikz':
        wrapper='tools/render_model_tikz.py'
        if wrapper not in tracked or not (root/wrapper).is_file():
            raise ValueError('Pinned dependency does not provide the tracked TikZ backend; upgrade the verified pin')
    for relative in ('skills/technical-architecture-diagrams/SKILL.md','skills/technical-diagram-options/SKILL.md'):
        if not (root/relative).is_file(): raise ValueError('Both sibling diagram Skills are required')
    if not (root/'skills/technical-architecture-diagrams/scripts/check_language.py').is_file():
        raise ValueError('Pinned dependency has no shared language checker; upgrade to the verified language-policy revision')
    return root


def input_path(req, key):
    value = req.get(key)
    if not isinstance(value,str) or not Path(value).is_file(): raise ValueError(key+' must name an existing local file')
    return Path(value).resolve()


def palette_overrides(req, chosen):
    # Default PPT theme wins over preset defaults. Explicit palette retains its semantic fills.
    t=chosen['theme']
    result={'text':{'primary':t['text'],'secondary':t['muted']},
            'background':{'canvas':t['background'],'panel':t['panel']},
            'line':{'default':t['line'],'strong':t['text']},'accent':{'primary':t['accent']}}
    if chosen['palette']=='huawei-plain':
        for role in ('compute','state','communication','rank0','rank1'):
            result[role]={'fill':t['panel'],'stroke':t['line']}
    custom=req.get('custom_tokens',{})
    if not isinstance(custom,dict): raise ValueError('custom_tokens must be an object')
    for group, values in custom.items():
        if not isinstance(values,dict): raise ValueError('custom token groups must be objects')
        result.setdefault(group,{}).update(values)
    return result


def report_palette(doc,tokens):
    if not isinstance(doc,dict): raise ValueError('Diagram IR must be an object')
    doc=copy.deepcopy(doc)
    for v in doc.get('views',[]):
        v['canvas']['background']=tokens['background']['canvas']
        for g in v.get('glyphs',[]):
            role=g.get('palette_role','compute')
            if role not in ('compute','state','communication','rank0','rank1','panel','accent','text'):
                raise ValueError('Unknown glyph palette_role: '+str(role))
            style=g.setdefault('style',{})
            if role in ('panel','text'):
                fill=tokens['background']['panel'] if role=='panel' else 'none'; stroke=tokens['line']['default'] if role=='panel' else 'none'
            elif role=='accent': fill=tokens['background']['panel']; stroke=tokens['accent']['primary']
            else: fill=tokens[role]['fill']; stroke=tokens[role]['stroke']
            style.update(fill=fill,stroke=stroke,text_color=tokens['text']['primary'])
        for p in v.get('paths',[]):
            role=p.get('palette_role','line')
            if role not in ('line','accent'): raise ValueError('Path palette_role must be line|accent')
            p.setdefault('style',{}).update(stroke=tokens['accent']['primary'] if role=='accent' else tokens['line']['strong'],text_color=tokens['text']['primary'])
    return doc


def render(req, output):
    chosen=plan(req, resolve_guidance=False); root=dependency(req); source=input_path(req,'input')
    output=Path(output).resolve()
    if output.exists() and any(output.iterdir()): raise ValueError('Use an empty output directory; preserve previous evidence')
    output.mkdir(parents=True,exist_ok=True)
    architecture=root/'skills/technical-architecture-diagrams'; report=root/'skills/technical-diagram-options'
    (output/('authored'+source.suffix.lower())).write_bytes(source.read_bytes())
    calls=[]
    evidence={'schema_version':2,'status':'running','intent':chosen['intent'],'package':chosen['package'],
              'dependency':chosen['dependency'],'palette':chosen['palette'],'theme':chosen['theme'],
              'target':'ppt','page':req.get('page',0),'model_backend':chosen['model_backend'],'language_profile':chosen['language_profile'],'input_sha256':sha(source),'calls':calls,'artifacts':[],'visual_qa':'not_performed'}
    def run(script, args, label, program=sys.executable):
        command=[program,str(script),*map(str,args)]
        record={'tool':str(script.relative_to(root)),'operation':label,'status':'running'}; calls.append(record)
        try:
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            env.pop('PYTHONPATH',None); env.pop('PYTHONHOME',None)
            done=subprocess.run(command,check=False,capture_output=True,text=True,timeout=180,env=env)
            record.update(returncode=done.returncode,status='ok' if done.returncode==0 else 'failed')
            # Full diagnostics stay in local output only; no automatic publishing.
            (output/(str(len(calls)).zfill(2)+'-'+label+'.log')).write_text(done.stdout+'\n'+done.stderr)
            if done.returncode: raise ValueError('Diagram tool failed: '+label+'; inspect local log')
            return done.stdout
        except (subprocess.SubprocessError,OSError) as exc:
            record['status']='failed'; raise ValueError('Diagram tool unavailable/timeout: '+label) from exc
    try:
        overrides=output/'theme-tokens.json'; save(overrides,palette_overrides(req,chosen))
        resolved=output/'palette.json'
        run(architecture/'scripts/resolve_palette.py',['--target','ppt','--palette',chosen['palette'],'--custom',overrides,'--output',resolved],'resolve-palette')
        run(architecture/'scripts/route_request.py',['--request',req.get('request','PPT diagram'),'--intent',chosen['intent'],'--target','ppt','--palette',chosen['palette'],'--custom',overrides,'--output',output/'route.json'],'route')
        evidence['layout_preferences']=route_layout_preferences(read(output/'route.json'))
        evidence['layout_decision']=req.get('layout_decision')
        evidence['layout_review']='not_automatically_evaluated'
        def language_check(prepared):
            qa_path=output/'language-qa.json'
            run(architecture/'scripts/check_language.py',['--input',prepared,'--format',chosen['intent'],'--profile',chosen['language_profile'],'--output',qa_path],'check-language')
            qa=checked_language_qa(qa_path,prepared,chosen['language_profile'])
            evidence['language_qa']={'path':qa_path.name,'sha256':sha(qa_path),'input_path':prepared.relative_to(output).as_posix(),'input_sha256':sha(prepared),'status':qa['status'],'contract_status':qa['contract_status'],'semantic_review':qa['semantic_review']}
        if chosen['intent']=='report':
            task=input_path(req,'task')
            run(report/'scripts/select_options.py',[task,'--out',output/'options.json'],'select-options')
            prepared=output/'prepared.diagram.json'
            authored=read(source)
            if not isinstance(authored,dict): raise ValueError('Diagram IR must be an object')
            if authored.get('language_profile',chosen['language_profile'])!=chosen['language_profile']:
                raise ValueError('Authored diagram language_profile differs from request')
            authored['language_profile']=chosen['language_profile']
            save(prepared,report_palette(authored,read(resolved)['tokens']))
            language_check(prepared)
            run(report/'scripts/diagram_tool.py',['check',prepared],'check-report')
            run(report/'scripts/diagram_tool.py',['render',prepared,'--out-dir',output/'artifacts'],'render-report')
            artifacts=list((output/'artifacts').glob('*.svg'))+list((output/'artifacts').glob('*.drawio'))+list((output/'artifacts').glob('*.source.json'))
        else:
            color_map=input_path(req,'color_map')
            (output/'color-map.json').write_bytes(color_map.read_bytes())
            if source.suffix.lower()!='.drawio': raise ValueError('model input must be native .drawio')
            checked_drawio(source)
            selected=output/'selected.drawio'
            select_model_page(source,selected,req.get('page',0),chosen['language_profile'])
            prepared=output/'model.drawio'
            run(architecture/'scripts/apply_palette.py',[selected,'--output',prepared,'--map',color_map,'--target','ppt','--palette',chosen['palette'],'--custom',overrides],'apply-model-palette')
            language_check(prepared)
            if chosen['model_backend']=='tikz':
                tex=input_path(req,'tex'); manifest_path=input_path(req,'tex_manifest')
                if req.get('trusted_tex') is not True: raise ValueError('TikZ requires explicit trusted_tex=true for reviewed task-authored source')
                manifest=checked_tex_manifest(read(manifest_path),source,tex,req,chosen,color_map)
                engine=req.get('tex_engine','xelatex')
                if engine not in ('pdflatex','xelatex'): raise ValueError('Unsupported TeX engine')
                timeout=req.get('tex_timeout',60)
                if not isinstance(timeout,int) or isinstance(timeout,bool) or not 1<=timeout<=180: raise ValueError('tex_timeout must be 1..180 seconds')
                save(output/'tex-source-review.json',manifest)
                run(root/'tools/render_model_tikz.py',['--input',tex,'--out-dir',output/'artifacts','--engine',engine,'--timeout',timeout,'--trusted-source'],'render-model-tikz')
                artifacts=[prepared,output/'artifacts/figure.tex',output/'artifacts/figure.pdf',output/'artifacts/figure.svg',output/'artifacts/figure.png',output/'artifacts/render-qa.json']
                evidence['tex_source_review']={'path':'tex-source-review.json','sha256':sha(output/'tex-source-review.json'),'source_tex_sha256':sha(tex),'status':'author_reviewed_not_automatic_equivalence'}
                evidence['editability']='Native TeX and drawio retained; exported SVG glyph outlines are not editable text'
            else:
                chrome=req.get('chrome') or os.environ.get('CHROME_BINARY')
                if not chrome or not Path(chrome).is_file(): raise ValueError('model renderer requires chrome or CHROME_BINARY')
                run(architecture/'scripts/drawio_runtime/export.mjs',['--input',prepared,'--out',output/'model.native','--graph-js',root/'third_party/drawio/app.min.js','--chrome',chrome,'--page','0'],'render-model',program='node')
                # Preserve native QA, then adapt the canvas in a distinct final SVG.
                svg_tree=ET.parse(output/'model.native.svg'); svg_root=svg_tree.getroot()
                for child in svg_root:
                    if child.tag.split('}')[-1]=='rect':
                        child.set('fill',read(resolved)['tokens']['background']['canvas']); break
                svg_tree.write(output/'model.svg',encoding='utf-8',xml_declaration=True)
                evidence['native_render']={'svg':'model.native.svg','runtime_qa':'model.native.runtime-qa.json', 'note':'Native output retained unchanged; model.svg applies only deck canvas background. Native PNG is not the adapted final image.'}
                artifacts=[prepared,output/'model.svg']
        for path in artifacts:
            if path.suffix=='.svg': checked_svg(path)
            evidence['artifacts'].append({'path':path.relative_to(output).as_posix(),'sha256':sha(path)})
        if not any(x['path'].endswith('.svg') for x in evidence['artifacts']): raise ValueError('No SVG produced')
        evidence['status']='rendered';save(output/'invocation.json',evidence)
        blocks=[{'type':'generated-diagram','path':str(output/x['path']),'invocation':str(output/'invocation.json'),
                 'alt':req.get('alt',req.get('request','Generated technical diagram'))} for x in evidence['artifacts'] if x['path'].endswith('.svg')]
        save(output/'blocks.json',blocks)
        return {'status':'rendered','invocation':str(output/'invocation.json'),'blocks':blocks,'language_qa':evidence['language_qa'],'visual_qa':'not_performed','layout_preferences':evidence['layout_preferences'],'layout_review':evidence['layout_review']}
    except Exception:
        evidence['status']='failed';save(output/'invocation.json',evidence);raise


def checked_tex_manifest(manifest, source, tex, request, chosen, color_map=None):
    if not isinstance(manifest,dict): raise ValueError('TeX source review must be an object')
    if color_map is not None and manifest.get('source_color_map_sha256')!=sha(color_map):
        raise ValueError('TeX/native color map binding mismatch')
    if manifest.get('source_master_sha256')!=sha(source) or manifest.get('native_tex_sha256')!=sha(tex):
        raise ValueError('TeX/native master source binding mismatch')
    if (manifest.get('language_profile')!=chosen['language_profile'] or manifest.get('theme_tokens')!=chosen['theme']
            or manifest.get('palette')!=chosen['palette'] or manifest.get('custom_tokens')!=request.get('custom_tokens',{})
            or manifest.get('page')!=request.get('page',0)):
        raise ValueError('TeX authoring theme/profile/page differs from the request')
    review=manifest.get('source_review')
    if not isinstance(review,dict) or review.get('reviewer') not in ('agent','user') or review.get('result')!='pass' or not isinstance(review.get('rationale'),str) or not review['rationale'].strip():
        raise ValueError('Reviewed TeX/master correspondence is required, not inferred from compilation')
    return manifest


def select_model_page(source, output, page, language_profile=None):
    if not isinstance(page,int) or isinstance(page,bool) or page<0: raise ValueError('page must be a nonnegative integer')
    root=ET.parse(source).getroot()
    models=list(root.iter('mxGraphModel'))
    if page>=len(models): raise ValueError('Model page out of range')
    if language_profile is not None:
        for element in (root,models[page]):
            if element.get('language_profile',language_profile)!=language_profile:
                raise ValueError('Authored model language_profile differs from request')
        models[page].set('language_profile',language_profile)
    ET.ElementTree(models[page]).write(output,encoding='utf-8',xml_declaration=True)


def checked_drawio(path):
    data=Path(path).read_bytes()
    try: text=data.decode('utf-8-sig')
    except UnicodeDecodeError as exc: raise ValueError('XML must be UTF-8') from exc
    if '\x00' in text: raise ValueError('XML must be UTF-8 without NUL')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper(): raise ValueError('XML entities are not allowed')
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper(): raise ValueError('Drawio entities are not allowed')
    try: root=ET.fromstring(data)
    except ET.ParseError as exc: raise ValueError('Invalid XML') from exc
    allowed={'mxfile','diagram','mxGraphModel','root','mxCell','mxGeometry','Array','mxPoint','object','UserObject'}
    for element in root.iter():
        if element.tag not in allowed: raise ValueError('Only native static drawio elements are supported')
        for key,value in element.attrib.items():
            if key.lower().startswith('on') or key.lower() in ('href','src','link'):
                raise ValueError('External/active drawio attributes are not supported')
            if key=='style' and re.search(r'image\s*=|url\(|shape=image',value,re.I):
                raise ValueError('External images are not supported in generated model diagrams')
            if key in ('value','label') and re.search(r'<[A-Za-z/!]',value):
                raise ValueError('Use plain labels, not HTML in model diagrams')
    if root.find('.//mxGraphModel') is None and root.tag!='mxGraphModel':
        raise ValueError('Use uncompressed drawio')
    return data


def checked_svg(path):
    data=Path(path).read_bytes()
    if len(data)>20*1024*1024: raise ValueError('SVG exceeds size limit')
    try: text=data.decode('utf-8-sig')
    except UnicodeDecodeError as exc: raise ValueError('SVG must be UTF-8') from exc
    if '\x00' in text: raise ValueError('SVG must be UTF-8 without NUL')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper(): raise ValueError('SVG entities are not allowed')
    if re.search(r'<\?(?!xml\s)',text,re.I): raise ValueError('SVG processing instructions are not allowed')
    if re.search(br'<\?(?!xml\s)',data,re.I): raise ValueError('SVG processing instructions are not allowed')
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper(): raise ValueError('SVG entities are not allowed')
    try: root=ET.fromstring(data)
    except ET.ParseError as exc: raise ValueError('Invalid XML') from exc
    if root.tag.split('}')[-1]!='svg': raise ValueError('Expected SVG')
    id_values=[element.get('id') for element in root.iter() if element.get('id')]
    if len(id_values)!=len(set(id_values)): raise ValueError('Duplicate SVG IDs are not supported')
    ids={element.get('id'):element for element in root.iter() if element.get('id')}
    for element in root.iter():
        tag=element.tag.split('}')[-1]
        if tag not in {'svg','g','rect','circle','ellipse','line','polyline','polygon','path','text','tspan','defs','marker','clipPath','title','desc','metadata','linearGradient','radialGradient','stop','symbol','use'}:
            raise ValueError('Unsupported active or external SVG element: '+tag)
        for key,value in element.attrib.items():
            key=key.split('}')[-1].lower()
            urls=re.findall(r'url\((.*?)\)',value,re.I|re.S)
            if '\\' in value and key not in ('content','aria-label') and not key.startswith('data-'): raise ValueError('CSS escapes are not allowed')
            if key=='href':
                if tag!='use' or not re.fullmatch(r'#[A-Za-z_][A-Za-z0-9_.:-]*',value): raise ValueError('Only local SVG use references are supported')
                target=ids.get(value[1:])
                if target is None or target.tag.split('}')[-1] not in ('path','g','symbol') or any(c.tag.split('}')[-1]=='use' for c in target.iter()): raise ValueError('Missing or recursive SVG glyph reference')
            if key.startswith('on') or key in ('src','base') or any(not re.fullmatch(r'#[A-Za-z_][A-Za-z0-9_.:-]*',u.strip().strip("\"'")) for u in urls):
                raise ValueError('Unsupported SVG external or active attribute')
    return data


def checked_language_qa(path, source, profile):
    """Consume the external checker's contract; linguistic rules belong upstream."""
    qa=read(path)
    if not isinstance(qa,dict) or qa.get('profile')!=profile or qa.get('input_sha256')!=sha(source):
        raise ValueError('Language QA profile/input binding mismatch')
    if not isinstance(qa.get('errors'),list) or qa['errors'] or qa.get('contract_status')!='pass' or qa.get('status')!='needs_review':
        raise ValueError('Language contract failed or unsupported QA status')
    if qa.get('semantic_review')!='not_run':
        raise ValueError('Automatic language QA cannot claim semantic review')
    return qa


def read_generated(block, expected_theme=None):
    if 'delivery_receipt' in block:
        from . import workflow
        return workflow.read_accepted(sys.modules[__name__],block,expected_theme)
    path=Path(block.get('path','')); invocation=Path(block.get('invocation',''))
    if not path.is_absolute() or not invocation.is_absolute(): raise ValueError('Generated diagram paths must be absolute local paths')
    if not block.get('alt'): raise ValueError('Generated diagram needs alt text')
    evidence=read(invocation)
    if not isinstance(evidence,dict): raise ValueError('Invocation must be an object')
    if evidence.get('schema_version')!=2: raise ValueError('Legacy invocation lacks the current language QA contract; regenerate rather than relabel')
    if expected_theme is not None and evidence.get('theme')!=theme(expected_theme): raise ValueError('Diagram theme differs from deck.theme; rerender with the shared theme')
    intent=evidence.get('intent')
    if intent not in ('model','report'): raise ValueError('Invocation must identify model or report')
    dep=evidence.get('dependency')
    package='technical-architecture-diagrams' if intent=='model' else 'technical-diagram-options'
    if (evidence.get('status')!='rendered' or not isinstance(dep,dict) or dep.get('commit')!=PIN
            or dep.get('repository')!=REPOSITORY or evidence.get('package')!=package or evidence.get('target')!='ppt'):
        raise ValueError('Missing successful pinned Skill invocation evidence')
    calls=evidence.get('calls')
    backend=evidence.get('model_backend','drawio')
    if intent=='model' and backend not in ('drawio','tikz'): raise ValueError('Unknown model backend evidence')
    operations=['resolve-palette','route']+(['select-options','check-language','check-report','render-report'] if intent=='report' else ['apply-model-palette','check-language','render-model-tikz' if backend=='tikz' else 'render-model'])
    files=['technical-architecture-diagrams/scripts/resolve_palette.py','technical-architecture-diagrams/scripts/route_request.py']+(
        ['technical-diagram-options/scripts/select_options.py','technical-architecture-diagrams/scripts/check_language.py','technical-diagram-options/scripts/diagram_tool.py','technical-diagram-options/scripts/diagram_tool.py'] if intent=='report' else
        ['technical-architecture-diagrams/scripts/apply_palette.py','technical-architecture-diagrams/scripts/check_language.py','../tools/render_model_tikz.py' if backend=='tikz' else 'technical-architecture-diagrams/scripts/drawio_runtime/export.mjs'])
    if not isinstance(calls,list) or len(calls)!=len(operations): raise ValueError('Incomplete diagram tool chain')
    for call,operation,file in zip(calls,operations,files):
        if (not isinstance(call,dict) or call.get('operation')!=operation or call.get('tool')!=('tools/render_model_tikz.py' if file.startswith('../tools/') else 'skills/'+file)
                or call.get('status')!='ok' or call.get('returncode')!=0): raise ValueError('Invalid or failed diagram tool call')
    language=evidence.get('language_qa')
    if not isinstance(language,dict) or evidence.get('language_profile')!=LOCK['language_profile']:
        raise ValueError('Legacy/unreviewed diagram has no current language QA; do not mark it compliant')
    if any(not isinstance(language.get(k),str) for k in ('path','sha256','input_path','input_sha256')):
        raise ValueError('Invalid language QA binding')
    qa_path=invocation.parent/language['path']; source=invocation.parent/language['input_path']
    if sha(qa_path)!=language['sha256'] or sha(source)!=language['input_sha256']:
        raise ValueError('Language QA/source changed after generation')
    qa=checked_language_qa(qa_path,source,evidence['language_profile'])
    if any(language.get(k)!=qa.get(k) for k in ('status','contract_status','semantic_review')):
        raise ValueError('Language QA summary differs from source result')
    artifacts=evidence.get('artifacts')
    if not isinstance(artifacts,list) or any(not isinstance(a,dict) or not isinstance(a.get('path'),str) or not isinstance(a.get('sha256'),str) for a in artifacts):
        raise ValueError('Invalid invocation artifacts')
    if intent=='model' and backend=='tikz':
        review=evidence.get('tex_source_review')
        if not isinstance(review,dict) or not isinstance(review.get('path'),str) or not isinstance(review.get('sha256'),str): raise ValueError('Missing TeX author review binding')
        review_path=invocation.parent/review['path']
        if sha(review_path)!=review['sha256']: raise ValueError('TeX author review changed')
        manifest=read(review_path); tex=invocation.parent/'artifacts/figure.tex'
        if not isinstance(manifest,dict): raise ValueError('TeX source review must be an object')
        if sha(tex)!=review.get('source_tex_sha256'): raise ValueError('Native TeX changed after render')
        checked_tex_manifest(manifest,invocation.parent/'authored.drawio',tex,
                             {'page':evidence.get('page',0),'custom_tokens':manifest.get('custom_tokens',{})},
                             {'theme':evidence.get('theme'),'palette':evidence.get('palette'),'language_profile':evidence.get('language_profile')},invocation.parent/'color-map.json')
    expected=next((a['sha256'] for a in evidence.get('artifacts',[]) if (invocation.parent/a['path']).resolve()==path.resolve()),None)
    if not expected or sha(path)!=expected: raise ValueError('Generated artifact differs from invocation evidence')
    return checked_svg(path)


def generated_html(block):
    data=read_generated(block)
    return '<figure class="source-figure"><img alt="'+html.escape(block['alt'],quote=True)+'" src="data:image/svg+xml;base64,'+base64.b64encode(data).decode()+'"></figure>'
