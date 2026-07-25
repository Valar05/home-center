import http from 'node:http';
import {renderBundle} from './render_bundle.mjs';

function send(res, status, body) {
  res.writeHead(status, {'content-type': 'application/json'});
  res.end(JSON.stringify(body));
}

async function readJson(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {};
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === 'GET' && req.url === '/health') return send(res, 200, {ok: true, service: 'command-center-blender-render'});
    if (req.method === 'POST' && req.url === '/render/glb') {
      const body = await readJson(req);
      const result = await renderBundle(body);
      return send(res, result.ok ? 200 : 422, result);
    }
    return send(res, 404, {ok: false, error: 'not found'});
  } catch (err) {
    return send(res, err.status || 500, {ok: false, status: 'failed', failureKind: err.failureKind || 'transport', error: err.message || String(err)});
  }
});

server.listen(Number(process.env.PORT || 8080), '0.0.0.0', () => {
  console.log(JSON.stringify({ok: true, service: 'command-center-blender-render', port: Number(process.env.PORT || 8080)}));
});
