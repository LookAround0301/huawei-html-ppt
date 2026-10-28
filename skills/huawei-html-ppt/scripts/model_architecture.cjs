(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.ModelArch2D=factory();})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const C={ink:'#20252B',muted:'#64717D',line:'#99A5B1',red:'#C00000',blue:'#E8F0F8',rose:'#F9E9E8',gray:'#F2F4F6',white:'#FFFFFF'};
const kinds=new Set(['mla','dsa','kda','moe','dense','gqa','residual','graph']);
function esc(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c])).replace(/\n/g,'&#xa;');}
function clone(v){return JSON.parse(JSON.stringify(v));}
function validate(m){
 const errors=[];if(!m||typeof m!=='object')return ['模型必须是 JSON 对象'];
 if(m.schema_version!==1)errors.push('schema_version 必须为 1');
 if(!m.id||!m.name)errors.push('缺少模型 id/name');
 if(!m.modules||!Object.keys(m.modules).length)errors.push('缺少 modules');
 const stages=m.architecture&&m.architecture.stages;
 if(!Array.isArray(stages)||!stages.length)errors.push('缺少 architecture.stages');
 let total=0;const ids=new Set();
 for(const s of stages||[]){
  if(!s.id||ids.has(s.id))errors.push('stage id 缺失或重复');ids.add(s.id);
  if(!Number.isInteger(s.repeat)||s.repeat<1)errors.push('stage.repeat 必须为正整数');
  if(!Array.isArray(s.blocks)||!s.blocks.length)errors.push('stage.blocks 不能为空');
  let count=0;
  for(const b of s.blocks||[]){
   if(!m.modules?.[b.attention])errors.push('未知 attention 引用: '+b.attention);
   if(b.ffn&&!m.modules?.[b.ffn])errors.push('未知 ffn 引用: '+b.ffn);
   if(!Number.isInteger(b.repeat)||b.repeat<1)errors.push('block.repeat 必须为正整数');
   count+=b.repeat||0;
  } total+=count*(s.repeat||0);
 }
 if(m.layers!=null&&m.layers!==total)errors.push('层数不一致：声明 '+m.layers+'，主干计算 '+total);
 for(const [id,mod] of Object.entries(m.modules||{})){
  if(!kinds.has(mod.kind))errors.push('未知模块类型 '+mod.kind+'；可使用 graph 显式定义');
  if(!mod.label)errors.push(id+' 缺少 label');
  if(mod.kind==='moe'&&(!(mod.experts>0)||!(mod.active>0)||mod.active>mod.experts||!(mod.shared>=0)))errors.push(id+' 专家数量无效');
  if(mod.kind==='dsa'&&(!(mod.top_k>0)||!(mod.index_heads>0)||!(mod.index_dim>0)))errors.push(id+' Indexer 参数不完整');
  if(mod.kind==='graph'){
   const ni=new Set((mod.graph?.nodes||[]).map(n=>n.id));
   if(ni.size!==(mod.graph?.nodes||[]).length||!ni.size)errors.push(id+' 自定义节点 id 缺失或重复');
   for(const e of mod.graph?.edges||[])if(!ni.has(e.source)||!ni.has(e.target))errors.push(id+' 自定义连线存在悬空端点');
  }
 }
 return errors;
}
class Scene{
 constructor(w=1500,h=900,title=''){this.width=w;this.height=h;this.title=title;this.nodes=[];this.edges=[];this.labels=[];this.frames=[];this.ids=new Set();}
 node(id,x,y,w,h,label,opt={}){if(this.ids.has(id))throw Error('重复节点 '+id);this.ids.add(id);const n={id,x,y,w,h,label,shape:'box',role:'compute',fill:C.white,fs:20,...opt};this.nodes.push(n);return n;}
 frame(id,x,y,w,h,label,opt={}){this.frames.push({id,x,y,w,h,label,...opt});}
 text(x,y,text,opt={}){this.labels.push({x,y,text,fs:18,color:C.muted,anchor:'start',...opt});}
 get(id){const n=this.nodes.find(n=>n.id===id);if(!n)throw Error('未知节点 '+id);return n;}
 port(id,p){
  const n=this.get(id);let {x,y,w,h}=n;
  if(n.shape==='label'){
   w=Math.max(n.fs*.7,...String(n.label||'').split('\n').map(line=>line.length*n.fs*.58))+8;
   h=n.fs*1.35;x=n.x+(n.w-w)/2;y=n.y+(n.h-h)/2;
  }
  if(Array.isArray(p))return[x+w*p[0],y+h*p[1]];
  return {n:[x+w/2,y],s:[x+w/2,y+h],w:[x,y+h/2],e:[x+w,y+h/2]}[p||'e'];
 }
 edge(a,b,opt={}){this.get(a);this.get(b);this.edges.push({id:'edge-'+this.edges.length,source:a,target:b,sourcePort:'e',targetPort:'w',role:'data',...opt});}
 path(e){return orthogonalPath(this.port(e.source,e.sourcePort),this.port(e.target,e.targetPort),e.sourcePort,e.targetPort,e.via||[]);}
}
function orthogonalPath(start,end,sourcePort='e',targetPort='w',via=[]){
 const horizontal=p=>Array.isArray(p)?(p[0]===0||p[0]===1):['e','w'].includes(p);
 const sh=horizontal(sourcePort),th=horizontal(targetPort);let points=[start];
 if(!via.length && start[0]!==end[0] && start[1]!==end[1]){
  if(sh&&th){const x=(start[0]+end[0])/2;points.push([x,start[1]],[x,end[1]]);}
  else if(!sh&&!th){const y=(start[1]+end[1])/2;points.push([start[0],y],[end[0],y]);}
  else points.push(sh?[end[0],start[1]]:[start[0],end[1]]);
  points.push(end);
 }else{
  const targets=[...via,end];let h=sh;
  for(let i=0;i<targets.length;i++){
   const a=points[points.length-1],b=targets[i];
   if(a[0]!==b[0]&&a[1]!==b[1]){
    const firstHorizontal=i===targets.length-1?!th:h;
    points.push(firstHorizontal?[b[0],a[1]]:[a[0],b[1]]);
   }
   points.push(b);const p=points[points.length-2];h=p[1]===b[1];
  }
 }
 points=points.map(p=>p.map(v=>Math.round(v*1000)/1000));
 const clean=[];for(const p of points){
  if(clean.length&&p[0]===clean.at(-1)[0]&&p[1]===clean.at(-1)[1])continue;
  while(clean.length>1){const a=clean.at(-2),b=clean.at(-1);if((a[0]===b[0]&&b[0]===p[0])||(a[1]===b[1]&&b[1]===p[1]))clean.pop();else break;}
  clean.push(p);
 }return clean;
}
function textSVG(x,y,t,fs,color,anchor='middle',bold=false){const lines=String(t).split('\n');return `<text x="${x}" y="${y-(lines.length-1)*fs*.58}" fill="${color}" font-size="${fs}" text-anchor="${anchor}" font-weight="${bold?600:400}">${lines.map((s,i)=>`<tspan x="${x}" dy="${i?fs*1.22:0}">${esc(s)}</tspan>`).join('')}</text>`;}
function nodeSVG(n){const line=n.selected?C.red:C.line;let shape='';
 if(n.shape==='label')shape='';
 else if(n.shape==='operator')shape=`<ellipse cx="${n.x+n.w/2}" cy="${n.y+n.h/2}" rx="${n.w/2}" ry="${n.h/2}" fill="${n.fill}" stroke="${line}"/>`;
 else if(n.shape==='tensor'){
  for(let r=0;r<4;r++)for(let c=0;c<3;c++)shape+=`<rect x="${n.x+c*n.w/3}" y="${n.y+r*n.h/4}" width="${n.w/3}" height="${n.h/4}" fill="${n.fill}" stroke="${line}" stroke-width=".7"/>`;
 }else if(n.shape==='experts'){
  for(let i=0;i<4;i++){const xx=n.x+i*(n.w-10)/4;shape+=`<rect x="${xx+4}" y="${n.y-4}" width="${(n.w-24)/4}" height="${n.h}" rx="3" fill="${n.fill}" stroke="${line}"/><rect x="${xx}" y="${n.y}" width="${(n.w-24)/4}" height="${n.h}" rx="3" fill="${n.fill}" stroke="${line}"/>`;}
 }else if(n.shape==='memory'){
  shape=`<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="5" fill="${n.fill}" stroke="${line}"/>`;
 }else shape=`<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="${n.shape==='pill'?n.h/2:5}" fill="${n.fill}" stroke="${line}" stroke-width="${n.selected?1.8:1}"/>`;
 if(n.label&&n.shape!=='tensor'&&n.shape!=='experts')shape+=textSVG(n.x+n.w/2,n.y+n.h/2+(n.sub?-3:n.fs*.32),n.label,n.fs,n.color||C.ink,'middle',n.bold);
 if(n.sub)shape+=textSVG(n.x+n.w/2,n.y+n.h-9,n.sub,Math.min(n.fs-3,17),C.muted);
 if(n.shape==='tensor'&&n.label)shape+=textSVG(n.x+n.w/2,n.y-12,n.label,17,C.ink);
 if(n.shape==='experts')shape+=textSVG(n.x+n.w/2,n.y+n.h+22,n.label,17,C.ink);
 return `<g data-node="${esc(n.id)}" ${n.module?`data-module="${esc(n.module)}" tabindex="0" role="button" aria-label="${esc(n.label)}"`:''}>${shape}</g>`;
}
function assertEnglishLabels(scene){
 const labels=[scene.title,...scene.nodes.flatMap(n=>[n.label,n.sub]),...scene.frames.map(f=>f.label),...scene.labels.map(l=>l.text)];
 const invalid=labels.filter(v=>v&&/\p{Script=Han}/u.test(String(v)));
 if(invalid.length)throw Error('Translate Chinese diagram labels before export: '+invalid.join(' | '));
}
function svg(scene){
 assertEnglishLabels(scene);
 let out=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${scene.width} ${scene.height}" width="${scene.width}" height="${scene.height}" role="img" aria-label="${esc(scene.title)}"><defs><marker id="arch-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 Z" fill="${C.muted}"/></marker><marker id="arch-red-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 Z" fill="${C.red}"/></marker></defs><style>text{font-family:Arial,'Microsoft YaHei',sans-serif}g[data-module]{cursor:pointer}g[data-module]:focus{outline:none}g[data-module]:hover>rect{stroke:#C00000;stroke-width:2}</style><rect width="100%" height="100%" fill="white"/>`;
 for(const f of scene.frames){out+=`<rect x="${f.x}" y="${f.y}" width="${f.w}" height="${f.h}" rx="6" fill="${f.fill||C.white}" stroke="${f.accent?C.red:'#BCC5CD'}" ${f.dash?'stroke-dasharray="6 5"':''}/>`;if(f.label)out+=textSVG(f.x+18,f.y+29,f.label,20,f.accent?C.red:C.ink,'start',true);}
 for(const e of scene.edges){const pts=scene.path(e);out+=`<polyline data-edge="${e.id}" data-source="${esc(e.source)}" data-target="${esc(e.target)}" points="${pts.map(p=>p.join(',')).join(' ')}" fill="none" stroke="${e.red?C.red:C.muted}" stroke-width="${e.role==='focus'?1.9:1.35}" stroke-linejoin="round" ${['control','zoom'].includes(e.role)?'stroke-dasharray="5 4"':''} marker-end="url(#${e.red?'arch-red-arrow':'arch-arrow'})"/>`;}
 for(const n of scene.nodes)out+=nodeSVG(n);
 for(const l of scene.labels)out+=textSVG(l.x,l.y,l.text,l.fs,l.color,l.anchor,l.bold);
 return out+'</svg>';
}
function dims(mod){return mod.params||{};}
function moduleGraph(s,mod,prefix,slot,opt={}){
 const sx=slot.w/1000,sy=slot.h/300;
 const pos=(x,y,w,h)=>[slot.x+x*sx,slot.y+y*sy,w*sx,h*sy];
 const id=k=>prefix+'.'+k;
 const node=(k,x,y,w,h,l,o={})=>s.node(id(k),...pos(x,y,w,h),l,{fs:18,fill:C.white,...o});
 const edge=(a,b,o={})=>{if(o.via)o.via=o.via.map(([x,y])=>[slot.x+x*sx,slot.y+y*sy]);s.edge(id(a),id(b),o);};
 const txt=(x,y,l,o={})=>s.text(slot.x+x*sx,slot.y+y*sy,l,{fs:17,...o});
 const p=dims(mod); const hidden=p.hidden||'d';
 if(mod.kind==='mla'||mod.kind==='dsa'){
  const sparse=mod.kind==='dsa';
  node('h',15,115,32,72,'h',{shape:'label'});
  node('q',102,46,155,49,'Q projection',{sub:p.q_rank?'rank '+p.q_rank:null});
  node('kv',102,197,155,48,'KV projection',{sub:p.kv_rank?'rank '+p.kv_rank:null});
  node('q_t',309,39.5,34,62,'Q',{shape:'label'});
  node('cache',304,197,172,48,'Main KV',{shape:'memory',fill:C.gray,sub:p.kv_rank?String(p.kv_rank)+(p.cache_extra_dim?' + '+p.cache_extra_dim:'')+' dims':null});
  node('attn',535,104,190,68,sparse?'Sparse MLA':'MLA',{fill:C.blue,sub:'Softmax(QKᵀ)V'});
  node('gate',791,117,42,42,'×',{shape:'operator',fs:25});
  node('out',884,113,101,50,'O proj.');
  node('gproj',586,240,176,40,'sigmoid(g_proj)',{fill:C.rose,fs:17});
  edge('h','q',{sourcePort:'e',targetPort:'w',via:[[75,151],[75,70]]});edge('h','kv',{via:[[75,151],[75,221]]});edge('q','q_t');
  if(sparse)edge('q_t','attn',{targetPort:'w',via:[[390,70.5],[390,138]]});
  else edge('q_t','attn',{targetPort:'n',via:[[630,70.5]]});
  edge('kv','cache');edge('cache','attn',{targetPort:'s',via:[[630,220]]});
  edge('attn','gate');edge('gate','out');edge('h','gproj',{sourcePort:'s',via:[[31,280],[560,280],[560,260]]});edge('gproj','gate',{sourcePort:'e',targetPort:'s',via:[[812,260]]});
  txt(756,227,'Gate',{color:C.muted});
  if(sparse){
   node('indexer',397,13,330,44,'Indexer · Top-'+mod.top_k,{fill:C.rose,fs:18,sub:mod.index_heads+' heads × '+mod.index_dim});
   node('indexcache',785,13,195,44,'Indexer K',{shape:'memory',fill:C.gray,fs:17,sub:mod.index_dim+' dims'});
   edge('h','indexer',{sourcePort:'e',targetPort:'w',via:[[65,151],[65,35]]});
   edge('indexer','indexcache',{sourcePort:[1,.3],targetPort:[0,.3],role:'write'});
   edge('indexcache','indexer',{sourcePort:[0,.8],targetPort:[1,.8],role:'read'});
   edge('indexer','attn',{sourcePort:'s',targetPort:'n',via:[[562,84],[630,84]],role:'control',red:true});txt(684,90,'indices',{color:C.red,fs:16});
  }
 } else if(mod.kind==='kda'){
  node('h',15,100,32,72,'h',{shape:'label'});node('qkv',112,65,155,50,'Q / K / V');node('conv',337,65,150,50,'Convolution',{fill:C.blue});
  node('core',570,65,155,50,'KDA',{fill:C.blue});node('norm',795,65,180,50,'Norm + gate\nO projection');
  node('gate',112,228,180,40,'β / f / g projection',{fill:C.rose,fs:17});node('cs',337,161,150,43,'Conv state',{shape:'memory',fill:C.gray,fs:17});node('rs',570,161,155,43,'Recurrent state',{shape:'memory',fill:C.gray,fs:17});
  edge('h','qkv',{via:[[78,136],[78,90]]});edge('qkv','conv');edge('conv','core');edge('core','norm');
  edge('h','gate',{sourcePort:'s',via:[[31,248]]});edge('gate','core',{targetPort:[.15,1],via:[[524,248],[524,131],[593,131]],role:'control'});
  edge('gate','norm',{targetPort:'s',via:[[780,248],[885,248]],role:'control'});
  for(const [a,b]of[['conv','cs'],['core','rs']]){edge(a,b,{sourcePort:[.42,1],targetPort:[.42,0],role:'write'});edge(b,a,{sourcePort:[.62,0],targetPort:[.62,1],role:'read'});}
  txt(523,156,'β, f',{fs:16});txt(900,215,'g',{fs:17});txt(340,294,'Prefill: chunk KDA   /   Decode: recurrent update',{fs:17});
 } else if(mod.kind==='moe'){
  node('h',15,119.5,32,75,'h',{shape:'label'});node('route',115,22,160,44,'Router');node('top',339,22,146,44,'Top '+mod.active+' / '+mod.experts,{fill:C.rose,fs:18});
  node('down',115,133,160,48,'Down projection',{fill:C.blue,sub:p.latent?hidden+' → '+p.latent:null});node('dispatch',340,133,140,48,opt.communication?'EP Dispatch':'Dispatch',{fill:C.blue});
  node('experts',534,116.5,210,81,mod.active+' active experts',{shape:'experts',fill:C.blue});node('combine',791,133,159,48,opt.communication?'EP Combine':'Combine',{fill:C.blue});
  node('up',791,190,159,43,'Norm + Up',{sub:p.latent?p.latent+' → '+hidden:null,fs:17});node('sum',971,250,38,38,'+',{shape:'operator',fs:25});
  edge('h','route',{sourcePort:'n',via:[[31,44]]});edge('route','top');edge('h','down');edge('down','dispatch');edge('dispatch','experts');edge('top','experts',{sourcePort:'s',targetPort:'n',via:[[412,85],[638,85]],role:'control'});edge('experts','combine');edge('combine','up',{sourcePort:'s',targetPort:'n'});edge('up','sum',{targetPort:'n',via:[[990,211.5]]});
  if(mod.shared){node('shared',340,250,300,38,mod.shared+' shared experts · '+hidden,{fill:C.rose,fs:17});edge('h','shared',{sourcePort:'s',via:[[31,269]]});edge('shared','sum');}
  txt(550,239,mod.activation||'Expert FFN',{fs:17});
 }else if(mod.kind==='dense'){
  node('h',20,120,35,75,'h',{shape:'label'});node('up',150,65,170,52,'Up projection',{fill:C.blue});node('gate',150,202,170,52,'Gate projection',{fill:C.blue});node('act',440,205,160,46,mod.activation||'Activation',{fill:C.rose});node('mul',681,131,44,44,'×',{shape:'operator',fs:26});node('down',806,126,166,55,'Down projection',{fill:C.blue});
  edge('h','up',{via:[[104,157],[104,91]]});edge('h','gate',{via:[[104,157],[104,228]]});edge('gate','act');edge('up','mul',{targetPort:'n',via:[[703,91]]});edge('act','mul',{targetPort:'s',via:[[703,228]]});edge('mul','down');
  txt(151,285,p.intermediate?hidden+' → '+p.intermediate+' → '+hidden:'Gated feed-forward network',{fs:18});
 }else if(mod.kind==='residual'){
  node('x',15,78,90,54,'h',{shape:'label'});node('mix1',166,78,118,54,'AttnRes',{fill:C.rose});node('attn',350,78,150,54,'Norm + Attn',{fill:C.blue});node('mix2',561,78,118,54,'AttnRes',{fill:C.rose});node('ffn',755,78,183,54,'Norm + FFN',{fill:C.blue});node('bank',233,220,422,44,'Cross-layer residual bank',{shape:'memory',fill:C.gray});
  for(const [a,b]of[['x','mix1'],['mix1','attn'],['attn','mix2'],['mix2','ffn']])edge(a,b);
  edge('bank','mix1',{sourcePort:[.15,0],targetPort:'s',via:[[225,190]],role:'read'});edge('bank','mix2',{sourcePort:[.88,0],targetPort:'s',via:[[620,190]],role:'read'});edge('x','bank',{sourcePort:'s',targetPort:'w',via:[[60,242]],role:'write'});txt(240,289,'Block size '+(mod.block_size||'?')+' · residual state is separate from KV cache',{fs:17});
 }else if(mod.kind==='gqa'){
  node('h',20,113,35,75,'h',{shape:'label'});node('qkv',155,120,170,64,'Q / K / V',{sub:mod.heads?mod.heads+' Q heads':null});node('cache',390,220,190,42,'KV Cache',{shape:'memory',fill:C.gray});node('attn',540,110,185,72,'Attention',{fill:C.blue,sub:'Softmax(QKᵀ)V'});node('out',820,120,150,64,'O projection');edge('h','qkv');edge('qkv','attn');edge('qkv','cache',{sourcePort:'s',targetPort:'w',via:[[240,241]]});edge('cache','attn',{targetPort:'s',via:[[630,241]]});edge('attn','out');
 }else if(mod.kind==='graph'){
  const graph=mod.graph,levels={};for(const n of graph.nodes)levels[n.id]=0;
  for(let i=0;i<graph.nodes.length;i++)for(const e of graph.edges)if(!['read','write','control'].includes(e.role))levels[e.target]=Math.max(levels[e.target],Math.min(graph.nodes.length,levels[e.source]+1));
  const max=Math.max(...Object.values(levels)),used={};for(const n of graph.nodes){const level=levels[n.id],row=used[level]||0;used[level]=row+1;node(n.id,20+level*820/Math.max(max,1),55+row*85,150,52,n.label,{shape:n.shape||'box',fill:C[n.fill]||C.blue,fs:17});}
  for(const e of graph.edges)edge(e.source,e.target,{role:e.role||'data',sourcePort:e.sourcePort||'e',targetPort:e.targetPort||'w'});
 }
}
function title(s,m,x=38,y=45){s.text(x,y,m.name,{fs:30,bold:true,color:C.ink});s.text(x,y+33,m.summary||'',{fs:18,color:C.muted});}
function backbone(s,m,x,y,w,selected,small=false){
 const fs=small?18:20;let yy=y;let last=null;const cx=x+w/2;
 function add(key,label,h=46,opt={}){const id=m.id+'.'+key;s.node(id,x+18,yy,w-36,h,label,{fs,module:opt.module,...opt});if(last)s.edge(last,id,{sourcePort:'s',targetPort:'n'});last=id;yy+=h+22;return id;}
 add('tokens','Input tokens',34,{shape:'label'});add('embedding','Embedding',43,{fill:C.rose});
 for(const stage of m.architecture.stages){
  const boxH=stage.blocks.length*89+43;
  s.frame(m.id+'.group.'+stage.id,x,yy-4,w,boxH,stage.repeat>1?'× '+stage.repeat:(stage.label||'Final layer'),{dash:true});yy+=40;
  for(let i=0;i<stage.blocks.length;i++){
   const b=stage.blocks[i],mod=m.modules[b.attention];
   const layerId=add(stage.id+'.'+i,mod.label+(b.repeat>1?' × '+b.repeat:''),59,{fill:mod.kind==='kda'?C.blue:C.rose,module:b.attention,selected:selected===b.attention,sub:b.ffn?'+ '+m.modules[b.ffn].label:null,fs});
  }
  yy+=7;
 }
 add('norm',m.architecture.norm||'Final Norm',40,{fill:C.gray});add('head',m.architecture.head||'LM Head',43,{fill:C.rose});add('output','Output tokens',34,{shape:'label'});
 return yy;
}
function render(m,options={}){
 const errors=validate(m);if(errors.length)throw Error(errors.join('\n'));
 const selected=options.module&&m.modules[options.module]?options.module:(m.default_attention||Object.keys(m.modules)[0]);
 const ffn=m.default_ffn||Object.keys(m.modules).find(k=>['moe','dense'].includes(m.modules[k].kind));
 const moduleOnly=options.view==='module';
 const backboneHeight=426+m.architecture.stages.reduce((n,g)=>n+g.blocks.length*81+47,0);
 const s=new Scene(1500,moduleOnly?590:Math.max(900,backboneHeight+60),m.name);
 title(s,m);s.text(1460,44,moduleOnly?'Module detail':'Model architecture',{fs:18,anchor:'end',color:C.red,bold:true});
 if(moduleOnly){s.frame('module-panel',28,110,1444,402,m.modules[selected].label,{fill:'#FAFBFC'});moduleGraph(s,m.modules[selected],'detail',{x:55,y:162,w:1384,h:316},options);s.text(45,553,m.modules[selected].note||'Data flow and state follow the module definition.',{fs:19});return s;}
 backbone(s,m,32,125,300,selected);
 s.text(36,107,'Model backbone',{fs:19,bold:true,color:C.red});
 const top=m.modules[selected];s.frame('attention-panel',386,117,1084,330,top.label,{fill:'#FBFCFD',accent:top.kind==='dsa'});moduleGraph(s,top,'detail',{x:405,y:166,w:1043,h:258},options);
 if(ffn){const mod=m.modules[ffn];s.frame('ffn-panel',386,478,1084,330,mod.label,{fill:'#FBFCFD'});moduleGraph(s,mod,'ffn',{x:405,y:523,w:1030,h:258},options);}
 s.text(390,844,m.architecture.residual||'Norm / residual connections follow the model definition.',{fs:18});
 s.text(390,875,m.architecture.exception_note||'',{fs:18,color:C.muted});
 return s;
}
function compare(a,b,options={}){
 for(const m of[a,b]){const e=validate(m);if(e.length)throw Error(e.join('\n'));}
 const s=new Scene(1500,920,a.name+' / '+b.name);s.text(34,44,a.name+'  →  '+b.name,{fs:29,bold:true,color:C.ink});s.text(34,78,'Aligned backbones with module changes',{fs:18});
 s.text(165,115,a.name,{fs:20,bold:true,anchor:'middle'});s.text(468,115,b.name,{fs:20,bold:true,anchor:'middle',color:C.red});
 backbone(s,a,24,142,282,a.default_attention,true);backbone(s,b,326,142,282,b.default_attention,true);
 const aMod=a.modules[a.default_attention],bMod=b.modules[b.default_attention];
 s.frame('before',650,127,824,340,a.name+' · '+aMod.label,{fill:'#FBFCFD'});moduleGraph(s,aMod,'before',{x:667,y:182,w:790,h:260},options);
 s.frame('after',650,499,824,340,b.name+' · '+bMod.label,{fill:'#FBFCFD',accent:true});moduleGraph(s,bMod,'after',{x:667,y:553,w:790,h:260},options);
 s.text(652,882,b.change_note||'Only explicitly defined module changes are shown.',{fs:18,color:C.red});return s;
}
function drawio(s){assertEnglishLabels(s);let cells='<mxCell id="0"/><mxCell id="1" parent="0"/>';
 for(const f of s.frames)cells+=`<mxCell id="frame-${esc(f.id)}" value="${esc(f.label)}" style="rounded=1;absoluteArcSize=1;arcSize=12;fillColor=${f.fill||C.white};strokeColor=${f.accent?C.red:C.line};dashed=${f.dash?1:0};verticalAlign=top;align=left;spacingLeft=14;fontSize=20;fontFamily=Microsoft YaHei;" vertex="1" parent="1"><mxGeometry x="${f.x}" y="${f.y}" width="${f.w}" height="${f.h}" as="geometry"/></mxCell>`;
 for(const n of s.nodes){
  if(['tensor','experts'].includes(n.shape)){
   cells+=`<mxCell id="${esc(n.id)}" value="" style="group;" vertex="1" connectable="1" parent="1"><mxGeometry x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" as="geometry"/></mxCell>`;
   const child=(key,x,y,w,h,style,value='')=>{cells+=`<mxCell id="${esc(n.id+'-'+key)}" value="${esc(value)}" style="${style}" vertex="1" connectable="0" parent="${esc(n.id)}"><mxGeometry x="${x}" y="${y}" width="${w}" height="${h}" as="geometry"/></mxCell>`;};
   const style=`fillColor=${n.fill};strokeColor=${C.line};strokeWidth=0.7;`;
   if(n.shape==='tensor'){for(let r=0;r<4;r++)for(let c=0;c<3;c++)child(r+'-'+c,c*n.w/3,r*n.h/4,n.w/3,n.h/4,style);child('label',-40,-28,n.w+80,24,'text;html=0;fontSize=17;fontFamily=Arial;align=center;verticalAlign=middle;',n.label);}
   else{for(let i=0;i<4;i++){const xx=i*(n.w-10)/4;child(i+'-back',xx+4,-4,(n.w-24)/4,n.h,style+'rounded=1;');child(i+'-front',xx,0,(n.w-24)/4,n.h,style+'rounded=1;');}child('label',-20,n.h+3,n.w+40,27,'text;html=0;fontSize=17;fontFamily=Arial;align=center;verticalAlign=middle;',n.label);}
  }else{const shape=n.shape==='operator'?'ellipse;':n.shape==='label'?'text;strokeOpacity=0;fillOpacity=0;':'';cells+=`<mxCell id="${esc(n.id)}" value="${esc(n.label+(n.sub?'\n'+n.sub:''))}" style="${shape}rounded=1;absoluteArcSize=1;arcSize=10;whiteSpace=wrap;html=0;fillColor=${n.fill};strokeColor=${n.selected?C.red:C.line};fontColor=${C.ink};fontSize=${n.fs};fontFamily=Arial;" vertex="1" parent="1"><mxGeometry x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" as="geometry"/></mxCell>`;}
 }
 const port=(id,p)=>{const n=s.get(id),v=s.port(id,p);return[(v[0]-n.x)/n.w,(v[1]-n.y)/n.h];};
 for(const e of s.edges){const ep=port(e.source,e.sourcePort),ip=port(e.target,e.targetPort),via=s.path(e).slice(1,-1);cells+=`<mxCell id="${e.id}" source="${esc(e.source)}" target="${esc(e.target)}" style="edgeStyle=none;html=0;endArrow=block;endFill=1;strokeColor=${e.red?C.red:C.muted};dashed=${['control','zoom'].includes(e.role)?1:0};exitX=${ep[0]};exitY=${ep[1]};entryX=${ip[0]};entryY=${ip[1]};exitPerimeter=0;entryPerimeter=0;" edge="1" parent="1"><mxGeometry relative="1" as="geometry">${via.length?'<Array as="points">'+via.map(([x,y])=>`<mxPoint x="${x}" y="${y}"/>`).join('')+'</Array>':''}</mxGeometry></mxCell>`;}
 s.labels.forEach((l,i)=>{cells+=`<mxCell id="label-${i}" value="${esc(l.text)}" style="text;html=0;fontSize=${l.fs};fontColor=${l.color};align=${l.anchor==='middle'?'center':l.anchor==='end'?'right':'left'};verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="${l.x-(l.anchor==='middle'?300:l.anchor==='end'?600:0)}" y="${l.y-l.fs}" width="600" height="${l.fs*1.8}" as="geometry"/></mxCell>`;});
 return `<?xml version="1.0" encoding="UTF-8"?><mxfile host="local"><diagram name="${esc(s.title)}"><mxGraphModel page="1" pageWidth="${s.width}" pageHeight="${s.height}"><root>${cells}</root></mxGraphModel></diagram></mxfile>`;
}
function audit(s){
 const errors=[];for(const n of s.nodes){if(n.x<0||n.y<0||n.x+n.w>s.width+1||n.y+n.h>s.height+1)errors.push('Node outside canvas: '+n.id);}
 for(const e of s.edges){const ps=s.path(e);for(let i=1;i<ps.length;i++)if(ps[i][0]!==ps[i-1][0]&&ps[i][1]!==ps[i-1][1])errors.push('Diagonal edge: '+e.id);}
 try{assertEnglishLabels(s);}catch(e){errors.push(e.message);}
 return{ok:!errors.length,errors,node_count:s.nodes.length,edge_count:s.edges.length,orthogonal:true,visual_review_required:true};
}
return{validate,render,compare,svg,drawio,Scene,colors:C,clone,moduleGraph,backbone,orthogonalPath,audit};
});
