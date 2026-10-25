"""Small parameterized vector components with ports and a replayable use record."""
from pathlib import Path
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
INK, GRAY, RED = '#1D1D1A', '#666666', '#C00000'
WHITE, PALE, BLUE, FILL, LINE = '#FFFFFF', '#F8EDEC', '#EDF2F6', '#F3F3F3', '#999999'

def digest(v):
    return hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def catalog():
    return json.loads((ROOT/'assets/components/catalog.json').read_text(encoding='utf-8'))

class Diagram:
    def __init__(self, title, width=1164, height=454):
        self.data = {'title': title, 'width': width, 'height': height, 'elements': [],
                     'graph': {'nodes': {}, 'edges': [], 'uses': []}}

    def add(self, typ, **kw):
        self.data['elements'].append({'type': typ, **kw})

    def text(self, x, y, value, fs=17, bold=False, color=INK, anchor='start'):
        self.add('text', x=x, y=y, text=str(value), fs=fs, bold=bold, color=color, anchor=anchor)

    def rect(self, x, y, w, h, fill=WHITE, stroke=LINE, dash=False, r=1):
        self.add('rect', x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, sw=.9, dash=dash, r=r)

    def line(self, points, arrow=True, red=False, dash=False, sw=1.1):
        self.add('line', points=points, arrow=arrow, stroke=RED if red else '#777777', dash=dash, sw=sw, fill='none')

    def frame(self, key, x, y, w, h, title, red=False, fill=WHITE):
        self.rect(x,y,w,h,fill,RED if red else LINE,True)
        self.text(x+12,y+23,title,18,True,RED if red else INK)
        self._register(key,x,y,w,h,'group')

    def _register(self, key, x, y, w, h, role, **extra):
        if key in self.data['graph']['nodes']: raise ValueError('Duplicate node '+key)
        self.data['graph']['nodes'][key]={'box':[x,y,w,h], 'role':role, **extra}

    def node(self, key, x, y, w, h, label, role='compute', shape='box', fill=WHITE,
             red=False, fs=17, bold=False, require_io=False):
        """Geometry and role are separate: a matrix is cells, not just a matrix label."""
        stroke=RED if red else LINE
        if shape=='operator':
            self.add('ellipse',x=x,y=y,w=w,h=h,fill=WHITE,stroke=stroke,sw=1)
        elif shape in ('stack','tensor'):
            for dx,dy in [(7,-6),(3,-3),(0,0)]:self.rect(x+dx,y+dy,w,h,fill,stroke)
            if shape=='tensor':
                for offset in (7,14):self.line([[x+offset,y],[x+offset,y+h]],False,sw=.55)
        elif shape=='storage':
            self.rect(x,y+7,w,h-14,fill,stroke)
            # Endcaps leave a clear central text lane.
            for yy in (y+h-14,y):self.add('ellipse',x=x,y=yy,w=w,h=14,fill=fill,stroke=stroke,sw=.9)
        else:self.rect(x,y,w,h,fill,stroke)
        lines=str(label).split('\n')
        self.text(x+w/2,y+h/2-(len(lines)-1)*fs*.675+fs*.35,label,fs,bold,anchor='middle')
        self._register(key,x,y,w,h,role,shape=shape,require_io=require_io)
        return key

    def matrix(self,key,x,y,w,h,rows,cols,label,red=False,fs=15):
        self.text(x+w/2,y-9,label,fs,True,RED if red else INK,'middle')
        for r in range(rows):
            for c in range(cols):
                self.rect(x+c*w/cols,y+r*h/rows,w/cols,h/rows,
                          PALE if red and r==c else BLUE if r==c else WHITE,LINE)
        self._register(key,x,y,w,h,'matrix',shape='matrix')
        return key

    def port(self,key,side):
        x,y,w,h=self.data['graph']['nodes'][key]['box']
        return {'n':[x+w/2,y],'s':[x+w/2,y+h],'w':[x,y+h/2],'e':[x+w,y+h/2]}[side]

    def connect(self,source,target,source_port='e',target_port='w',via=(),kind='data',red=False,dash=False):
        points=[self.port(source,source_port),*[list(p) for p in via],self.port(target,target_port)]
        ix=len(self.data['elements'])
        self.line(points,True,red,dash or kind in ('control','zoom'))
        self.data['graph']['edges'].append({'source':source,'target':target,'kind':kind,'element':ix,
                                          'source_port':source_port,'target_port':target_port})

    def use(self,component,instance,x,y,w,h,**params):
        """Instantiate real drawing code. Merely listing an id in notes is not reuse."""
        defs={u['id']:u for u in catalog()['components']}
        if component not in defs or component not in BUILDERS:raise ValueError('Unknown component '+component)
        before=len(self.data['elements']); keys=set(self.data['graph']['nodes'])
        local=Diagram(component,defs[component]['viewbox'][0],defs[component]['viewbox'][1])
        BUILDERS[component](local,instance,params)
        sx=w/local.data['width'];sy=h/local.data['height']
        if abs(sx-sy)>.03:raise ValueError('Preserve component aspect ratio; resize its slot instead')
        for e in local.data['elements']:
            e=copy.deepcopy(e)
            if e['type']=='line' or e['type']=='polygon':e['points']=[[x+a*sx,y+b*sy] for a,b in e['points']]
            else:
                e['x']=x+e['x']*sx;e['y']=y+e['y']*sy
                for a in ('w','h','fs','r'):
                    if a in e:e[a]*=sx
            self.data['elements'].append(e)
        for key,n in local.data['graph']['nodes'].items():
            n=copy.deepcopy(n);a,b,c,d=n['box'];n['box']=[x+a*sx,y+b*sy,c*sx,d*sy]
            if key in keys:raise ValueError('Duplicate component instance '+instance)
            self.data['graph']['nodes'][key]=n
        for edge in local.data['graph']['edges']:
            edge=copy.deepcopy(edge);edge['element']+=before;self.data['graph']['edges'].append(edge)
        use={'component':component,'revision':defs[component]['revision'],'instance':instance,
             'slot':[x,y,w,h],'params':copy.deepcopy(params),'range':[before,len(self.data['elements'])],
             'geometry_hash':digest(self.data['elements'][before:]),'builder_hash':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        self.data['graph']['uses'].append(use)
        return {k.split(instance+'.',1)[-1]:k for k in local.data['graph']['nodes']}

    def contract(self,kind,required=(),paths=(),zooms=(),reference=None):
        self.data['acceptance']={'version':1,'kind':kind,'required_nodes':list(required),
             'paths':[list(p) for p in paths],'zooms':[list(p) for p in zooms],
             'reference':reference or 'No visual reference supplied; review against source-derived topology'}
        return self.data

def moe(d,i,p):
    def k(s):return i+'.'+s
    h=str(p['hidden']);inner=str(p['intermediate']);top=p['top_k'];experts=p['experts'];shared=p['shared']
    if not (0<top<=experts and shared>=0):raise ValueError('Invalid MoE routing')
    d.node(k('input'),8,85,73,57,'h\n'+h,'input','tensor',BLUE,fs=17)
    d.node(k('router'),129,15,117,33,'Router',fs=17)
    d.node(k('select'),290,15,158,33,f'Top-{top} / {experts}',role='routing',red=True)
    d.node(k('dispatch'),129,92,117,37,'Dispatch',fs=17)
    d.node(k('experts'),302,81,144,57,f'{top} 个激活专家','experts','stack',BLUE,fs=17)
    d.node(k('combine'),508,88,130,42,'加权合并',fs=17)
    d.node(k('sum'),690,96,25,25,'+','operation','operator',fs=19)
    d.node(k('output'),745,89,46,39,h,'output',fs=15)
    d.connect(k('input'),k('router'),'n','w',[[44,31]])
    d.connect(k('router'),k('select'))
    d.connect(k('input'),k('dispatch'))
    d.connect(k('select'),k('experts'),'s','n',[[369,64],[374,64]],kind='control',red=True)
    d.connect(k('dispatch'),k('experts'))
    d.connect(k('experts'),k('combine'))
    d.connect(k('select'),k('combine'),'e','n',[[572,31]],kind='control',red=True)
    d.connect(k('combine'),k('sum'))
    d.connect(k('sum'),k('output'))
    d.text(302,160,f'SwiGLU：{h} → {inner} → {h}',15)
    if shared:
        d.node(k('shared'),130,181,315,33,f'{shared} Shared expert · 独立计算','shared',fill=FILL,fs=17)
        d.connect(k('input'),k('shared'),'s','w',[[44,198]])
        d.connect(k('shared'),k('sum'),'e','s',[[702,198]])

def backbone(d,i,p):
    def k(s):return i+'.'+s
    d.node(k('output'),78,5,182,29,p.get('output','LM Head → token'),'output',fs=17)
    d.node(k('final'),93,48,152,28,p.get('final','Norm'),fs=16)
    d.frame(k('repeat'),25,99,289,250,p['repeat'])
    for key,y,label,fill in [('ffn',132,p['ffn'],BLUE),('post',181,p['post'],WHITE),
                              ('attn',231,p['attention'],PALE),('pre',280,p['pre'],WHITE)]:
        d.node(k(key),56,y,227,31,label,'compute',fill=fill,fs=16)
    d.node(k('input'),44,403,247,32,p['input'],'input',fill=FILL,fs=16)
    d.connect(k('input'),k('pre'),'n','s')
    for a,b in [('pre','attn'),('attn','post'),('post','ffn'),('ffn','final'),('final','output')]:d.connect(k(a),k(b),'n','s')
    d.text(44,335,p['layer_note'],14)
    d.text(44,378,p.get('below_note',''),15) if p.get('below_note') else None

def locator(d,i,p):
    for row,entries in enumerate([p['before'],p['after']]):
        y=8+row*48
        d.text(4,y+21,p['before_label'] if row==0 else p['after_label'],17,True,INK if row==0 else RED)
        d.node(i+f'.{row}.input',128,y,130,29,'Embedding','input',fs=16)
        last=i+f'.{row}.input';x=289
        avail=650;gap=27;cw=(avail-gap*(len(entries)-1))/len(entries)
        for n,e in enumerate(entries):
            key=i+f'.{row}.{e["id"]}'
            d.node(key,x,y,cw,29,e['label'],'change' if e.get('changed') else 'compute',fill=PALE if e.get('changed') else FILL,red=e.get('changed',False),fs=16)
            d.connect(last,key);last=key;x+=cw+gap
        out=i+f'.{row}.output';d.node(out,993,y,166,29,'Norm → LM Head','output',fs=16);d.connect(last,out)

def mhc(d,i,p):
    n=p['streams'];h=p['hidden']
    if not 2<=n<=6:raise ValueError('This compact mixer supports 2–6 streams')
    for a in range(n):
        key=i+f'.x{a}';d.node(key,13+a*139,17,117,31,f'x{a+1} · {h}','input','tensor',BLUE,fs=16)
    d.matrix(i+'.pre',192,99,76,43,1,n,'Hpre',True)
    d.matrix(i+'.res',36,174,102,92,n,n,'Hres',True)
    d.node(i+'.core',335,99,183,43,p.get('core','Norm → Attention'),'compute',fill=WHITE,fs=17)
    d.matrix(i+'.post',591,99,72,60,n,1,'Hpost',True)
    d.node(i+'.sum',703,188,28,28,'+','operation','operator',fs=20)
    d.node(i+'.output',778,164,189,74,f'{n} 条输出流\n每条 {h} 维','output','tensor',BLUE,fs=17)
    d._register(i+'.streams',13,71,534,2,'tensor-bus')
    for a in range(n):
        d.connect(i+f'.x{a}',i+'.streams','s','w',[[71+a*139,72]])
        d.data['elements'][-1]['arrow']=False
    d.connect(i+'.streams',i+'.pre','s','n',[[280,87],[230,87]])
    d.connect(i+'.streams',i+'.res','w','n',[[4,72],[4,155],[87,155]],kind='residual')
    d.connect(i+'.pre',i+'.core')
    d.connect(i+'.core',i+'.post')
    d.connect(i+'.post',i+'.sum','e','n',[[717,129]])
    d.connect(i+'.res',i+'.sum','e','s',[[174,220],[174,291],[717,291]],kind='residual')
    d.connect(i+'.sum',i+'.output')
    d.text(180,323,'Xout = Hres · X + Hpost · F(Hpre · X)',21,True)
    d.text(181,354,p.get('note','Hres 经 Sinkhorn 约束；Attention / FFN 各使用一组混合参数。'),16)

def recurrent(d,i,p):
    k=lambda s:i+'.'+s
    d.node(k('input'),10,30,76,32,'h(t)','input','tensor',BLUE,fs=17)
    d.node(k('proj'),136,26,252,42,'Q / K / V 投影 + 短卷积',fs=16)
    d.connect(k('input'),k('proj'))
    for j,(name,label) in enumerate([('q','q'),('k','k'),('v','v')]):
        d.node(k(name),151+j*80,96,46,31,label,'tensor','tensor',BLUE,fs=18)
        d.connect(k('proj'),k(name),'s','n',[[262,83],[174+j*80,83]])
    d.node(k('gate'),10,101,102,35,'遗忘 / 更新门',fs=14)
    d.connect(k('input'),k('gate'),'s','n')
    d.matrix(k('state'),17,191,88,63,4,4,'S(t−1)',False)
    d.node(k('update'),188,174,200,34,'门控 Delta 更新',fs=17,red=True)
    d.connect(k('state'),k('update'))
    for key in ('k','v'):d.connect(k(key),k('update'),'s','n',[[d.port(k(key),'s')[0],153],[288,153]])
    d.connect(k('gate'),k('update'),'e','w',[[132,119],[132,191]],kind='control')
    d.node(k('read'),217,224,170,31,'q 读取新状态',fs=16)
    d.connect(k('update'),k('read'),'s','n')
    d.connect(k('q'),k('read'),'s','w',[[174,239]])
    d.node(k('output'),217,273,170,29,'输出门控 → O proj','output',fs=15)
    d.connect(k('read'),k('output'),'s','n')
    d.connect(k('update'),k('state'),'e','s',[[395,191],[395,265],[61,265]],kind='write',dash=True)
    d.text(8,316,p['state_label'],14)

def sparse(d,i,p):
    k=lambda s:i+'.'+s
    d.node(k('input'),5,32,78,32,'h(t)','input','tensor',BLUE,fs=17)
    d.node(k('index_proj'),114,25,177,43,'Q index / K / Gate',fs=16)
    d.connect(k('input'),k('index_proj'))
    d.node(k('pool'),332,25,170,43,f'{p["pool"]} token → 1 索引','compute',fill=PALE,red=True,fs=16)
    d.connect(k('index_proj'),k('pool'))
    d.node(k('index'),568,14,163,66,f'池化索引 K\n{p["index_dim"]}维 · BF16','storage','storage',BLUE,fs=15,require_io=True)
    d.connect(k('pool'),k('index'),kind='write')
    d.node(k('tail'),330,105,171,53,'尾部 K / Gate\nFP32','storage','storage',FILL,fs=15,require_io=True)
    d.connect(k('index_proj'),k('tail'),'s','w',[[202,132]],kind='write')
    d.node(k('select'),568,116,163,36,'打分 → Top-K',red=True,fs=17)
    d.connect(k('index'),k('select'),'s','n',kind='read')
    d.connect(k('index_proj'),k('select'),'e','w',[[304,47],[304,91],[542,91],[542,134]],kind='data')
    d.node(k('expand'),330,185,401,32,'展开为 token 索引，并补齐尾部 token',fs=16)
    d.connect(k('select'),k('expand'),'s','n',[[650,172],[531,172]])
    d.connect(k('tail'),k('expand'),'s','n',[[416,173],[481,173]],kind='read',dash=True)
    d.node(k('mla'),9,165,196,39,'Q / latent KV 投影',fs=16)
    d.connect(k('input'),k('mla'),'s','n',[[44,143],[107,143]])
    d.node(k('main'),9,239,196,65,p['cache_label'],'storage','storage',BLUE,fs=15,require_io=True)
    d.connect(k('mla'),k('main'),'s','n',kind='write')
    d.node(k('attn'),351,260,200,35,'SFA → 输出投影','output',fill=PALE,fs=17)
    d.connect(k('main'),k('attn'),kind='read')
    d.connect(k('expand'),k('attn'),'s','n',[[531,237],[451,237]],kind='control',red=True)
    d.text(334,317,'主 KV 不池化；Top-K = '+str(p['top_k']),15,True,RED)

def comparison(d,i,p):
    headers=p['headers'];rows=p['rows'];widths=p.get('widths',[1/len(headers)]*len(headers))
    if len(widths)!=len(headers) or abs(sum(widths)-1)>.001 or any(len(row)!=len(headers) for row in rows):raise ValueError('Comparison columns mismatch')
    rh=(418-34)/max(1,len(rows));yy=0
    changed=set(p.get('changed_rows',[]))
    for n,row in enumerate([headers]+rows):
        xx=0;hh=34 if n==0 else rh
        for j,value in enumerate(row):
            w=520*widths[j];d.rect(xx,yy,w,hh,FILL if n==0 else WHITE)
            text=str(value);fs=p.get('font_size',16);lines=text.split('\n')
            d.text(xx+8,yy+hh/2-(len(lines)-1)*fs*.675+fs*.35,text,fs,n==0 or n-1 in changed,
                   RED if n-1 in changed and j==len(headers)-1 else INK)
            xx+=w
        yy+=hh
    d._register(i+'.table',0,0,520,418,'comparison')
    if p.get('note'):d.text(2,438,p['note'],14,color=GRAY)

def budget(d,i,p):
    cap=p['capacity'];segments=p['segments'];total=sum(s['gib'] for s in segments)
    if cap<=0 or any(s['gib']<0 for s in segments):raise ValueError('Invalid memory budget')
    scale=420/max(cap,total);xx=0
    d.text(0,18,p['title'],17,True)
    for n,s in enumerate(segments):
        w=s['gib']*scale;d.rect(xx,29,w,30,BLUE if n%2 else FILL)
        if w>=len(s['label'])*14+8:d.text(xx+w/2,49,s['label'],14,anchor='middle')
        xx+=w
    if total<cap:
        d.rect(xx,29,420-xx,30,WHITE)
        if 420-xx>=70:d.text((xx+420)/2,49,'未计项预算',14,color=GRAY,anchor='middle')
    d.rect(0,29,420,30,'none',RED if total>cap else LINE)
    d.text(0,80,f'已核算 {total:.2f} / {cap:.2f} GiB；'+('超出容量' if total>cap else '其余空间未必可用'),15,color=RED if total>cap else GRAY)
    d._register(i+'.budget',0,29,420,30,'capacity',capacity=cap,known_total=total,unresolved=p.get('unresolved',[]))

BUILDERS={'moe-routing':moe,'model-backbone':backbone,'version-locator':locator,
          'mhc-mixer':mhc,'recurrent-state':recurrent,'pooled-sparse-attention':sparse,
          'comparison-table':comparison,'memory-budget':budget}
