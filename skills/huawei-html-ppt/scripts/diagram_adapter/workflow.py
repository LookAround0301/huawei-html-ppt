"""Thin high-level handoff. The host runtime, not Python, schedules a drawing agent."""
from pathlib import Path
import os
import subprocess
import sys


def fresh_output(output):
    output=Path(output).resolve()
    if output.exists() and any(output.iterdir()): raise ValueError('Preserve previous evidence; choose an empty output directory')
    output.mkdir(parents=True,exist_ok=True)
    return output


def execute(api, root, tool, args, output):
    script=root/'tools'/tool
    try:
        tracked=subprocess.run(['git','-C',str(root),'ls-files','--error-unmatch',str(script.relative_to(root))],capture_output=True,text=True,timeout=15)
    except (OSError,subprocess.SubprocessError) as exc:
        raise ValueError('Pinned drawing workflow could not be verified') from exc
    if tracked.returncode or not script.is_file(): raise ValueError('Pinned drawing dependency does not provide high-level workflow tools')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    try:
        done=subprocess.run([sys.executable,str(script),*map(str,args)],capture_output=True,text=True,timeout=60,env=env)
    except (OSError,subprocess.SubprocessError) as exc:
        raise ValueError('Drawing workflow tool unavailable') from exc
    (output/(tool+'.log')).write_text(done.stdout+'\n'+done.stderr)
    if done.returncode: raise ValueError('Drawing workflow contract failed; inspect tool log')


def prepare(api, req, output):
    root=api.dependency(req); output=fresh_output(output)
    brief=req.get('brief')
    if not isinstance(brief,dict): raise ValueError('brief must contain facts and constraints, not pre-authored geometry')
    # The external schema owns allowed fields and design constraints.
    source=output/'submitted-brief.json';api.save(source,brief)
    handoff=output/'handoff'
    execute(api,root,'prepare_diagram_brief.py',['--input',source,'--out-dir',handoff],output)
    prepared=handoff/'brief.json';task=handoff/'agent-task.md'
    if not prepared.is_file() or not task.is_file(): raise ValueError('Independent drawing tool did not produce a handoff')
    available=req.get('agent_dispatch_available') is True
    result={'schema_version':1,'status':'awaiting_drawing_agent' if available else 'blocked_no_agent_dispatch',
            'brief':str(prepared),'brief_sha256':api.sha(prepared),'agent_task':str(task),'agent_task_sha256':api.sha(task),
            'dependency':{'repository':api.REPOSITORY,'commit':api.PIN},
            'dispatch':'Host must actually spawn an independent drawing agent with this handoff; no design or rendering has run.',
            'completion':'Return delivery and actual dispatch evidence to diagram-accept; do not substitute host-authored geometry.'}
    api.save(output/'handoff.json',result)
    return result


def dispatch_evidence(api, path, brief):
    evidence=api.read(path)
    if not isinstance(evidence,dict) or evidence.get('status')!='completed': raise ValueError('Independent agent execution not completed')
    if evidence.get('mechanism')!='independent_agent': raise ValueError('A real independent drawing agent is required')
    for key in ('host_agent_id','drawing_agent_id','task_record','task_record_sha256'):
        if not isinstance(evidence.get(key),str) or not evidence[key].strip(): raise ValueError('Missing independent agent dispatch evidence')
    if evidence['host_agent_id'].strip()==evidence['drawing_agent_id'].strip(): raise ValueError('Host authoring is not independent drawing execution')
    if evidence.get('brief_sha256')!=api.sha(brief): raise ValueError('Dispatch brief binding mismatch')
    record=Path(evidence['task_record'])
    if not record.is_absolute(): record=path.parent/record
    if not record.is_file() or api.sha(record)!=evidence['task_record_sha256']: raise ValueError('Missing or changed actual agent task record')
    return evidence,record.resolve()


def accept(api, req, output):
    root=api.dependency(req);output=fresh_output(output)
    brief=api.input_path(req,'brief');delivery=api.input_path(req,'delivery');dispatch=api.input_path(req,'dispatch')
    execution,record=dispatch_evidence(api,dispatch,brief)
    artifact_root=Path(req.get('artifact_root','')).resolve()
    if not req.get('artifact_root') or not artifact_root.is_dir(): raise ValueError('artifact_root must be the independent drawing delivery directory')
    qa=output/'delivery-qa.json'
    execute(api,root,'check_diagram_delivery.py',['--brief',brief,'--delivery',delivery,'--root',artifact_root,'--output',qa],output)
    check=api.read(qa)
    if not isinstance(check,dict) or check.get('contract_status')!='pass': raise ValueError('Independent drawing delivery contract did not pass')
    if check.get('brief_sha256')!=api.sha(brief) or check.get('delivery_sha256')!=api.sha(delivery): raise ValueError('Drawing delivery QA input binding mismatch')
    content=api.read(delivery)
    if not isinstance(content,dict) or content.get('status')!='completed': raise ValueError('Drawing agent delivery is blocked, not complete')
    selected_id=req.get('selected_variant_id')
    if not isinstance(selected_id,str) or not selected_id.strip(): raise ValueError('Host must explicitly choose selected_variant_id')
    variants=content.get('variants')
    if not isinstance(variants,list) or any(not isinstance(v,dict) for v in variants): raise ValueError('Missing drawing variants')
    chosen=[v for v in variants if v.get('id')==selected_id]
    if len(chosen)!=1: raise ValueError('Unknown or duplicate selected_variant_id')
    selected_ids=chosen[0].get('rendered_artifact_ids')
    if not isinstance(selected_ids,list): raise ValueError('Selected variant has no rendered artifacts')
    items=content.get('artifacts')
    if not isinstance(items,list) or any(not isinstance(a,dict) or any(not isinstance(a.get(k),str) for k in ('id','path','sha256','kind')) for a in items): raise ValueError('Invalid delivered artifacts')
    def bound_artifact(item):
        if not isinstance(item.get('path'),str): raise ValueError('Invalid drawing artifact path')
        path=(artifact_root/item['path']).resolve()
        if not path.is_relative_to(artifact_root) or api.sha(path)!=item.get('sha256'): raise ValueError('Drawing artifact changed or escaped delivery directory')
        return {'path':str(path),'sha256':item['sha256']}
    artifacts=[]
    for item in items:
        if item.get('id') not in selected_ids or item.get('kind')!='rendered' or Path(item.get('path','')).suffix.lower()!='.svg': continue
        bound=bound_artifact(item);api.checked_svg(Path(bound['path']));artifacts.append(bound)
    if not artifacts: raise ValueError('No safe rendered SVG for PPT embedding')
    pdfs=[a for a in items if a.get('id')==content.get('archive_pdf_artifact_id')]
    if len(pdfs)!=1 or Path(pdfs[0].get('path','')).suffix.lower()!='.pdf': raise ValueError('Missing all-variants PDF archive')
    archive=bound_artifact(pdfs[0])
    receipt={'schema_version':1,'status':'accepted_contract_not_aesthetic_approval',
             'dependency':{'repository':api.REPOSITORY,'commit':api.PIN},'theme':api.theme(api.read(brief).get('theme')),
             'theme_policy':'affinity_not_exact_colors','selected_variant_id':selected_id,'variants':variants,'archive_pdf':archive,
             'bindings':[{'path':str(p),'sha256':api.sha(p)} for p in (brief,delivery,dispatch,record,qa)],
             'drawing_agent_id':execution['drawing_agent_id'],'artifacts':artifacts,
             'review_boundary':'Contract and hashes checked; agent visual observations are evidence, not automated aesthetic proof or user approval.'}
    receipt_path=output/'acceptance.json';api.save(receipt_path,receipt)
    blocks=[{'type':'generated-diagram','path':a['path'],'delivery_receipt':str(receipt_path),'variant_id':selected_id,'alt':req.get('alt','Independently designed technical diagram')} for a in artifacts]
    api.save(output/'blocks.json',blocks)
    return {'status':receipt['status'],'receipt':str(receipt_path),'blocks':blocks,'selected_variant_id':selected_id,'variants':variants,'archive_pdf':archive}


def read_accepted(api, block, expected_theme=None):
    if not isinstance(block.get('path'),str) or not isinstance(block.get('delivery_receipt'),str) or not Path(block['path']).is_absolute() or not Path(block['delivery_receipt']).is_absolute():
        raise ValueError('Generated diagram paths must be absolute local paths')
    if not isinstance(block.get('alt'),str) or not block['alt'].strip(): raise ValueError('Generated diagram needs alt text')
    receipt=api.read(block['delivery_receipt'])
    if not isinstance(receipt,dict) or receipt.get('schema_version')!=1 or receipt.get('status')!='accepted_contract_not_aesthetic_approval':
        raise ValueError('Invalid independent drawing acceptance')
    if receipt.get('dependency')!={'repository':api.REPOSITORY,'commit':api.PIN}: raise ValueError('Independent drawing dependency mismatch')
    if receipt.get('theme_policy')!='affinity_not_exact_colors': raise ValueError('Missing high-level theme policy')
    if not isinstance(receipt.get('selected_variant_id'),str) or block.get('variant_id')!=receipt['selected_variant_id']: raise ValueError('Selected drawing variant differs from acceptance')
    archive=receipt.get('archive_pdf')
    if not isinstance(archive,dict) or not isinstance(archive.get('path'),str) or api.sha(Path(archive['path']))!=archive.get('sha256'): raise ValueError('All-variants PDF archive changed')
    bindings=receipt.get('bindings')
    if not isinstance(bindings,list) or len(bindings)!=5: raise ValueError('Missing independent drawing evidence bindings')
    for item in bindings:
        if not isinstance(item,dict) or not isinstance(item.get('path'),str) or api.sha(Path(item['path']))!=item.get('sha256'):
            raise ValueError('Independent drawing evidence changed')
    artifacts=receipt.get('artifacts')
    if not isinstance(artifacts,list) or any(not isinstance(a,dict) or not isinstance(a.get('path'),str) or not isinstance(a.get('sha256'),str) for a in artifacts): raise ValueError('Invalid independent drawing artifacts')
    path=Path(block['path']).resolve()
    match=next((a for a in artifacts if Path(a.get('path','')).resolve()==path),None)
    if not match or api.sha(path)!=match.get('sha256'): raise ValueError('Independent drawing SVG changed')
    return api.checked_svg(path)
