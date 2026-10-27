"""Read-only dependency inventory. Never installs, downloads, or grants consent."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys


def probe(args, timeout=15):
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    try:
        done=subprocess.run(args,capture_output=True,text=True,timeout=timeout,env=env)
        return {'ok':done.returncode==0,'output':done.stdout.strip(),'error':done.stderr.strip()}
    except (OSError,subprocess.SubprocessError) as exc:
        return {'ok':False,'output':'','error':str(exc)}


def inspect(api, req):
    if not isinstance(req,dict): raise ValueError('doctor request must be an object')
    backend=req.get('backend','common')
    if backend not in ('common','report','drawio','tikz'): raise ValueError('Choose backend common|report|drawio|tikz')
    checks=[]
    def add(component,ready,required,source,location,impact,detail=''):
        checks.append({'component':component,'status':'available' if ready else 'missing_or_incompatible',
                       'required_version':required,'source':source,'install_location':location,'impact':impact,'detail':detail})
    dispatch=req.get('agent_dispatch_available') is True
    add('independent_agent_dispatch',dispatch,'host runtime capability; not an installable Python package',
        'Host Agent scheduling tools','host runtime','Cannot be fixed by software installation; do not substitute host-authored drawings')
    add('python',sys.version_info>=(3,10),'Python >=3.10','https://www.python.org/downloads/',
        'approved task/project environment','Do not replace system Python',sys.version.split()[0])
    git=shutil.which('git');add('git',bool(git),'Git supporting the pinned checkout','https://git-scm.com/downloads',
        'existing executable or user-approved platform package location','No sudo or system changes by this tool')
    value=req.get('infra_root') or os.environ.get('INFRA_IO_ROOT');root=Path(value).resolve() if value else None
    verified=False;checkout_state='not_configured';detail='Set INFRA_IO_ROOT to an existing checkout, or approve a new version-specific task directory.'
    if root and root.is_dir() and git:
        prefix=[git,'-c','core.fsmonitor=false','-C',str(root)]
        head=probe(prefix+['rev-parse','HEAD']);status=probe(prefix+['status','--porcelain','--untracked-files=normal'])
        if not head['ok'] or not status['ok']: checkout_state='unreadable';detail='Read-only Git probe failed; do not repair or overwrite automatically.'
        elif status['output']: checkout_state='dirty';detail='Existing changes/untracked files require review; preserve them. Use another directory, never clean/reset automatically.'
        elif head['output']!=api.PIN: checkout_state='version_mismatch';detail='Keep existing checkout intact; use a separate pinned version directory after consent.'
        else: verified=True;checkout_state='clean_pinned';detail=head['output']
    add('infra_io_checkout',verified,api.PIN,api.REPOSITORY,str(root) if root else 'user-confirmed version-specific task directory',
        'Network download and disk use only after confirmation; do not overwrite another checkout',detail)
    requirements=[]
    if verified:
        path=root/'requirements.txt'
        try:
            lines=[line.strip() for line in path.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
            matches=[re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s#]+)',line) for line in lines]
            valid=bool(lines) and all(matches)
            if valid: requirements=[m.groups() for m in matches]
        except OSError: valid=False
        if not valid: add('python_requirements_manifest',False,'nonempty exact requirements.txt pins at '+api.PIN,api.REPOSITORY,'pinned checkout','Do not infer absent requirements or guessed versions')
    if not verified:
        add('python_dependencies',False,'requirements.txt at '+api.PIN,api.REPOSITORY+'/blob/'+api.PIN+'/requirements.txt',
            'isolated project virtual environment','pip downloads only after confirmation; enumerate exact package pins after checkout')
    for name,wanted in requirements:
        try: actual=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: actual=None
        add('python:'+name,actual==wanted,wanted,'https://pypi.org/project/'+name+'/'+wanted+'/',
            'isolated project virtual environment','Do not uninstall/change system packages; version differences require review',actual or 'not installed')
    binaries=['pdfinfo','pdftotext']
    if backend in ('report','drawio','tikz'): binaries+=['inkscape']
    if backend=='tikz': binaries+=['xelatex','kpsewhich','pdftocairo','pdftoppm']
    for binary in binaries:
        source=('https://inkscape.org/release/' if binary=='inkscape' else 'https://tug.org/texlive/' if binary in ('xelatex','kpsewhich') else 'https://poppler.freedesktop.org/')
        add(binary,bool(shutil.which(binary)),'platform package version to disclose before install',source,
            'existing PATH or user-approved task/user package location','Platform-dependent package/download size; no privileged install',shutil.which(binary) or '')
    if backend=='tikz' and shutil.which('kpsewhich'):
        for name in ('xelatex.fmt','standalone.cls','tikz.sty','fontspec.sty'):
            result=probe([shutil.which('kpsewhich'),name]);add('tex:'+name,result['ok'] and bool(result['output']),
                'same approved TeX Live distribution as selected engine','https://tug.org/texlive/',
                'existing TEXMF/TEXFORMATS or approved task cache','TeX may be large; reuse compatible installed packages/formats; never regenerate system caches automatically',result['output'])
    if backend=='drawio':
        node=shutil.which('node');version=probe([node,'--version']) if node else {'ok':False,'output':''};match=re.match(r'v?(\d+)',version['output'])
        add('node',bool(version['ok'] and match and int(match[1])>=20),'Node >=20','https://nodejs.org/en/download',
            'existing PATH or approved user-level runtime','Do not replace system runtime',version['output'])
        module=Path(os.environ['PLAYWRIGHT_MODULE']) if os.environ.get('PLAYWRIGHT_MODULE') else root/'node_modules/playwright' if root else None
        package=module/'package.json' if module and module.is_dir() else module.parent/'package.json' if module else None
        try:
            metadata=json.loads(package.read_text()) if package and package.is_file() else {}
            installed=metadata.get('version') if isinstance(metadata,dict) else None
        except (OSError,ValueError): installed=None
        add('playwright',installed=='1.62.1','1.62.1 (pinned package-lock.json)','https://playwright.dev/docs/library',
            'approved project dependency directory','npm package and browser downloads require separate disclosed consent',installed or 'not found')
        chrome=os.environ.get('CHROME_BINARY') or shutil.which('chromium') or shutil.which('google-chrome')
        add('chromium',bool(chrome and Path(chrome).is_file() and os.access(chrome,os.X_OK)),'compatible with pinned Playwright; launch not tested',
            'https://playwright.dev/docs/browsers','existing executable or approved browser cache','Browser download may be substantial; no sandbox/security bypass',chrome or '')
        if verified:
            manifest=root/'skills/technical-architecture-diagrams/scripts/drawio_runtime/graph-runtime.json';bundle=root/'third_party/drawio/app.min.js'
            try:
                expected=json.loads(manifest.read_text())
                if not isinstance(expected,dict) or not isinstance(expected.get('version'),str) or not isinstance(expected.get('sha256'),str): raise ValueError('Invalid runtime metadata')
                ok=bundle.is_file() and hashlib.sha256(bundle.read_bytes()).hexdigest()==expected['sha256']
            except (OSError,ValueError,KeyError): expected={};ok=False
            add('drawio_bundle',ok,expected.get('version','pinned manifest')+' / SHA256 '+expected.get('sha256','unknown'),
                expected.get('download_url',api.REPOSITORY),'pinned checkout third_party/drawio','Reuse matching bundle; only approved official pin/hash fetch, not rolling latest')
    missing=[x for x in checks if x['status']!='available'];software=[x for x in missing if x['component']!='independent_agent_dispatch']
    declined=req.get('installation_decision')=='declined'
    status='ready_for_workflow' if not missing else 'blocked_no_agent_dispatch' if not dispatch else 'blocked_installation_declined' if declined else 'needs_installation_review'
    return {'status':status,'read_only':True,'backend':backend,'checkout_state':checkout_state,
            'dependency':{'repository':api.REPOSITORY,'commit':api.PIN},'checks':checks,'install_plan':software,
            'installation_executed':False,'consent_required':bool(software),'configuration_is_not_consent':True,'installation_declined':declined,
            'plan_requires_resolution':bool(software),
            'next_action':'Continue workflow; do not ask to reinstall available dependencies.' if not missing else 'Host independent-agent scheduling is unavailable; installation cannot supply it. Remain blocked and do not repeatedly ask to install software for this capability.' if not dispatch else 'Installation was declined: remain blocked, preserve requested drawing quality, and do not repeat the same question without changed circumstances.' if declined else 'Resolve and show missing components, exact selected platform versions/location/size-impact and official commands; only then ask for explicit installation confirmation. No install:true flag grants consent.',
            'limits':['Executable presence/version is not a successful renderer launch or visual test.','Backend-specific preflight must follow renderer selection; source-specific fonts and actual launch still require a self-test.','Host Agent scheduling cannot be installed by this tool.','After approved installation, rerun this doctor and the documented backend self-test; never silently simplify a blocked drawing.']}
