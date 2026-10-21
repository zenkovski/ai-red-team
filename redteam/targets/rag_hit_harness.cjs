// Runs RAG-Demo/site/api/hit.js locally with a fake Redis (fetch stub). Reads one JSON case on stdin, prints one JSON result.
// Nothing leaves the machine: global fetch is replaced before hit.js is loaded.
const path = require("path");
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const calls = [];
global.fetch = async (url, opts) => { calls.push({ url, cmds: JSON.parse(opts.body) }); return { ok: true, json: async () => [] }; };
process.env.KV_REST_API_URL = "https://fake-redis.invalid";
process.env.KV_REST_API_TOKEN = "fake-token";
const handler = require(path.join(input.siteApiDir, "hit.js"));
const res = { statusCode: 0, headers: {}, ended: false, setHeader(k, v) { this.headers[k] = v; }, end() { this.ended = true; } };
const req = { method: input.method || "POST", headers: input.headers || {}, body: input.body };
(async () => {
  let err = null;
  try { await handler(req, res); } catch (e) { err = String((e && e.stack) || e); }
  console.log(JSON.stringify({ status: res.statusCode, ended: res.ended, store_calls: calls.length, calls, error: err }));
  process.exit(0);
})();
