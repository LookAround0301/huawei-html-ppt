"""Render two-style JSON decks, diagrams and editable draw.io locally (stdlib only)."""
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
import argparse, base64, copy, html, json, importlib.util, hashlib

ROOT=Path(__file__).resolve().parents[1]
E=lambda v: html.escape(str(v),quote=True)


def chart_svg(data):
    """Simple report charts; shared data only, no estimated or generated values."""
    width,height=660,370;left,top,right,bottom=72,36,24,62
    w,h=width-left-right,height-top-bottom
    labels=data['x'];series=data['series'];maximum=max(v for s in series for v in s['values']) or 1
    maximum*=1.12
    colors=['#C00000','#666666','#1D1D1A']
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{E(data.get("title","数据图"))}">']
    for i in range(5):
        y=top+h-h*i/4;value=maximum*i/4
        out.append(f'<line x1="{left}" y1="{y}" x2="{width-right}" y2="{y}" stroke="#D9D9D9"/><text x="{left-8}" y="{y+5}" text-anchor="end" font-size="14" fill="#666666">{value:.3g}</text>')
    numeric_x=data['kind']=='line' and len(labels)>1 and all(isinstance(v,(int,float)) for v in labels)
    def px(i):
        if numeric_x:return left+w*(labels[i]-min(labels))/(max(labels)-min(labels))
        return left+w*(i+.5)/len(labels)
    for i,label in enumerate(labels):
        out.append(f'<text x="{px(i)}" y="{top+h+25}" text-anchor="middle" font-size="14" fill="#1D1D1A">{E(label)}</text>')
    for j,s in enumerate(series):
        points=[]
        for i,value in enumerate(s['values']):
            x,y=px(i),top+h-value/maximum*h;points.append(f'{x},{y}')
            if data['kind']=='bar':
                bw=w/len(labels)*.72/len(series);x+=bw*(j-len(series)/2)
                fill=colors[j] if j==0 else ['#C00000','#BDBDBD','#E7E7E7'][j]
                out.append(f'<rect x="{x}" y="{y}" width="{bw-3}" height="{top+h-y}" fill="{fill}" stroke="{colors[j]}" stroke-width="1"/>')
            else:
                out.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{colors[j]}"/>')
        if data['kind']=='line':out.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{colors[j]}" stroke-width="2.5"'+(' stroke-dasharray="6 3"' if j==2 else '')+'/>')
        out.append(f'<rect x="{left+j*170}" y="15" width="16" height="4" fill="{colors[j]}"/><text x="{left+22+j*170}" y="24" font-size="14" fill="#1D1D1A">{E(s["name"])}</text>')
    out.append(f'<text x="{left}" y="{height-5}" font-size="14" fill="#666666">{E(data.get("x_label",""))}</text><text x="8" y="22" font-size="14" fill="#666666">{E(data.get("y_label",""))}</text></svg>')
    return ''.join(out)


def prepare_diagram(diagram):
    """Use the accepted black/gray/red label policy without altering topology."""
    result=copy.deepcopy(diagram)
    if result.get('preserve_text_colors',False):
        return result
    gray={'#666666','#5C6974','#73828D','#929292','#667580'}
    red={'#C00000','#E9002F','#C20041','RED'}
    for element in result.get('elements',[]):
        if element.get('type')!='text':
            continue
        color=element.get('color','#1D1D1A').upper()
        element['color']=('#C00000' if color in red else '#666666' if color in gray
                          else '#FFFFFF' if color in {'#FFFFFF','WHITE'} else '#1D1D1A')
    return result

def svg(d, marker_prefix=None):
    marker_prefix=marker_prefix or 'arrow-'+hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()[:12]
    colors=sorted({e.get('stroke','#526573') for e in d['elements'] if e.get('arrow')})
    markers={c:f'{marker_prefix}-{n}' for n,c in enumerate(colors)}
    defs=''.join(f'<marker id="{E(key)}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto-start-reverse" markerUnits="userSpaceOnUse"><path d="M0,0 L9,4.5 L0,9 Z" fill="{E(color)}"/></marker>' for color,key in markers.items())
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {d["width"]} {d["height"]}" role="img" aria-label="{E(d.get("title","技术图"))}"><defs>{defs}</defs>']
    for e in d['elements']:
        typ=e['type'];fill=e.get('fill','none');stroke=e.get('stroke','#526573');sw=e.get('sw',1.2)
        attrs=f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"'+(' stroke-dasharray="6 4"' if e.get('dash') else '')
        if typ=='rect': out.append(f'<rect x="{e["x"]}" y="{e["y"]}" width="{e["w"]}" height="{e["h"]}" rx="{e.get("r",0)}" {attrs}/>')
        elif typ=='ellipse': out.append(f'<ellipse cx="{e["x"]+e["w"]/2}" cy="{e["y"]+e["h"]/2}" rx="{e["w"]/2}" ry="{e["h"]/2}" {attrs}/>')
        elif typ in ('line','polygon'):
            tag='polygon' if typ=='polygon' else 'polyline'
            points=' '.join(f'{p[0]},{p[1]}' for p in e['points'])
            out.append(f'<{tag} points="{points}" {attrs}'+(f' marker-end="url(#{markers[stroke]})"' if e.get('arrow') else '')+'/>')
        elif typ=='text':
            fs=e.get('fs',18);lines=e['text'].split('\n');anchor=e.get('anchor','start');x=e['x'];y=e['y']
            out.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{fs}" style="fill:{e.get("color","#202B35")};font-weight:{700 if e.get("bold") else 400}">')
            for i,line in enumerate(lines):out.append(f'<tspan x="{x}" dy="{0 if i==0 else fs*1.35}">{E(line)}</tspan>')
            out.append('</text>')
    return ''.join(out)+'</svg>'

def drawio(d,path):
    root=Element('mxfile',host='local');di=SubElement(root,'diagram',name=d.get('title','Diagram'),id='local-diagram')
    model=SubElement(di,'mxGraphModel',page='1',pageWidth=str(d['width']),pageHeight=str(d['height']));rt=SubElement(model,'root')
    SubElement(rt,'mxCell',id='0');SubElement(rt,'mxCell',id='1',parent='0')
    for i,e in enumerate(d['elements'],2):
        typ=e['type'];stroke=e.get('stroke','#526573');fill=e.get('fill','none');sw=e.get('sw',1.2)
        style=f'strokeColor={stroke};fillColor={fill};strokeWidth={sw};'+('dashed=1;' if e.get('dash') else '')
        a={'id':str(i),'parent':'1'}
        if typ=='line':
            a.update(edge='1',style=style+'edgeStyle=none;endArrow='+('block;' if e.get('arrow') else 'none;'))
            c=SubElement(rt,'mxCell',a);g=SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'});ps=e['points']
            for p,role in [(ps[0],'sourcePoint'),(ps[-1],'targetPoint')]:SubElement(g,'mxPoint',x=str(p[0]),y=str(p[1]),attrib={'as':role})
            if len(ps)>2:
                ar=SubElement(g,'Array',attrib={'as':'points'})
                for p in ps[1:-1]:SubElement(ar,'mxPoint',x=str(p[0]),y=str(p[1]))
            continue
        if typ=='polygon':
            # All polygons in this library are triangular operation/projection shapes.
            xs=[p[0] for p in e['points']];ys=[p[1] for p in e['points']]
            x,y,w,h=min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)
            style+='shape=triangle;direction=east;'
        else:
            x,y=e['x'],e['y'];w=e.get('w',220);h=e.get('h',len(e.get('text','').split('\n'))*e.get('fs',18)*1.35)
            if typ=='ellipse':style+='ellipse;'
            elif typ=='text':
                fs=e.get('fs',18);w=e.get('w',min(d['width'],max(len(v) for v in e['text'].split('\n'))*fs));h=len(e['text'].split('\n'))*fs*1.35
                if e.get('anchor')=='middle':x-=w/2
                y-=fs;style=f'text;html=0;whiteSpace=wrap;align={"center" if e.get("anchor")=="middle" else "left"};fontFamily=Microsoft YaHei;fontSize={fs};fontColor={e.get("color","#202B35")};fontStyle={1 if e.get("bold") else 0};'
                a['value']=e['text']
            else:style+='rounded='+('1;' if e.get('r') else '0;')
        a.update(vertex='1',style=style);c=SubElement(rt,'mxCell',a);SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
    path.write_text(tostring(root,encoding='unicode'),encoding='utf-8')

def render(spec,outdir,asset_root=ROOT):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);(outdir/'diagrams').mkdir(exist_ok=True)
    catalog=json.loads((asset_root/'assets/two-style/layouts.json').read_text(encoding='utf-8'))
    style=spec['style'];assert style in catalog['styles']
    styles=(asset_root/'assets/two-style/style.css').read_text(encoding='utf-8')+'\n'+(asset_root/'assets/project-report/style.css').read_text(encoding='utf-8')+'\n'+(asset_root/'assets/slide-viewer.css').read_text(encoding='utf-8')
    viewer=(asset_root/'assets/slide-viewer.js').read_text(encoding='utf-8')
    logo=base64.b64encode((asset_root/'assets/huawei-logo.png').read_bytes()).decode()
    pages=[]
    for n,s in enumerate(spec['slides'],1):
        lay=catalog['layouts'][s['layout']];assert lay['style']==style,(style,s['layout'])
        if lay.get('class')=='project-report':
            module=importlib.util.spec_from_file_location('formal_project',ROOT/'scripts/render_project_report.py')
            project=importlib.util.module_from_spec(module);module.loader.exec_module(project)
            ds=[]
            if s['layout']=='project-portfolio': body=project.portfolio(s,ds)
            elif s['layout']=='project-landscape': body=project.landscape(s)
            elif s['layout']=='project-coordination': body=project.coordination(s)
            else: body=project.explainer(s)
            for k,d in enumerate(ds,1):
                (outdir/'diagrams'/f'{n:02d}-{k}.svg').write_text(svg(d,f'arrow-{n}-{k}'),encoding='utf-8')
                drawio(d,outdir/'diagrams'/f'{n:02d}-{k}.drawio')
            pages.append(f'<article class="slide project-report" data-slide="{n}" data-layout="{s["layout"]}"><span class="context">{E(s.get("context",""))}</span><h1>{E(s["title"])}</h1>{body}<footer><span>{n:02d} / {len(spec["slides"]):02d}</span><img alt="HUAWEI" src="data:image/png;base64,{logo}"></footer></article>')
            continue
        if style=='technical-project':
            labels=s.get('labels',lay['header']);assert labels in [['挑战','目标'],['目标','进展']]
            assert len(s.get('summary',[]))==2
            top='<div class="summary">'+''.join(f'<div class="pair"><strong>{E(l)}</strong><p>{E(v)}</p></div>' for l,v in zip(labels,s['summary']))+'</div>'
        else:
            assert s.get('conclusion')
            top=f'<aside class="insight-conclusion" aria-label="分析结论"><strong class="conclusion-label">分析结论</strong><p>{E(s["conclusion"])}</p></aside>'
        panels=[]
        for k,p in enumerate(s['panels'],1):
            body=''
            for block_index,b in enumerate(p['blocks'],1):
                if b['type']=='diagram':
                    d=prepare_diagram(b['data']);stem=f'{n:02d}-{k}'
                    if sum(v['type']=='diagram' for v in p['blocks'])>1:stem+=f'-{block_index}'
                    body+=svg(d,f'arrow-{stem}')
                    (outdir/'diagrams'/f'{stem}.svg').write_text(svg(d,f'arrow-{stem}'),encoding='utf-8');drawio(d,outdir/'diagrams'/f'{stem}.drawio')
                elif b['type']=='chart':body+=chart_svg(b['data'])
                elif b['type']=='text':body+=f'<p class="{E(b.get("class",""))}">{E(b["text"]).replace(chr(10),"<br>")}</p>'
                elif b['type']=='heading':body+=f'<h3>{E(b["text"])}</h3>'
                elif b['type']=='bullets':body+='<ul>'+''.join(f'<li>{E(v)}</li>' for v in b['items'])+'</ul>'
                elif b['type']=='table':
                    widths=b.get('widths',[1/len(b['headers'])]*len(b['headers']))
                    body+='<div class="table-wrap"><table><colgroup>'+''.join(f'<col style="width:{w*100}%">' for w in widths)+'</colgroup><thead><tr>'+''.join(f'<th>{E(v)}</th>' for v in b['headers'])+'</tr></thead><tbody>'
                    for row in b['rows']:body+='<tr>'+''.join(f'<td>{E(v).replace(chr(10),"<br>")}</td>' for v in row)+'</tr>'
                    body+='</tbody></table></div>'
            panels.append(f'<section class="frame {E(p.get("class",""))}"><h2>{E(p["title"])}</h2>{body}</section>')
        pages.append(f'<article class="slide {style}" data-slide="{n}" data-layout="{s["layout"]}"><span class="eyebrow">{E(spec.get("chapter",catalog["styles"][style]["name"]))}</span><h1>{E(s["title"])}</h1><div class="head-rule"></div>{top}<div class="body-grid {lay["class"]}">{"".join(panels)}</div><footer><span>{n:02d} / {len(spec["slides"]):02d}　 Huawei Confidential</span><img alt="HUAWEI" src="data:image/png;base64,{logo}"></footer></article>')
    metadata=json.dumps(spec,ensure_ascii=False).replace('</','<\\/')
    doc=f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(spec["title"])}</title><style>{styles}</style></head><body><main class="deck">{"".join(pages)}</main><script type="application/json" id="deck-model">{metadata}</script><script>{viewer}</script></body></html>'
    output=outdir/(spec['title']+'.html');output.write_text(doc,encoding='utf-8');(outdir/'deck-model.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    return str(output)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('spec');p.add_argument('outdir');p.add_argument('--assets-root',type=Path,default=ROOT);a=p.parse_args()
    print(render(json.loads(Path(a.spec).read_text(encoding='utf-8')),a.outdir,a.assets_root))
