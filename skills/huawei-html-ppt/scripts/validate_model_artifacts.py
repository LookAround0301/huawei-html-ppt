"""Validate semantic graphs and model-analysis scenarios against an explicit contract.

Contract paths are relative to the contract file. This validates consistency with
declared evidence; it does not establish that the evidence or runtime is correct.
"""
from pathlib import Path
import argparse, hashlib, json, sys

class ValidationError(ValueError): pass

def require(value,message):
    if not value: raise ValidationError(message)

def field(data,path):
    for name in path.split('.'):
        data=data[name]
    return data

def reachable(graph,start,end):
    seen=set();pending=[start]
    while pending:
        node=pending.pop()
        if node==end:return True
        if node in seen:continue
        seen.add(node)
        pending.extend(edge[1] for edge in graph['edges'] if edge[0]==node)
    return False

def load_objects(contract,root):
    objects={}
    for name,filename in contract['files'].items():
        p=root/filename
        objects[name]=p.read_text(encoding='utf-8-sig') if name=='html' else json.loads(p.read_text(encoding='utf-8-sig'))
    return objects

def validate_objects(contract,objects):
    graphs=objects['graphs'];count=0
    for name,g in graphs.items():
        for edge in g['edges']:
            require(edge[0] in g['nodes'] and edge[1] in g['nodes'],f'Unknown endpoint: {name}/{edge}')
    for rule in contract.get('graph_rules',[]):
        graph=graphs[rule['graph']]
        if 'when' in rule and field(objects['config'],rule['when']['field'])!=rule['when']['equals']:continue
        forbidden=set(rule.get('forbid_ops',[]))
        require(not any(n.get('op') in forbidden for n in graph['nodes'].values()),f'Forbidden operation: {rule["graph"]}')
        order=rule.get('ordered_nodes',[])
        for a,b in zip(order,order[1:]):
            require(reachable(graph,a,b),f'Execution order missing: {rule["graph"]}/{a}->{b}')
            require(not reachable(graph,b,a),f'Execution order reversed: {rule["graph"]}/{b}->{a}')
        for node,op in rule.get('node_ops',{}).items():
            require(graph['nodes'][node].get('op')==op,f'Operation mismatch: {rule["graph"]}/{node}')
        count+=1
    results=objects['results'];profiles=objects['profiles']['scenarios']
    actual={s['name']:s for s in results['scenarios']}
    require(len(actual)==len(results['scenarios']),'Duplicate result scenarios')
    require(set(actual)=={s['name'] for s in profiles},'Scenario coverage differs from baseline')
    scenario_checks=[]
    for expected in profiles:
        s=actual[expected['name']]
        require(s['inputs']==expected['inputs'],f'Input mismatch: {s["name"]}')
        for key in ['partitions','recipe','phase','scope']:
            require(s[key]==expected[key],f'{key} mismatch: {s["name"]}')
        require(sum(s['partitions'])==field(objects['config'],'text_config.num_hidden_layers'),f'PP coverage: {s["name"]}')
        require(len(s['stages'])==len(s['partitions']),f'PP result coverage: {s["name"]}')
        for stage in s['stages']:
            require(stage['total_bytes']==stage['weight_bytes']+stage['cache_bytes']+stage['buffer_bytes'],f'Stage sum mismatch: {s["name"]}')
        max_stage=max(s['stages'],key=lambda x:x['total_bytes'])
        require(s['max_stage']==max_stage['stage'] and s['total_bytes']==max_stage['total_bytes'],f'Wrong complete-stage maximum: {s["name"]}')
        require(s['total_bytes']==round(expected['expected_max_total_gib']*2**30),f'Baseline maximum differs: {s["name"]}')
        current=s['stages'][expected['current_stage']]
        for key in ['weight','cache','buffer','total']:
            require(current[key+'_bytes']==round(expected['expected_current'][key+'_gib']*2**30),f'Baseline current-stage {key}: {s["name"]}')
        scenario_checks.append({'name':s['name'],'max_stage':s['max_stage'],'delta_bytes':0})
    if 'html' in objects:
        digest=hashlib.sha256(json.dumps(graphs,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        require(f'content="{digest}"' in objects['html'],'HTML graph digest differs from validated graph data')
    return {'passed':True,'graph_rules_checked':count,'scenarios':scenario_checks,'device_execution':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--contract',required=True);p.add_argument('--output')
    args=p.parse_args();source=Path(args.contract).resolve();contract=json.loads(source.read_text(encoding='utf-8-sig'))
    try:result=validate_objects(contract,load_objects(contract,source.parent))
    except (ValidationError,KeyError,TypeError) as error:
        print(json.dumps({'passed':False,'error':str(error)},ensure_ascii=False));return 1
    if args.output:Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False));return 0

if __name__=='__main__':sys.exit(main())
