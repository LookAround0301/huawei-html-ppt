"""Check component replay, directed paths, storage I/O and overview-to-zoom links.

These checks verify stated structure, not visual quality or the truth of model facts.
"""
from collections import deque
import json
import math
from pathlib import Path
import diagram_components as dc

def audit(d,required=False):
    errors=[];warnings=[];g=d.get('graph');contract=d.get('acceptance')
    if not g or not contract:
        (errors if required else warnings).append('Missing diagram graph/acceptance contract; only legacy geometry checks are available')
        return {'ok':not errors,'errors':errors,'warnings':warnings,'components':[], 'visual_review_required':True}
    nodes=g.get('nodes',{});edges=g.get('edges',[]);uses=g.get('uses',[])
    def fail(message):errors.append(message)
    for key,n in nodes.items():
        b=n.get('box',[])
        if len(b)!=4 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in b):fail('Invalid node box: '+key);continue
        x,y,w,h=b
        if min(w,h)<=0 or x<0 or y<0 or x+w>d['width']+1 or y+h>d['height']+1:fail('Node outside canvas: '+key)
    for n,e in enumerate(d.get('elements',[])):
        if e['type'] in ('rect','ellipse'):
            if e['x']<0 or e['y']<0 or e['x']+e['w']>d['width']+1 or e['y']+e['h']>d['height']+1:fail(f'Shape {n} outside canvas')
        if e['type']=='text' and e.get('color',dc.INK).upper() not in {dc.INK,dc.GRAY,dc.RED,dc.WHITE}:fail(f'Text {n} uses nonstandard color')
    adjacency={key:[] for key in nodes}
    for e in edges:
        a,b=e.get('source'),e.get('target')
        if a not in nodes or b not in nodes:fail('Dangling edge: '+str((a,b)));continue
        if e.get('kind')!='zoom':adjacency[a].append(b)
        ix=e.get('element',-1)
        if not 0<=ix<len(d['elements']) or d['elements'][ix]['type']!='line':fail('Edge has no rendered line: '+str((a,b)))
    def reachable(a,b):
        seen=set();q=deque([a])
        while q:
            v=q.popleft()
            if v==b:return True
            if v in seen:continue
            seen.add(v);q.extend(adjacency.get(v,[]))
        return False
    for key in contract.get('required_nodes',[]):
        if key not in nodes:fail('Missing required node: '+key)
    for path in contract.get('paths',[]):
        for a,b in zip(path,path[1:]):
            if a not in nodes or b not in nodes or not reachable(a,b):fail('Broken required path: '+a+' -> '+b)
    for a,b in contract.get('zooms',[]):
        if not any(e['source']==a and e['target']==b and e.get('kind')=='zoom' for e in edges):fail('Missing visible zoom link: '+a+' -> '+b)
    for key,n in nodes.items():
        if n.get('require_io'):
            if not any(e['target']==key and e.get('kind')=='write' for e in edges):fail('Storage has no write: '+key)
            if not any(e['source']==key and e.get('kind')=='read' for e in edges):fail('Storage has no read: '+key)
    ids=[]
    if contract.get('kind') in ('architecture','zoom','mechanism') and not uses:fail('This structural diagram needs an instantiated component or a documented custom component')
    for u in uses:
        ids.append(u.get('component'))
        try:
            replay=dc.Diagram('replay',d['width'],d['height'])
            replay.use(u['component'],u['instance'],*u['slot'],**u['params'])
            start,end=u['range'];actual=d['elements'][start:end]
            if dc.digest(actual)!=u['geometry_hash'] or dc.digest(actual)!=dc.digest(replay.data['elements']):fail('Component geometry changed or not generated: '+u['instance'])
            if u['revision']!=replay.data['graph']['uses'][0]['revision']:fail('Component revision mismatch: '+u['instance'])
            for key,n in replay.data['graph']['nodes'].items():
                if nodes.get(key)!=n:fail('Component semantic node changed: '+key)
            for e in replay.data['graph']['edges']:
                expected={**e,'element':e['element']+start}
                if expected not in edges:fail('Component internal edge removed: '+str((e['source'],e['target'])))
        except (KeyError,TypeError,ValueError,OSError) as ex:fail('Cannot replay component: '+str(ex))
    if contract.get('kind') in ('architecture','zoom','mechanism') and not contract.get('paths'):warnings.append('No end-to-end semantic path declared')
    return {'ok':not errors,'errors':errors,'warnings':warnings,'components':ids,'visual_review_required':True}

def deck_audit(deck):
    result=[]
    for n,s in enumerate(deck.get('slides',[]),1):
        for p in s.get('panels',[]):
            for b in p.get('blocks',[]):
                if b.get('type')=='diagram':result.append({'slide':n,**audit(b['data'],deck.get('diagram_contract')==1)})
        for t in s.get('topics',[]):
            if t.get('diagram'):result.append({'slide':n,**audit(t['diagram'],deck.get('diagram_contract')==1)})
    return {'ok':all(r['ok'] for r in result),'diagrams':result,'visual_review_required':True,
            'review_items':['Compare actual model backbone and branches with sources','Inspect overview-to-zoom correspondence','Inspect text/arrow collisions at presentation size','Assess whether diagrams explain the conclusion; do not equate static pass with visual acceptance']}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('deck');p.add_argument('--output');a=p.parse_args()
    r=deck_audit(json.loads(Path(a.deck).read_text(encoding='utf-8')))
    if a.output:Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(not r['ok'])
