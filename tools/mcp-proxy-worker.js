/**
 * 麦当劳 MCP 中转 —— Cloudflare Worker 备选版（主用方案见 server/server.js）
 *
 * 主方案：`server/server.js`（零依赖 Node 单文件），已用 WorkBuddy 应用托管部署，
 *  网页版开页即实时，不用填 Token。本文件是同一中转的轻量备选，适合没有 Node 托管的环境。
 *
 * 为什么需要它：
 *   mcp.mcd.cn 不返回任何 `Access-Control-Allow-Origin` 头（OPTIONS 预检直接 403），
 *   浏览器端即使拿到 Token 也发不出请求。这个 Worker 只做一件事——把请求转发过去，
 *   并替服务端补上 CORS 头。
 *
 * 部署（任选其一）：
 *   1) 网页版：https://workers.cloudflare.com → Create Worker → 粘贴本文件 → Deploy
 *   2) 命令行：npm i -g wrangler && wrangler deploy tools/mcp-proxy-worker.js --name mcd-proxy
 *   部署完拿到形如 https://mcd-proxy.<你的子域>.workers.dev 的地址，填进网页版「中转地址」。
 *
 * 安全说明：
 *   - Token 由浏览器放在 `x-mcd-token` 头里透传，Worker 不写日志、不落库（本版不内置 Token）。
 *   - 想限定只有自己的页面能用：在 Worker 设置里加环境变量
 *     ALLOW_ORIGIN = https://midark.github.io
 *   - 只允许 POST，且只转发到 mcp.mcd.cn，不做任意 URL 代理（避免被当开放代理用）。
 *   - 与 server/server.js 的差别：不做方法/工具白名单，只透传——要白名单就用 Node 版。
 */

const MCP_URL = "https://mcp.mcd.cn";
const MAX_BODY = 32 * 1024;

export default {
  async fetch(request, env) {
    const allowOrigin = (env && env.ALLOW_ORIGIN) || "*";
    const cors = {
      "Access-Control-Allow-Origin": allowOrigin,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "content-type, x-mcd-token, mcp-protocol-version",
      "Access-Control-Max-Age": "86400",
      Vary: "Origin",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }
    if (request.method !== "POST") {
      return json({ error: "只支持 POST" }, 405, cors);
    }

    const token = (request.headers.get("x-mcd-token") || "").trim();
    if (!token) return json({ error: "缺少 x-mcd-token" }, 400, cors);

    const body = await request.text();
    if (!body || body.length > MAX_BODY) {
      return json({ error: "请求体为空或过大" }, 413, cors);
    }

    let upstream;
    try {
      upstream = await fetch(MCP_URL, {
        method: "POST",
        headers: {
          Authorization: "Bearer " + token,
          "Content-Type": "application/json",
          Accept: request.headers.get("accept") || "application/json, text/event-stream",
          "MCP-Protocol-Version": request.headers.get("mcp-protocol-version") || "2024-11-05",
        },
        body,
      });
    } catch (err) {
      return json({ error: "上游请求失败：" + String(err && err.message) }, 502, cors);
    }

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: {
        ...cors,
        "Content-Type": upstream.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  },
};

function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });
}
