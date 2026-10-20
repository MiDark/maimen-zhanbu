/* 麦当劳 MCP 只读客户端 —— 网页版（浏览器侧）
 *
 * 与 scripts/mcp_client.py、miniprogram/utils/mcd_api.js 同口径（勿单改一端）：
 *   同样五个只读工具、同样的载荷解析（先抽载荷再判断）、同样的降级。
 *   只调查询类工具，绝不触发下单 / 领券 / 抽奖等任何写操作。
 *
 * 为什么不能直连 mcp.mcd.cn：该端点不返回 Access-Control-Allow-Origin，
 * 浏览器 fetch 必被拦。所以请求先打到自建中转（tools/mcp-proxy-worker.js），
 * 由中转补 CORS 再转发。没有中转地址时 consult() 直接返回 {ok:false}。
 *
 * Token 只存在本机浏览器（localStorage），由用户自己填；页面不会把 Token
 * 发给除中转以外的任何地方。
 */

(function (global) {
  "use strict";

  var PROTOCOL = "2024-11-05";

  /* 与 Python 端 READONLY_TOOLS 一致：只允许这些查询工具 */
  var READONLY_TOOLS = [
    "query-my-account", "campaign-calendar", "available-coupons",
    "query-store-coupons", "query-my-coupons", "query-nearby-stores",
    "list-nutrition-foods", "now-time-info", "query-lottery-info", "query-my-prizes"
  ];

  /* ───────────────────────── 传输层 ───────────────────────── */
  function requestRaw(proxyUrl, token, payload, timeoutMs) {
    var ctrl = typeof AbortController === "function" ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctrl) ctrl.abort(); }, timeoutMs || 20000);
    return fetch(proxyUrl, {
      method: "POST",
      signal: ctrl ? ctrl.signal : undefined,
      headers: {
        "Content-Type": "application/json",
        "x-mcd-token": token,
        "MCP-Protocol-Version": PROTOCOL
      },
      body: JSON.stringify(payload)
    }).then(function (res) {
      clearTimeout(timer);
      if (res.status >= 400) throw new Error("中转/上游 HTTP " + res.status);
      return res.text();
    }, function (err) {
      clearTimeout(timer);
      throw new Error("中转不可达：" + ((err && err.message) || "网络错误"));
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

  function callTool(proxyUrl, token, name, args, rid) {
    if (READONLY_TOOLS.indexOf(name) < 0) {
      return Promise.reject(new Error("仅允许只读工具，拒绝调用：" + name));
    }
    return requestRaw(proxyUrl, token, {
      jsonrpc: "2.0",
      id: rid || 1,
      method: "tools/call",
      params: { name: name, arguments: args || {} }
    }).then(function (raw) {
      return extractText(parseResponse(raw));
    });
  }

  /* mcp.mcd.cn 偶发 502：重试两次基本能过（与 Python 端同参数） */
  function callRetry(proxyUrl, token, name, args, tries) {
    var n = tries || 3;
    function attempt(i) {
      return callTool(proxyUrl, token, name, args, i + 1).then(function (txt) {
        if (txt.indexOf("查询失败") < 0) return txt;
        if (i < n - 1) {
          return new Promise(function (res) { setTimeout(res, 1200); })
            .then(function () { return attempt(i + 1); });
        }
        return txt;
      });
    }
    return attempt(0);
  }

  /* ───────────────────────── 载荷解析（与 Python 同式） ───────────────────────── */
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
   * 返回结构与 mcd_data.js 快照同形（页面渲染零改动可换源）：
   *   { ok, city, keyword, fetched_at, live, now, points, stores, coupons, campaigns }
   */
  function consult(proxyUrl, token, city, keyword) {
    if (!proxyUrl) return Promise.resolve({ ok: false, reason: "未填写中转地址" });
    if (!token) return Promise.resolve({ ok: false, reason: "未填写 Token" });

    var out = { ok: false, demo: false, live: true, city: city || "", keyword: keyword || "" };
    var storeArgs = { beType: 1, searchType: 2 };
    if (keyword) storeArgs.keyword = keyword;
    if (city) storeArgs.city = city;

    return callRetry(proxyUrl, token, "now-time-info").then(function (t) {
      out.now = nowFrom(t);
      return callRetry(proxyUrl, token, "query-my-account");
    }).then(function (t) {
      out.points = pointsFrom(t);
      return (keyword || city) ? callRetry(proxyUrl, token, "query-nearby-stores", storeArgs) : Promise.resolve("");
    }).then(function (t) {
      out.stores = storesFrom(t);
      return callRetry(proxyUrl, token, "available-coupons");
    }).then(function (t) {
      out.coupons = parseCoupons(t).slice(0, 8);
      return callRetry(proxyUrl, token, "campaign-calendar");
    }).then(function (t) {
      out.campaigns = parseCampaigns(t).slice(0, 6);
      var n = 0;
      ["points", "stores", "coupons", "campaigns"].forEach(function (k) {
        var v = out[k];
        if (v && (v instanceof Array ? v.length : Object.keys(v).length)) n++;
      });
      out.ok = n >= 2;
      out.fetched_at = (out.now && out.now.datetime) || fmtNow();
      if (!out.ok) out.reason = "只读接口均未取到真实数据（Token 失效、限流或中转异常）";
      return out;
    }).catch(function (err) {
      return { ok: false, live: true, demo: false, reason: (err && err.message) || "MCP 请求失败" };
    });
  }

  function fmtNow() {
    var d = new Date();
    function p(n) { return ("0" + n).slice(-2); }
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) +
      " " + p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
  }

  global.MCD_LIVE = {
    READONLY_TOOLS: READONLY_TOOLS,
    consult: consult,
    callTool: callTool,
    parseCoupons: parseCoupons,
    parseCampaigns: parseCampaigns
  };
})(typeof window !== "undefined" ? window : this);
