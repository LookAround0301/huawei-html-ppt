'use strict';
// Synthetic fragments only; no model, performance or visual-support claims.
const test = require('node:test');
const assert = require('node:assert/strict');
const A = require('../skills/huawei-html-ppt/scripts/model_architecture.cjs');
const F = require('../skills/huawei-html-ppt/scripts/feature_overlay.cjs');

function fixture() {
  const s = new A.Scene(1150,430,'Synthetic feature');
  s.node('attention',20,75,160,55,'Attention');
  s.node('other',20,190,160,55,'Other layer');
  const spec = {id:'phase',title:'Decode / group size G',anchor:'attention',x:240,y:20,w:880,h:220,
    scopeVia:[[210,102.5],[210,44]],
    nodes:[
      {id:'q',label:'Q projection',x:20,y:70,w:150,h:60,change:'existing',kind:'compute'},
      {id:'exchange',label:'CP AllGather\nQ heads',x:220,y:70,w:170,h:60,change:'added',kind:'communication',
        collective:'AllGather',group:'CP',tensor:'Q heads',source_refs:['synthetic:exchange']},
      {id:'compute',label:'Attention kernel',x:440,y:70,w:180,h:60,change:'existing',kind:'compute'},
      {id:'merge',label:'Fused merge',x:670,y:70,w:185,h:60,change:'added',kind:'merge',source_refs:['synthetic:merge']},
    ],
    edges:[{source:'q',target:'exchange'},{source:'exchange',target:'compute'},{source:'compute',target:'merge'}],
    paths:[['q','exchange','compute','merge']],
  };
  return {s,spec};
}

test('overlay associates only its declared model module and preserves increments', () => {
  const {s,spec}=fixture(),before=s.nodes.length;
  const out=F.addFeatureLane(s,spec),record=out.record;
  assert.equal(s.nodes.length,before+spec.nodes.length+1);
  assert.equal(record.anchor,'attention');
  assert.ok(!s.edges.some(e=>e.source==='other'||e.target==='other'));
  const leader=s.edges.find(e=>e.id===record.scope_edge);
  assert.equal(leader.role,'control');
  assert.equal(leader.relation,'feature-scope');
  assert.equal(s.get(out.nodes.q).fill,A.colors.blue);
  assert.equal(s.get(out.nodes.exchange).fill,A.colors.rose);
  assert.deepEqual(s.get(out.nodes.exchange).source_refs,['synthetic:exchange']);
  assert.equal(F.auditFeatureOverlays(s).ok,true);
  assert.equal(F.auditFeatureOverlays(s).visual_review_required,true);
  const xml=A.drawio(s),svg=A.svg(s);
  assert.ok(xml.includes('source="attention" target="phase.scope"'));
  assert.ok(xml.includes('source="phase.q" target="phase.exchange"'));
  assert.ok(svg.includes('data-source="phase.exchange" data-target="phase.compute"'));
});

test('communication omissions, bypasses and wrong groups fail after rendering', () => {
  for (const mutate of [
    s=>{s.edges=s.edges.filter(e=>!(e.source==='phase.exchange'&&e.target==='phase.compute'));},
    s=>{s.edges.find(e=>e.source==='phase.q').target='phase.compute';},
    s=>{s.get('phase.exchange').group='OTHER';},
    s=>{s.nodes=s.nodes.filter(n=>n.id!=='phase.merge');},
    s=>{s.edges.find(e=>e.relation==='feature-scope').role='data';},
  ]) {
    const {s,spec}=fixture();F.addFeatureLane(s,spec);mutate(s);
    assert.equal(F.auditFeatureOverlays(s).ok,false);
  }
});

test('new nodes need evidence and communication semantics before Scene mutation', () => {
  for (const mutate of [
    p=>{p.anchor='missing';},p=>{p.nodes[1].source_refs=[];},
    p=>{delete p.nodes[1].group;},p=>{delete p.nodes[1].tensor;},
    p=>{p.nodes[1].change='unknown';},p=>{p.nodes[1].label='通信';},
    p=>{p.edges[0].target='other';},p=>{p.nodes[1].x=870;},
  ]) {
    const {s,spec}=fixture(),before=JSON.stringify(s);mutate(spec);
    assert.throws(()=>F.addFeatureLane(s,spec),/Feature overlay/);
    assert.equal(JSON.stringify(s),before);
  }
});

test('phase lanes retain separate topology and never invent collectives', () => {
  const {s,spec}=fixture();F.addFeatureLane(s,spec);
  const other={...structuredClone(spec),id:'other-phase',title:'Prefill',y:245,h:170};
  other.nodes=[{id:'chunk',label:'Chunk kernel',x:20,y:60,w:180,h:60,kind:'compute',change:'replaced',source_refs:['synthetic:chunk']},
    {id:'out',label:'Output',x:300,y:60,w:180,h:60,kind:'compute',change:'existing'}];
  other.edges=[{source:'chunk',target:'out'}];other.paths=[['chunk','out']];
  F.addFeatureLane(s,other);
  assert.equal(s.nodes.filter(n=>n.role==='communication').length,1);
  assert.equal(s.get('other-phase.chunk').feature_change,'replaced');
  assert.equal(F.auditFeatureOverlays(s).components,2);
  assert.equal(F.auditFeatureOverlays(s).ok,true);
});

test('state dependency, shape and activation conditions survive component export', () => {
  const {s,spec}=fixture();
  spec.nodes.push({id:'state',label:'Local state',sub:'[N,H,D,D]',condition:'backend supported',
    x:440,y:150,w:220,h:65,kind:'state',change:'existing'});
  spec.edges.push({source:'state',target:'compute',sourcePort:'n',targetPort:'s',role:'read'});
  spec.paths.push(['state','compute']);
  F.addFeatureLane(s,spec);
  assert.equal(s.get('phase.state').shape,'memory');
  for (const out of [A.svg(s),A.drawio(s)]) {
    assert.ok(out.includes('[N,H,D,D]'));
    assert.ok(out.includes('backend supported'));
  }
  assert.equal(F.auditFeatureOverlays(s).ok,true);
  s.get('phase.state').condition='another backend';
  assert.equal(F.auditFeatureOverlays(s).ok,false);
});
