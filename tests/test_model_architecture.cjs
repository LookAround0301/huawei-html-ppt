'use strict';
// Synthetic topologies only: these tests do not certify a model backend or visual quality.
const test = require('node:test');
const assert = require('node:assert/strict');
const A = require('../skills/huawei-html-ppt/scripts/model_architecture.cjs');

function model() {
  return {
    schema_version: 1, id: 'synthetic', name: 'Synthetic model', layers: 4,
    default_attention: 'attention', default_ffn: 'ffn',
    modules: {
      attention: {kind: 'gqa', label: 'Grouped attention', heads: 8},
      ffn: {kind: 'moe', label: 'Routed FFN', experts: 8, active: 2, shared: 1,
        params: {hidden: 256, latent: 128}},
    },
    architecture: {stages: [{id: 'main', repeat: 2,
      blocks: [{attention: 'attention', ffn: 'ffn', repeat: 2}]}]},
  };
}

function assertOrthogonal(points) {
  assert.ok(points.length >= 2);
  for (let i = 1; i < points.length; i++) {
    assert.ok(points[i][0] === points[i-1][0] || points[i][1] === points[i-1][1]);
    assert.notDeepEqual(points[i], points[i-1]);
  }
}

test('model validation checks layer counts, references and router constraints', () => {
  assert.deepEqual(A.validate(model()), []);
  for (const mutate of [
    m => {m.layers = 5;},
    m => {m.architecture.stages[0].blocks[0].attention = 'missing';},
    m => {m.modules.ffn.active = 9;},
    m => {m.modules.attention = {kind: 'dsa', label: 'Sparse attention', top_k: 8};},
  ]) {
    const m = model(); mutate(m); assert.ok(A.validate(m).length > 0);
  }
});

test('all port orientations and explicit waypoints produce orthogonal paths', () => {
  for (const source of ['n', 's', 'e', 'w', [1, 0.3]]) {
    for (const target of ['n', 's', 'e', 'w', [0, 0.7]]) {
      for (const via of [[], [[180, 40], [260, 210]]]) {
        const points = A.orthogonalPath([80, 100], [400, 250], source, target, via);
        assert.deepEqual(points[0], [80, 100]);
        assert.deepEqual(points.at(-1), [400, 250]);
        assertOrthogonal(points);
      }
    }
  }
});

test('SVG and draw.io preserve the same endpoints and route waypoints', () => {
  const s = new A.Scene(600, 400, 'Execution');
  s.node('h', 10, 70, 80, 70, 'h', {shape: 'label'});
  s.node('op', 350, 200, 180, 60, 'Fused op', {sub: '[T, H] -> [T, N, D]'});
  s.edge('h', 'op', {sourcePort: 'e', targetPort: 'w', via: [[150, 105], [150, 230]]});
  const points = s.path(s.edges[0]), xml = A.drawio(s);
  assert.ok(A.svg(s).includes('points="' + points.map(p => p.join(',')).join(' ') + '"'));
  for (const [x, y] of points.slice(1, -1)) assert.ok(xml.includes(`<mxPoint x="${x}" y="${y}"/>`));
  const cell = xml.match(/<mxCell id="edge-0"[^>]+>/)[0];
  const number = name => Number(cell.match(new RegExp(name + '=([^;]+);'))[1]);
  for (const [id, point, prefix] of [['h', points[0], 'exit'], ['op', points.at(-1), 'entry']]) {
    const n = s.get(id);
    assert.ok(Math.abs(n.x + n.w * number(prefix + 'X') - point[0]) < 0.001);
    assert.ok(Math.abs(n.y + n.h * number(prefix + 'Y') - point[1]) < 0.001);
  }
  const labelWidth = s.port('h', 'e')[0] - s.port('h', 'w')[0];
  assert.ok(labelWidth > 0 && labelWidth < s.get('h').w / 2);
});

test('semantic modules keep data, routing and cache paths with plain I/O labels', () => {
  const modules = [
    {kind: 'mla', label: 'MLA', params: {q_rank: 64, kv_rank: 32}},
    {kind: 'dsa', label: 'DSA', top_k: 8, index_heads: 2, index_dim: 16},
    {kind: 'kda', label: 'KDA'}, model().modules.ffn,
    {kind: 'dense', label: 'Dense', params: {hidden: 256, intermediate: 512}},
    {kind: 'gqa', label: 'GQA', heads: 8},
    {kind: 'residual', label: 'Residual', block_size: 2},
  ];
  for (const mod of modules) {
    const s = new A.Scene(1100, 380, mod.label);
    A.moduleGraph(s, mod, mod.kind, {x: 20, y: 20, w: 1000, h: 300});
    assert.ok(A.audit(s).ok, JSON.stringify(A.audit(s)));
    assert.equal(s.nodes.find(n => n.label === 'h').shape, 'label');
    assert.ok(s.nodes.every(n => n.shape !== 'tensor'));
    for (const e of s.edges) assertOrthogonal(s.path(e));
    const svg = A.svg(s), xml = A.drawio(s);
    assert.ok(!xml.includes('cylinder'));
    assert.ok(!svg.includes('<ellipse') || s.nodes.some(n => n.shape === 'operator'));
    if (mod.kind === 'kda') {
      assert.equal(s.nodes.filter(n => n.shape === 'memory').length, 2);
      for (const role of ['read', 'write']) assert.equal(s.edges.filter(e => e.role === role).length, 2);
    }
    if (mod.kind === 'moe') {
      assert.ok(s.edges.some(e => e.source.endsWith('.shared') && e.target.endsWith('.sum')));
      assert.ok(s.edges.some(e => e.source.endsWith('.top') && e.target.endsWith('.experts')));
    }
  }
});

test('exports escape XML and reject Chinese in every visible label location', () => {
  const s = new A.Scene(300, 180, 'A & B');
  s.node('a', 20, 40, 200, 60, 'Q < K & V', {sub: '[T, H] -> [T, D]'});
  for (const output of [A.svg(s), A.drawio(s)]) {
    assert.ok(output.includes('A &amp; B'));
    assert.ok(output.includes('Q &lt; K &amp; V'));
  }
  for (const mutate of [
    x => {x.title = '标题';}, x => {x.nodes[0].label = '节点';},
    x => {x.nodes[0].sub = '维度';}, x => {x.text(10, 10, '注释');},
    x => {x.frame('f', 0, 0, 100, 100, '分组');},
  ]) {
    const bad = new A.Scene(300, 180, 'Test'); bad.node('a', 10, 10, 100, 40, 'Input'); mutate(bad);
    assert.throws(() => A.svg(bad), /Chinese diagram labels/);
    assert.throws(() => A.drawio(bad), /Chinese diagram labels/);
    assert.equal(A.audit(bad).ok, false);
  }
});

test('audit reports bounds and always requires a separate visual review', () => {
  const s = A.render(model());
  assert.equal(A.audit(s).ok, true);
  assert.equal(A.audit(s).visual_review_required, true);
  s.node('outside', 1490, 10, 50, 50, 'Outside');
  assert.equal(A.audit(s).ok, false);
  assert.ok(A.audit(s).errors.some(e => e.includes('outside')));
});
