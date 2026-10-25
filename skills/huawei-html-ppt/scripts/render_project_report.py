"""Render formal project portfolio, landscape, coordination and explainer pages."""
from pathlib import Path
import argparse, base64, html, importlib.util, json

ROOT=Path(__file__).resolve().parents[1]
mod=importlib.util.spec_from_file_location('shared_diagrams',ROOT/'scripts/render_style_deck.py')
dg=importlib.util.module_from_spec(mod);mod.loader.exec_module(dg)
E=lambda x:html.escape(str(x),quote=True)

def rich(value):
    if isinstance(value,str):return E(value)
    return ''.join(f'<span class="em">{E(x["text"])}</span>' if isinstance(x,dict) and x.get('em') else E(x.get('text','') if isinstance(x,dict) else x) for x in value)

def ribbon(label,lines):
    return '<div class="ribbon"><div class="ribbon-label">'+E(label)+'</div><div class="ribbon-lines">'+''.join('<p>'+rich(x)+'</p>' for x in lines)+'</div></div>'

def milestones(items):
    return '<div class="milestones">'+''.join(f'<div class="milestone {"current" if x.get("current") else ""}"><b>{E(x["label"])}</b><i></i><span>{E(x["date"])}</span></div>' for x in items)+'</div>'

def portfolio(slide,diagrams):
    topics=slide['topics'];weights=slide.get('row_weights',[1]*len(topics))
    if len(topics)!=len(weights):raise ValueError('Topic row weights must align.')
    rows=';grid-template-rows:'+' '.join(f'{x}fr' for x in weights)
    left=[];right=[]
    for topic in topics:
        diagram=dg.prepare_diagram(topic['diagram']);diagrams.append(diagram)
        left.append(f'<section class="topic-row"><h3 class="topic-name">{E(topic["name"])}</h3><div class="topic-figure">{dg.svg(diagram)}</div></section>')
        cols=topic['progress_columns'];assert 1<=len(cols)<=3
        content=''.join('<div>'+''.join(f'<p class="progress-item"><span class="item-name">{E(item["name"])}：</span>{rich(item["text"])}</p>' for item in col)+'</div>' for col in cols)
        right.append(f'<section class="topic-row progress-row"><div class="theme-marker">{E(topic["name"])}</div><div class="progress-content"><p class="topic-summary"><span class="item-name">总进展：</span>{rich(topic["summary"])}</p><div class="progress-columns" style="--columns:{len(cols)}">{content}</div></div></section>')
    return ribbon('专题目标',slide['targets'])+'<div class="timeline"><div class="timeline-caption">项目节点<small>'+E(slide.get('milestone_note','日期为评审计划'))+'</small></div>'+milestones(slide['milestones'])+'</div><div class="portfolio-grid"><section class="corner-frame"><h2>技术布局</h2><div class="topic-rows" style="'+rows+'">'+''.join(left)+'</div></section><section class="corner-frame"><h2>技术点进展</h2><div class="topic-rows" style="'+rows+'">'+''.join(right)+'</div></section></div>'

def landscape(slide):
    cols=[]
    for project in slide['projects']:
        challenges=''.join(f'<li><b>{E(x["name"])}：</b>{rich(x["text"])}</li>' for x in project['challenges'])
        boxes=''.join(f'<div class="topic-box">{E(x)}</div>' for x in project['topics'])
        cols.append(f'<section class="corner-frame landscape-card"><h2>{E(project["name"])}</h2><p class="scope">{E(project["scope"])}</p><h3>核心挑战</h3><ul class="challenges">{challenges}</ul><div class="topic-matrix"><h3>对应专题</h3><div class="topic-boxes">{boxes}</div></div></section>')
    return ribbon('项目定位',[slide['positioning']])+'<div class="landscape-grid">'+''.join(cols)+'</div>'

def coordination(slide):
    stages=''.join(f'<div class="track-stage"><h3>{E(x["name"])}</h3><b>{E(x["owner"])}</b><p>{rich(x["description"])}</p></div>' for x in slide['stages'])
    handoff=''.join('<p>'+rich(x)+'</p>' for x in slide['handoff'])
    rules=''.join(f'<p class="{"gate" if x.get("gate") else ""}"><span class="item-name">{E(x["label"])}：</span>{rich(x["text"])}</p>' for x in slide['rules'])
    return ribbon('协同目标',[slide['purpose']])+f'<div class="coordination"><div class="track"><div class="track-name">技术线</div><div class="track-stages">{stages}</div></div><div class="handoff">{handoff}</div><div class="track version-track"><div class="track-name">版本线</div>{milestones(slide["versions"])}</div><div class="rules">{rules}</div></div>'

def explainer(slide):
    rows=slide['rows'];height=max(57,min(96,460//max(1,len(rows))))
    table='<table class="explain-table"><colgroup><col style="width:24%"><col style="width:40%"><col style="width:36%"></colgroup><thead><tr><th>技术点</th><th>做什么</th><th>解决什么问题</th></tr></thead><tbody>'
    for row in rows:table+=f'<tr style="height:{height}px">'+''.join('<td>'+rich(x)+'</td>' for x in row)+'</tr>'
    table+='</tbody></table>'
    return ribbon('作用',[slide['purpose']])+table+f'<div class="glossary">{E(slide.get("glossary",""))}</div>'

def render(spec,outdir):
    assert spec['style']=='technical-project'
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);(outdir/'diagrams').mkdir(exist_ok=True)
    css=(ROOT/'assets/project-report/style.css').read_text(encoding='utf-8')+'\n'+(ROOT/'assets/slide-viewer.css').read_text(encoding='utf-8')
    js=(ROOT/'assets/slide-viewer.js').read_text(encoding='utf-8')
    logo=base64.b64encode((ROOT/'assets/huawei-logo.png').read_bytes()).decode()
    pages=[]
    for n,slide in enumerate(spec['slides'],1):
        diagrams=[];layout=slide['layout']
        if layout=='project-portfolio':body=portfolio(slide,diagrams)
        elif layout=='project-landscape':body=landscape(slide)
        elif layout=='project-coordination':body=coordination(slide)
        elif layout=='project-explainer':body=explainer(slide)
        else:raise ValueError('Unsupported formal-project layout: '+layout)
        for k,d in enumerate(diagrams,1):
            (outdir/'diagrams'/f'{n:02d}-{k}.svg').write_text(dg.svg(d),encoding='utf-8');dg.drawio(d,outdir/'diagrams'/f'{n:02d}-{k}.drawio')
        pages.append(f'<article class="slide project-report" data-slide="{n}" data-layout="{layout}"><span class="context">{E(slide.get("context",""))}</span><h1>{E(slide["title"])}</h1>{body}<footer><span>{n:02d} / {len(spec["slides"]):02d}</span><img alt="HUAWEI" src="data:image/png;base64,{logo}"></footer></article>')
    metadata=json.dumps(spec,ensure_ascii=False).replace('</','<\\/')
    doc='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+E(spec['title'])+'</title><style>'+css+'</style></head><body><main class="deck">'+''.join(pages)+'</main><script type="application/json" id="deck-model">'+metadata+'</script><script>'+js+'</script></body></html>'
    output=outdir/(spec['title']+'.html');output.write_text(doc,encoding='utf-8');(outdir/'deck-model.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    return str(output)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('spec');p.add_argument('outdir');a=p.parse_args()
    print(render(json.loads(Path(a.spec).read_text(encoding='utf-8')),a.outdir))
