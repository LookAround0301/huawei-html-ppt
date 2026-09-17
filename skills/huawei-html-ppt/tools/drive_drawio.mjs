// 通过 stdio JSON-RPC 驱动 draw.io mcp-server（无 MCP 工具时的后备通道）：
//   node drive_drawio.mjs 图.drawio       # start_session + create_new_diagram 后挂住
// server 来源：本目录 drawio-server/dist/index.js（内置离线），缺失时回退 npx。
// 端口：默认 6002，被占用时设 PORT 环境变量。
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const localServer = join(here, 'drawio-server', 'dist', 'index.js');
const xmlPath = process.argv[2];
if (!xmlPath) {
  console.error('usage: node drive_drawio.mjs <diagram.drawio>');
  process.exit(1);
}
const xml = readFileSync(xmlPath, 'utf8');

let child;
if (existsSync(localServer)) {
  child = spawn(process.execPath, [localServer], { stdio: ['pipe', 'pipe', 'pipe'] });
} else {
  // Windows 下 npx 是 .cmd；跨平台走 cmd /c
  const isWin = process.platform === 'win32';
  const cmd = isWin ? 'cmd' : 'npx';
  const args = isWin ? ['/c', 'npx', '@next-ai-drawio/mcp-server@latest'] : ['@next-ai-drawio/mcp-server@latest'];
  child = spawn(cmd, args, { stdio: ['pipe', 'pipe', 'pipe'] });
}

const rl = createInterface({ input: child.stdout });
const pending = new Map();
let nextId = 1;

function send(obj) {
  child.stdin.write(JSON.stringify(obj) + '\n');
}
function request(method, params) {
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    send({ jsonrpc: '2.0', id, method, params });
    setTimeout(() => {
      if (pending.has(id)) {
        pending.delete(id);
        reject(new Error(`timeout waiting for ${method}`));
      }
    }, 60000);
  });
}

rl.on('line', (line) => {
  line = line.trim();
  if (!line) return;
  let msg;
  try { msg = JSON.parse(line); } catch { return; }
  if (msg.id !== undefined && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
  }
});
child.stderr.on('data', (d) => process.stderr.write(`[server] ${d}`));
child.on('exit', (code) => { console.error(`server exited: ${code}`); process.exit(1); });

const init = await request('initialize', {
  protocolVersion: '2024-11-05',
  capabilities: {},
  clientInfo: { name: 'cli-driver', version: '1.0.0' },
});
console.log('initialized, server:', init.serverInfo.name, init.serverInfo.version);
send({ jsonrpc: '2.0', method: 'notifications/initialized' });

const s = await request('tools/call', { name: 'start_session', arguments: {} });
console.log(s.content.map(c => c.text).join('\n'));

const r = await request('tools/call', { name: 'create_new_diagram', arguments: { xml } });
console.log(r.isError ? 'ERROR: ' + r.content.map(c => c.text).join('') : 'diagram created: ' + r.content.map(c => c.text).join('').slice(0, 200));

console.log('KEEPALIVE - browser preview active');
setInterval(() => {}, 1 << 30);
