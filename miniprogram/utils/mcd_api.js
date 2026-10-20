/* 麦当劳 MCP 只读客户端 —— 小红书小程序端
 *
 * 与 scripts/mcp_client.py 同口径（勿单改一端）：
 *   POST https://mcp.mcd.cn（Stateless Streamable HTTP，JSON-RPC tools/call）
 *   同样五个只读工具、同样的载荷解析（先抽载荷再判断）、同样自带降级。
 *   只调查询类工具，绝不触发下单 / 领券 / 抽奖等任何写操作。
 *
 * Token 从 config/token.js 注入（该文件不入公开仓库，见 .gitignore）。
 * 没有 Token、请求失败或解析不出数据时，consult() 返回 {ok:false}，
 * 页面自动退回内置快照（data/mcd_real.js），卦照常算。
 */

var MCP_URL = "https://mcp.mcd.cn";
var PROTOCOL = "2024-11-05";

/* 与 Python 端 READONLY_TOOLS 一致：只允许这些查询工具 */
var READONLY_TOOLS = [
  "query-my-account", "campaign-calendar", "available-coupons",
  "query-store-coupons", "query-my-coupons", "query-nearby-stores",
  "list-nutrition-foods", "now-time-info", "query-lottery-info", "query-my-prizes"
];

/* ───────────────────────── 传输层 ───────────────────────── */
function requestRaw(payload, token, timeoutMs) {
  return new Promise(function (resolve, reject) {
    var api = (typeof xhs !== "undefined" && xhs.request) ? xhs.request
            : (typeof wx !== "undefined" && wx.request) ? wx.request : null;
    if (!api) { reject(new Error("小程序 request API 不可用")); return; }
    api({
      url: MCP_URL,
      method: "POST",
      timeout: timeoutMs || 15000,
      header: {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL
      },
      data: payload,
      success: function (res) {
        if (res.statusCode >= 400) {
          reject(new Error("MCP HTTP " + res.statusCode));
          return;
        }
        /* 有的运行时会把 JSON 自动解析成对象，统一转回字符串走同一套解析 */
        resolve(typeof res.data === "string" ? res.data : JSON.stringify(res.data));
      },
      fail: function (err) {
        reject(new Error((err && err.errMsg) || "request fail"));
      }
    });
  });
}

/* SSE（event:/data: 行）与纯 JSON 两种返回都认 */
function parseResponse(raw) {
  if (raw && (raw.indexOf("event:") === 0 || raw.indexOf("\ndata:") >= 0 || raw.indexOf("data:") === 0)) {
    var lines = raw.split("\n");
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].trim();
      if (line.indexOf("data:") === 0) {
        var chunk = line.slice(5).trim();
        if (chunk && chunk !== "[DONE]") {
          try { return JSON.parse(chunk); } catch (e) { /* 继续找下一行 */ }
        }
      }
    }
    return {};
  }
  try { return JSON.parse(raw); } catch (e) { return { raw: raw }; }
}

function extractText(result) {
  if (!result || typeof result !== "object") return "";
  var res = result.result || result;
  if (res && res.content && res.content.length) {
    var parts = [];
    for (var i = 0; i < res.content.length; i++) {
      var c = res.content[i];
      if (c && c.type === "text" && c.text) parts.push(c.text);
    }
    return parts.join("\n");
  }
  if (res && res.text) return res.text;
  try { return JSON.stringify(res); } catch (e) { return ""; }
}

function callTool(token, name, args, rid) {
  if (READONLY_TOOLS.indexOf(name) < 0) {
    return Promise.reject(new Error("仅允许只读工具，拒绝调用：" + name));
  }
  var payload = {
    jsonrpc: "2.0",
    id: rid || 1,
    method: "tools/call",
    params: { name: name, arguments: args || {} }
  };
  return requestRaw(payload, token).then(function (raw) {
    return extractText(parseResponse(raw));
  });
}

/* mcp.mcd.cn 偶发 502：重试两次基本能过（与 Python 端同参数） */
function callRetry(token, name, args, tries) {
  var n = tries || 3;
  function attempt(i) {
    return callTool(token, name, args, i + 1).then(function (txt) {
      if (txt.indexOf("查询失败") < 0) return txt;
      if (i < n - 1) {
        return new Promise(function (res) { setTimeout(res, 1500); })
          .then(function () { return attempt(i + 1); });
      }
      return txt;
    });
  }
  return attempt(0);
}

/* ───────────────────────── 载荷解析（与 Python 同式） ───────────────────────── */
/* 载荷一定以 {"success" 起头，取文本里最后一个能配平的 JSON 对象 */
function payloadJson(text) {
  if (!text) return null;
  var idx = text.lastIndexOf('{"success"');
  if (idx < 0) return null;
  var depth = 0;
  for (var i = idx; i < text.length; i++) {
    var ch = text.charAt(i);
    if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) {
        try { return JSON.parse(text.slice(idx, i + 1)); } catch (e) { return null; }
      }
    }
  }
  return null;
}

function stripTags(s) {
  return String(s || "").replace(/<[^>]+>/g, "").trim();
}

/* markdown 券列表「优惠券标题：X / 状态：Y」→ [{title,status}] */
function parseCoupons(text) {
  if (!text) return [];
  var out = [], cur = null;
  var lines = text.split("\n");
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].trim().replace(/\\$/, "").trim();
    var m = line.match(/优惠券标题[：:]\s*(.+)/);
    if (m) {
      if (cur) out.push(cur);
      cur = { title: stripTags(m[1]), status: "" };
      continue;
    }
    if (cur) {
      var ms = line.match(/状态[：:]\s*(\S+)/);
      if (ms) cur.status = ms[1].trim();
    }
  }
  if (cur) out.push(cur);
  return out.filter(function (c) { return c.title; });
}

/* 活动日历 markdown「#### 日期 tag / 活动标题**：X」→ [{date,tag,title}] */
function parseCampaigns(text) {
  if (!text) return [];
  var out = [], date = "", tag = "";
  var lines = text.split("\n");
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].trim();
    var mh = line.match(/^####\s*(\d{4}年\d{1,2}月\d{1,2}日)\s*(.*)$/);
    if (mh) { date = mh[1]; tag = (mh[2] || "").trim(); continue; }
    var mt = line.match(/活动标题\*\*[：:]\s*(.+)/);
    if (mt) {
      var title = stripTags(mt[1]).replace(/\\/g, "").trim();
      if (title) out.push({ date: date, tag: tag, title: title.slice(0, 48) });
    }
  }
  /* 同一活动会横跨多日返回两次：标题去重，「今日」优先 */
  var seen = {}, uniq = [];
  out.sort(function (a, b) {
    return ((a.tag || "").indexOf("今日") >= 0 ? 0 : 1) - ((b.tag || "").indexOf("今日") >= 0 ? 0 : 1);
  });
  for (var j = 0; j < out.length; j++) {
    if (!seen[out[j].title]) { seen[out[j].title] = 1; uniq.push(out[j]); }
  }
  return uniq;
}

function storesFrom(text, limit) {
  var d = payloadJson(text);
  if (!d || !d.success || !d.data || !d.data.length) return [];
  var out = [];
  var rows = d.data.slice(0, limit || 6);
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    out.push({
      name: r.storeName || "",
      address: r.address || "",
      distance: (r.distance === undefined || r.distance === null) ? null : r.distance,
      open: r.businessStartTime || "",
      close: r.businessEndTime || "",
      open_now: !!r.businessStatus,
      reservation: !!r.reservation
    });
  }
  return out;
}

function pointsFrom(text) {
  var d = payloadJson(text);
  if (!d || !d.success || !d.data) return null;
  var data = d.data;
  try {
    return {
      available: parseInt(data.availablePoint, 10) || 0,
      accumulative: parseInt(data.accumulativePoint, 10) || 0,
      expiring: parseInt(data.currentMouthExpirePoint, 10) || 0
    };
  } catch (e) { return null; }
}

function nowFrom(text) {
  var d = payloadJson(text);
  if (!d || !d.success || !d.data) return null;
  return { datetime: d.data.formatted || "", date: d.data.date || "", weekday: d.data.dayOfWeek || "" };
}

/* ───────────────────────── 对外：一次只读咨询 ─────────────────────────
 * 返回结构与 data/mcd_real.js 快照同形（页面渲染零改动可换源）：
 *   { ok, city, keyword, fetched_at, now, points, stores, coupons, campaigns }
 */
function consult(token, city, keyword) {
  if (!token) return Promise.resolve({ ok: false, reason: "未配置 MCD_MCP_TOKEN" });
  var out = { ok: false, demo: false, city: city || "", keyword: keyword || "" };

  var storeArgs = { beType: 1, searchType: 2 };
  if (keyword) storeArgs.keyword = keyword;
  if (city) storeArgs.city = city;

  return callRetry(token, "now-time-info").then(function (t) {
    out.now = nowFrom(t);
    return callRetry(token, "query-my-account");
  }).then(function (t) {
    out.points = pointsFrom(t);
    return (keyword || city) ? callRetry(token, "query-nearby-stores", storeArgs) : Promise.resolve("");
  }).then(function (t) {
    out.stores = storesFrom(t);
    return callRetry(token, "available-coupons");
  }).then(function (t) {
    out.coupons = parseCoupons(t).slice(0, 8);
    return callRetry(token, "campaign-calendar");
  }).then(function (t) {
    out.campaigns = parseCampaigns(t).slice(0, 6);
    var n = 0;
    ["now", "points", "stores", "coupons", "campaigns"].forEach(function (k) {
      if (out[k] && (!out[k].length || typeof out[k] === "object")) {
        if (out[k] instanceof Array ? out[k].length : Object.keys(out[k]).length) n++;
      }
    });
    out.ok = n >= 2;
    out.fetched_at = (out.now && out.now.datetime) || "";
    if (!out.ok) out.reason = "只读接口均未取到真实数据（可能限流或 Token 失效）";
    return out;
  }).catch(function () {
    return { ok: false, reason: "MCP 请求失败", demo: false };
  });
}

module.exports = {
  READONLY_TOOLS: READONLY_TOOLS,
  callTool: callTool,
  consult: consult,
  parseCoupons: parseCoupons,
  parseCampaigns: parseCampaigns,
  payloadJson: payloadJson
};
