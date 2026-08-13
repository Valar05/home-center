'use strict';

const http = require('http');
const crypto = require('crypto');

const PORT = Number(process.env.PORT || 8080);
const API_KEY = String(process.env.GEMINI_API_KEY || '').trim();
const DEFAULT_MODEL = String(process.env.HC_GEMINI_MODEL || 'gemini-2.5-flash').trim();
const MAX_BODY = 128 * 1024;
const MAX_PROMPT = 48000;
const MAX_OUTPUT = Math.max(128, Math.min(Number(process.env.HC_GEMINI_MAX_OUTPUT_TOKENS || 4096), 8192));

function json(res, status, body) {
  const raw = Buffer.from(JSON.stringify(body));
  res.writeHead(status, {'content-type':'application/json; charset=utf-8','content-length':String(raw.length),'cache-control':'no-store'});
  res.end(raw);
}

function body(req) {
  return new Promise((resolve, reject) => {
    let size = 0; const chunks = [];
    req.on('data', chunk => { size += chunk.length; if (size > MAX_BODY) { reject(new Error('request_too_large')); req.destroy(); return; } chunks.push(chunk); });
    req.on('end', () => { try { resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {}); } catch { reject(new Error('invalid_json')); } });
    req.on('error', reject);
  });
}

function requestId() { return crypto.randomUUID(); }
function promptFrom(input) {
  const text = typeof input?.prompt === 'string' ? input.prompt.trim() : '';
  if (!text) throw new Error('prompt_required');
  if (text.length > MAX_PROMPT) throw new Error('prompt_too_large');
  return text;
}
function modelFrom(input) {
  const model = typeof input?.model === 'string' && input.model.trim() ? input.model.trim() : DEFAULT_MODEL;
  if (!/^gemini-[a-z0-9._-]+$/i.test(model)) throw new Error('invalid_model');
  return model;
}

async function runGemini(input) {
  if (!API_KEY) throw new Error('gemini_api_key_missing');
  const prompt = promptFrom(input);
  const model = modelFrom(input);
  const started = Date.now();
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(API_KEY)}`;
  const payload = {
    contents: [{role:'user', parts:[{text: prompt}]}],
    generationConfig: {temperature: Number.isFinite(Number(input.temperature)) ? Math.max(0, Math.min(Number(input.temperature), 1.5)) : 0.2, maxOutputTokens: MAX_OUTPUT}
  };
  const response = await fetch(url, {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify(payload), signal:AbortSignal.timeout(90000)});
  const raw = await response.text();
  let data = {}; try { data = raw ? JSON.parse(raw) : {}; } catch {}
  if (!response.ok) {
    const detail = String(data?.error?.message || raw || `HTTP ${response.status}`).slice(0, 1800);
    const error = new Error(`gemini_http_${response.status}:${detail}`); error.status = response.status; throw error;
  }
  const text = (data.candidates || []).flatMap(c => c?.content?.parts || []).map(p => p?.text || '').join('').trim();
  return {
    schema:'home-center.gemini-worker.receipt.v1', ok:true, requestId:requestId(), model,
    elapsedMs:Date.now()-started, text,
    usage:data.usageMetadata || {}, finishReason:data.candidates?.[0]?.finishReason || '',
    execution:'google-generative-language-api', machineBodyUsed:false, sshUsed:false, ipv6Required:false
  };
}

async function handler(req, res) {
  if (req.method === 'GET' && req.url === '/health') {
    return json(res, 200, {schema:'home-center.gemini-worker.health.v1', ok:true, service:'home-center-gemini-free-worker', model:DEFAULT_MODEL, configured:Boolean(API_KEY), sshRequired:false, ipv6Required:false});
  }
  if (req.method === 'POST' && req.url === '/v1/run') {
    try { return json(res, 200, await runGemini(await body(req))); }
    catch (error) { const msg=String(error?.message||error); const status=msg==='prompt_required'||msg==='prompt_too_large'||msg==='invalid_model'||msg==='invalid_json'||msg==='request_too_large'?400:502; return json(res,status,{schema:'home-center.gemini-worker.receipt.v1',ok:false,error:msg.slice(0,2000),sshUsed:false,ipv6Required:false}); }
  }
  return json(res, 404, {ok:false,error:'not_found'});
}

if (require.main === module) http.createServer((req,res)=>handler(req,res)).listen(PORT, '0.0.0.0', () => console.log(`home-center-gemini-free-worker listening ${PORT}`));
module.exports = {handler, runGemini, promptFrom, modelFrom};
