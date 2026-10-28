'use strict';
// Small Scene fragment; it supplies no model facts or collective sequence.
const A = require('./model_architecture.cjs');
const revision = 1;
const changes = new Set(['existing', 'added', 'replaced']);
const kinds = new Set(['compute', 'communication', 'merge', 'state']);
const copy = value => JSON.parse(JSON.stringify(value));
const fail = message => { throw new Error('Feature overlay: ' + message); };
const english = value => { if (/\p{Script=Han}/u.test(String(value || ''))) fail('diagram labels must be English'); };
const fill = n => n.change === 'existing' ? (n.kind === 'state' ? A.colors.gray : A.colors.blue) : A.colors.rose;

function addFeatureLane(scene, spec) {
  const {id, title, anchor, x, y, w, h, nodes, edges, paths} = spec;
  if (typeof id !== 'string' || !id || !title || !anchor || !scene.ids.has(anchor)) fail('id, title and an existing backbone anchor are required');
  if (![x,y,w,h].every(Number.isFinite) || x < 0 || y < 0 || w <= 0 || h <= 50 || x+w > scene.width || y+h > scene.height) fail('lane must fit the canvas');
  if (!Array.isArray(nodes) || !nodes.length || !Array.isArray(edges) || !Array.isArray(paths) || !paths.length) fail('declare nodes, edges and required paths');
  english(title);
  const local = new Set(), ids = Object.create(null);
  for (const n of nodes) {
    if (typeof n.id !== 'string' || !n.id || local.has(n.id) || !n.label || !changes.has(n.change) || !kinds.has(n.kind)) fail('nodes need unique ids, labels, change and kind');
    if (![n.x,n.y,n.w,n.h].every(Number.isFinite) || n.x < 0 || n.y < 50 || n.w <= 0 || n.h <= 0 || n.x+n.w > w || n.y+n.h > h) fail('node must fit below the lane title: ' + n.id);
    if (n.change !== 'existing' && (!Array.isArray(n.source_refs) || !n.source_refs.length || n.source_refs.some(r => typeof r !== 'string' || !r.trim()))) fail('added/replaced nodes need source references: ' + n.id);
    if (n.kind === 'communication' && (!n.collective || !n.group || !n.tensor)) fail('communication needs collective, group and tensor: ' + n.id);
    for (const value of [n.label,n.sub,n.condition,n.collective,n.group,n.tensor]) english(value);
    local.add(n.id); ids[n.id] = id + '.' + n.id;
  }
  const scope = id + '.scope';
  if (new Set([scope,...Object.values(ids)]).size !== nodes.length+1 || [scope,...Object.values(ids)].some(k => scene.ids.has(k)) || scene.frames.some(f => f.id === id)) fail('duplicate component id');
  for (const e of edges) {
    if (!local.has(e.source) || !local.has(e.target)) fail('edges must reference this lane');
    if (e.via && e.via.some(p => !Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite))) fail('invalid relative waypoint');
  }
  for (const p of paths) if (!Array.isArray(p) || p.length < 2 || p.some(k => !local.has(k))) fail('required paths must reference this lane');
  if (spec.scopeVia && spec.scopeVia.some(p => !Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite))) fail('invalid absolute scope waypoint');

  // Scope is a dashed association, never an extra model data-flow edge.
  scene.frame(id, x, y, w, h, '', {fill:'#FBFCFD'});
  scene.node(scope, x+16, y+10, spec.titleWidth || w-32, 28, title, {shape:'label',fs:24,bold:true});
  scene.edge(anchor, scope, {sourcePort:spec.anchorPort || 'e',targetPort:'w',
    via:spec.scopeVia || [],role:'control',relation:'feature-scope'});
  const scopeEdge = scene.edges.at(-1).id;
  for (const n of nodes) {
    const sub = [n.sub,n.condition].filter(Boolean).join(' / ');
    scene.node(ids[n.id], x+n.x, y+n.y, n.w, n.h, n.label, {
      fs:n.fs || 22, sub:sub || undefined, shape:n.kind === 'state' ? 'memory' : 'box',
      fill:fill(n), role:n.kind, feature_change:n.change, feature_lane:id,
      source_refs:n.source_refs || [], condition:n.condition || null,
      collective:n.collective || null, group:n.group || null, tensor:n.tensor || null,
    });
  }
  const edgeRecords = [];
  for (const e of edges) {
    const opt = {sourcePort:e.sourcePort || 'e',targetPort:e.targetPort || 'w',
      via:(e.via || []).map(p => [x+p[0],y+p[1]]),role:e.role || 'data'};
    scene.edge(ids[e.source],ids[e.target],opt);
    edgeRecords.push(copy(scene.edges.at(-1)));
  }
  const record = {component:'feature-backbone-overlay',revision,id,anchor,scope,scope_edge:scopeEdge,
    nodes:copy(nodes),ids,edges:edgeRecords,paths:paths.map(p => p.map(k => ids[k])),params:copy(spec)};
  (scene.feature_overlays ||= []).push(record);
  return {scope,nodes:ids,record};
}

function auditFeatureOverlays(scene) {
  const errors = [];
  try { errors.push(...A.audit(scene).errors); } catch (e) { errors.push(e.message); }
  const byId = new Map(scene.nodes.map(n => [n.id,n]));
  for (const use of scene.feature_overlays || []) {
    const scope = scene.edges.find(e => e.id === use.scope_edge);
    if (!byId.has(use.anchor) || !byId.has(use.scope) || !scope || scope.source !== use.anchor || scope.target !== use.scope || scope.role !== 'control' || scope.relation !== 'feature-scope') errors.push('Invalid backbone scope: ' + use.id);
    for (const expected of use.nodes) {
      const n = byId.get(use.ids[expected.id]);
      if (!n || n.feature_change !== expected.change || n.role !== expected.kind || n.fill !== fill(expected)) errors.push('Missing/changed operator: ' + use.ids[expected.id]);
      else if (n.collective !== (expected.collective || null) || n.group !== (expected.group || null) || n.tensor !== (expected.tensor || null) || n.condition !== (expected.condition || null) || JSON.stringify(n.source_refs) !== JSON.stringify(expected.source_refs || [])) errors.push('Changed operator semantics: ' + n.id);
    }
    for (const expected of use.edges) {
      const edge = scene.edges.find(e => e.id === expected.id);
      if (!edge || edge.source !== expected.source || edge.target !== expected.target || edge.role !== expected.role) errors.push('Missing/changed feature edge: ' + expected.id);
    }
    const members = new Set(Object.values(use.ids));
    const reachable = (a,b) => {
      const queue=[a],seen=new Set(queue);
      for (const current of queue) for (const e of scene.edges) {
        if (e.source !== current || !members.has(e.target) || e.role === 'control' || e.relation === 'feature-scope') continue;
        if (e.target === b) return true;
        if (!seen.has(e.target)) { seen.add(e.target); queue.push(e.target); }
      }
      return false;
    };
    for (const p of use.paths) for (let i=1;i<p.length;i++) if (!reachable(p[i-1],p[i])) errors.push('Broken feature path: ' + p[i-1] + ' -> ' + p[i]);
  }
  return {ok:!errors.length,errors,components:(scene.feature_overlays || []).length,visual_review_required:true};
}

module.exports = {addFeatureLane,auditFeatureOverlays,revision};
