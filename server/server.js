/**
 * 麦门占卜 · 麦当劳 MCP 只读中转（单文件 Node 服务，零依赖）
 *
 * 为什么需要它
 *   mcp.mcd.cn 不返回任何 Access-Control-Allow-Origin 头（预检 OPTIONS 直接 403），
 *   浏览器即使拿到 Token 也发不出请求。这个服务只做一件事：把 JSON-RPC 转发过去，
 *   并替上游补上 CORS 头。网页版（GitHub Pages）因此能直接查真实门店 / 券 / 积分。
 *
 * 接口
 *   GET  /health          → { ok, has_token, upstream, readonly_tools }
 *   POST /mcp             → 转发到 mcp.mcd.cn；请求头 x-mcd-token 可覆盖内置 Token
 *   OPTIONS /mcp          → CORS 预检 204
 *   GET  /                → 同上 health（给人工看）
 *
 * 安全边界（刻意做窄，避免被当开放代理 / 被拿去下单）
 *   1. 只转发到 mcp.mcd.cn，不接受任意 URL。
 *   2. 只放行 JSON-RPC 的 initialize / ping / tools/list / tools/call，
 *      且 tools/call 的 name 必须在只读白名单里 —— 下单、领券、抽奖一律 403。
 *   3. 请求体上限 32KB，单次上游 30s 超时，每 IP 10 分钟 90 次。
 *   4. 内置 Token 只用于只读查询；不写日志、不落库。想收紧可配 config.allowedOrigins。
 *
 * 启动：PORT=3000 node server.js
 */

const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");

const MCP_HOST = "mcp.mcd.cn";
const MCP_PATH = "/";
const PROTOCOL = "2024-11-05";
const MAX_BODY = 32 * 1024;
const UPSTREAM_TIMEOUT = 30000;
const RATE_WINDOW_MS = 10 * 60 * 1000;
const RATE_MAX = 90;

/* 与 scripts/mcp_client.py、web/mcd_live.js、miniprogram/utils/mcd_api.js 同一份白名单 */
const READONLY_TOOLS = [
  "query-my-account", "campaign-calendar", "available-coupons",
  "query-store-coupons", "query-my-coupons", "query-nearby-stores",
  "list-nutrition-foods", "now-time-info", "query-lottery-info", "query-my-prizes",
];
const ALLOW_METHODS = ["initialize", "notifications/initialized", "ping", "tools/list", "tools/call"];

/* ───────────── 配置 ───────────── */
let CONFIG = {};
try {
  CONFIG = JSON.parse(fs.readFileSync(path.join(__dirname, "config.json"), "utf8")) || {};
} catch (e) {
  CONFIG = {};
}
const SERVER_TOKEN = String(process.env.MCD_MCP_TOKEN || CONFIG.token || "").trim();
const ALLOWED_ORIGINS = Array.isArray(CONFIG.allowedOrigins) ? CONFIG.allowedOrigins : null;

/* ───────────── CORS ───────────── */
function corsHeaders(origin) {
  let allow = "*";
  if (ALLOWED_ORIGINS && ALLOWED_ORIGINS.length) {
    allow = ALLOWED_ORIGINS.indexOf(origin) >= 0 ? origin : ALLOWED_ORIGINS[0];
  }
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "content-type, x-mcd-token, mcp-protocol-version, accept",
    "Access-Control-Max-Age": "86400",
    "Access-Control-Expose-Headers": "content-type",
    Vary: "Origin",
  };
}

function sendJson(res, status, obj, origin) {
  const body = JSON.stringify(obj);
  res.writeHead(status, Object.assign({
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "Content-Length": Buffer.byteLength(body),
  }, corsHeaders(origin)));
  res.end(body);
}

/* ───────────── 限流 ───────────── */
const hits = new Map();
function rateLimited(ip) {
  const now = Date.now();
  const rec = hits.get(ip);
  if (!rec || now > rec.reset) {
    hits.set(ip, { n: 1, reset: now + RATE_WINDOW_MS });
    if (hits.size > 5000) {
      for (const [k, v] of hits) if (now > v.reset) hits.delete(k);
    }
    return false;
  }
  rec.n += 1;
  return rec.n > RATE_MAX;
}

function clientIp(req) {
  const fwd = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim();
  return fwd || (req.socket && req.socket.remoteAddress) || "unknown";
}

/* ───────────── 请求体 ───────────── */
function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on("data", (c) => {
      size += c.length;
      if (size > MAX_BODY) {
        reject(Object.assign(new Error("请求体过大"), { status: 413 }));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

/* ───────────── 转发 ───────────── */
function forward(body, token, clientAccept, clientProtocol) {
  return new Promise((resolve, reject) => {
    const payload = Buffer.from(body, "utf8");
    const req = https.request(
      {
        host: MCP_HOST,
        path: MCP_PATH,
        method: "POST",
        headers: {
          Authorization: "Bearer " + token,
          "Content-Type": "application/json",
          Accept: clientAccept || "application/json, text/event-stream",
          "MCP-Protocol-Version": clientProtocol || PROTOCOL,
          "Content-Length": payload.length,
        },
        timeout: UPSTREAM_TIMEOUT,
      },
      (up) => {
        const bufs = [];
        up.on("data", (c) => bufs.push(c));
        up.on("end", () =>
          resolve({
            status: up.statusCode || 502,
            contentType: up.headers["content-type"] || "application/json",
            text: Buffer.concat(bufs).toString("utf8"),
          })
        );
      }
    );
    req.on("timeout", () => req.destroy(new Error("上游超时")));
    req.on("error", reject);
    req.end(payload);
  });
}

/* ───────────── 路由 ───────────── */
const server = http.createServer(async (req, res) => {
  const origin = String(req.headers.origin || "");
  const url = String(req.url || "/").split("?")[0];

  if (req.method === "OPTIONS") {
    res.writeHead(204, corsHeaders(origin));
    res.end();
    return;
  }

  if (url === "/health" || url === "/") {
    sendJson(res, 200, {
      ok: true,
      service: "maimen-zhanbu mcp proxy",
      upstream: "https://" + MCP_HOST,
      has_token: !!SERVER_TOKEN,
      readonly_tools: READONLY_TOOLS,
      note: "只读转发：下单 / 领券 / 抽奖类调用会被拒绝",
    }, origin);
    return;
  }

  if (url !== "/mcp") {
    sendJson(res, 404, { error: "只有 /mcp 和 /health" }, origin);
    return;
  }

  if (req.method !== "POST") {
    sendJson(res, 405, { error: "只支持 POST" }, origin);
    return;
  }

  const ip = clientIp(req);
  if (rateLimited(ip)) {
    sendJson(res, 429, { error: "查得太快了，歇 10 分钟再来" }, origin);
    return;
  }

  let body;
  try {
    body = await readBody(req);
  } catch (err) {
    sendJson(res, err.status || 400, { error: err.message || "读取请求失败" }, origin);
    return;
  }
  if (!body) {
    sendJson(res, 400, { error: "请求体为空" }, origin);
    return;
  }

  let rpc;
  try {
    rpc = JSON.parse(body);
  } catch (e) {
    sendJson(res, 400, { error: "请求体不是合法 JSON" }, origin);
    return;
  }

  const method = rpc && rpc.method;
  if (ALLOW_METHODS.indexOf(method) < 0) {
    sendJson(res, 403, { error: "只允许只读方法，拒绝：" + method }, origin);
    return;
  }
  if (method === "tools/call") {
    const name = rpc.params && rpc.params.name;
    if (READONLY_TOOLS.indexOf(name) < 0) {
      sendJson(res, 403, { error: "只允许只读工具，拒绝：" + name }, origin);
      return;
    }
  }

  const token = String(req.headers["x-mcd-token"] || "").trim() || SERVER_TOKEN;
  if (!token) {
    sendJson(res, 401, { error: "没有可用 Token：请传 x-mcd-token，或在 server/config.json 配 token" }, origin);
    return;
  }

  let up;
  try {
    up = await forward(body, token, req.headers.accept, req.headers["mcp-protocol-version"]);
  } catch (err) {
    sendJson(res, 502, { error: "上游请求失败：" + ((err && err.message) || "未知") }, origin);
    return;
  }

  res.writeHead(up.status, Object.assign({
    "Content-Type": up.contentType,
    "Cache-Control": "no-store",
    "Content-Length": Buffer.byteLength(up.text),
  }, corsHeaders(origin)));
  res.end(up.text);
});

const PORT = Number(process.env.PORT || 3000);
server.listen(PORT, "0.0.0.0", () => {
  console.log("[mcp-proxy] listening on 0.0.0.0:" + PORT +
    (SERVER_TOKEN ? " (内置 Token 已就绪)" : " (未配置 Token，需客户端自带)"));
});
