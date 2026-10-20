#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦当劳 MCP 只读客户端（纯标准库，零第三方依赖）。

仅调用 mcd-mcp 的**只读查询**工具，绝不触发任何写操作（下单/领券/抽奖等）。
Token 只从环境变量 MCD_MCP_TOKEN 读取，绝不落盘、绝不写进仓库。

调用链（Stateless Streamable HTTP）：
  POST https://mcp.mcd.cn
  Headers: Authorization: Bearer <TOKEN>, Content-Type: application/json,
           Accept: application/json, text/event-stream
  Body:   {"jsonrpc":"2.0","id":N,"method":"tools/call","params":{"name":工具,"arguments":{...}}}

## 返回形态（2026-10-20 实测）

麦当劳 MCP 有两类返回，必须分开解析，否则会把真实数据误判成噪音：

1. **JSON 类**：一段「# API Response Information / 字段说明」，末尾跟
   `{"success":true,...,"data":{...}}`。真实载荷在最后这个 JSON 里。
2. **Markdown 类**（`available-coupons` / `campaign-calendar` / `query-nearby-stores`
   的失败提示）：直接是可读文本，券是 `- 优惠券标题：X \\ 状态：Y` 的列表。

旧版把整段文本丢给 `_looks_real()` 判断，由于开头永远是 "API Response Information"，
真实数据 100% 被判为噪音 —— 这是「MCP 接了但界面上看不见」的根因。现在改为
**先抽载荷再判断**：抽不出结构化内容才算暂缺。
"""

import os
import re
import json
import urllib.request
import urllib.error

MCP_URL = "https://mcp.mcd.cn"
PROTOCOL = "2024-11-05"
SERVER = "mcd-mcp"

# 本项目使用的只读工具（决策辅助定位，规避一切写操作）
READONLY_TOOLS = [
    "query-my-account",
    "campaign-calendar",
    "available-coupons",
    "query-store-coupons",
    "query-my-coupons",
    "query-nearby-stores",
    "list-nutrition-foods",
    "now-time-info",
    "query-lottery-info",
    "query-my-prizes",
]


# ───────────────────────── 传输层 ─────────────────────────
def _post(token: str, payload: dict, timeout: int = 20) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(MCP_URL, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    req.add_header("MCP-Protocol-Version", PROTOCOL)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace") if e.fp else ""
        raise RuntimeError(f"MCP HTTP {e.code}: {body[:300]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"MCP 连接失败：{e.reason}")
    # 兼容 SSE（text/event-stream）与纯 JSON 两种返回
    if raw.lstrip().startswith("event:") or "\ndata:" in raw:
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[len("data:"):].strip()
                if chunk and chunk != "[DONE]":
                    try:
                        return json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _extract_text(result: dict) -> str:
    """从 MCP tools/call 的 result 中抽取可读文本（content[].text）。"""
    if not isinstance(result, dict):
        return ""
    res = result.get("result", result)
    if isinstance(res, dict) and "content" in res:
        parts = []
        for c in res["content"]:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
        return "\n".join(p for p in parts if p)
    if isinstance(res, dict) and "text" in res:
        return res["text"]
    return json.dumps(res, ensure_ascii=False)


def call_tool(token: str, name: str, arguments: dict = None, rid: int = 1) -> str:
    """调用单个只读工具，返回其原始文本；失败返回 `[查询失败]` 前缀串（便于降级）。"""
    if name not in READONLY_TOOLS:
        raise ValueError(f"仅允许只读工具，拒绝调用：{name}")
    payload = {
        "jsonrpc": "2.0",
        "id": rid,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }
    try:
        resp = _post(token, payload)
        return _extract_text(resp)
    except Exception as e:  # 任何失败都不阻断主流程，交由上层降级
        return f"[查询失败] {name}: {e}"


# ───────────────────────── 载荷解析 ─────────────────────────
def payload_json(text: str):
    """从「字段说明 + Original Response」包装里抽出真实 JSON。抽不到返回 None。"""
    if not text:
        return None
    # 载荷一定以 {"success" 起头，且是文本里最后一个能解析的 JSON 对象
    idx = text.rfind('{"success"')
    if idx < 0:
        return None
    depth, start = 0, idx
    for i in range(idx, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


_COUPON_FIELD = re.compile(r"优惠券标题[：:]\s*(.+)")
_STATUS_FIELD = re.compile(r"状态[：:]\s*(\S+)")


def payload_coupons(text: str) -> list:
    """解析 markdown 券列表 → [{title, status}]。"""
    if not text:
        return []
    out, cur = [], None
    for raw in text.splitlines():
        line = raw.strip().rstrip("\\").strip()
        m = _COUPON_FIELD.search(line)
        if m:
            if cur:
                out.append(cur)
            cur = {"title": m.group(1).strip(), "status": ""}
            continue
        if cur:
            ms = _STATUS_FIELD.search(line)
            if ms:
                cur["status"] = ms.group(1).strip()
    if cur:
        out.append(cur)
    # 去掉标题里混进的图片/转义残留
    for c in out:
        c["title"] = re.sub(r"<[^>]+>", "", c["title"]).strip()
    return [c for c in out if c["title"]]


_CAMP_HEAD = re.compile(r"^####\s*(\d{4}年\d{1,2}月\d{1,2}日)\s*(.*)$")
_CAMP_TITLE = re.compile(r"活动标题\*\*[：:]\s*(.+)")


def payload_campaigns(text: str) -> list:
    """解析活动日历 markdown → [{date, tag, title}]。"""
    if not text:
        return []
    out, date, tag = [], "", ""
    for raw in text.splitlines():
        line = raw.strip()
        m = _CAMP_HEAD.match(line)
        if m:
            date, tag = m.group(1), m.group(2).strip()
            continue
        mt = _CAMP_TITLE.search(line)
        if mt:
            title = re.sub(r"<[^>]+>", "", mt.group(1)).strip()
            title = title.replace("\\", "").strip()
            if title:
                out.append({"date": date, "tag": tag, "title": title[:48]})
    # 同一活动会横跨多日返回；标题去重，「今日」优先
    seen, uniq = set(), []
    for c in sorted(out, key=lambda x: 0 if "今日" in (x.get("tag") or "") else 1):
        key = c["title"]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)
    return uniq


# ───────────────────────── 对外：一次只读咨询 ─────────────────────────
def _stores_from(text: str, limit: int = 6) -> list:
    d = payload_json(text)
    if not isinstance(d, dict) or not d.get("success"):
        return []
    rows = d.get("data") or []
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows[:limit]:
        out.append({
            "name": r.get("storeName", ""),
            "address": r.get("address", ""),
            "distance": r.get("distance"),
            "open": r.get("businessStartTime", ""),
            "close": r.get("businessEndTime", ""),
            "open_now": bool(r.get("businessStatus", False)),
            "reservation": bool(r.get("reservation", False)),
        })
    return out


def _points_from(text: str):
    d = payload_json(text)
    if not isinstance(d, dict) or not d.get("success"):
        return None
    data = d.get("data") or {}
    try:
        return {
            "available": int(data.get("availablePoint") or 0),
            "accumulative": int(data.get("accumulativePoint") or 0),
            "expiring": int(data.get("currentMouthExpirePoint") or 0),
        }
    except (TypeError, ValueError):
        return None


def _now_from(text: str):
    d = payload_json(text)
    if not isinstance(d, dict) or not d.get("success"):
        return None
    data = d.get("data") or {}
    return {"datetime": data.get("formatted", ""), "date": data.get("date", ""),
            "weekday": data.get("dayOfWeek", "")}


def _lottery_from(text: str):
    d = payload_json(text)
    if not isinstance(d, dict) or not d.get("success"):
        return None
    data = d.get("data") or {}
    status = (data.get("status") or {}).get("code", "")
    if status and status != "SUCCESS":
        return None
    name = data.get("activityName") or ""
    if not name:
        return None
    return {"name": name, "status": data.get("activityStatusText", ""),
            "cost": data.get("drawPoint", "")}


def _call_retry(token: str, name: str, arguments: dict = None, tries: int = 3) -> str:
    """带重试的只读调用：mcp.mcd.cn 偶发 502，实测重试两次基本能过。"""
    import time
    txt = ""
    for i in range(tries):
        txt = call_tool(token, name, arguments)
        if "查询失败" not in txt:
            return txt
        if i < tries - 1:
            time.sleep(1.5)
    return txt


def consult(token: str = None, city: str = None, keyword: str = None) -> dict:
    """一次性只读咨询，返回**结构化**真实数据（自带降级，缺项为 None/[]）。

    结构：
      ok / fetched_at / now / points / stores / coupons / campaigns / lottery
    """
    token = token or os.environ.get("MCD_MCP_TOKEN")
    if not token:
        return {"ok": False, "reason": "未配置 MCD_MCP_TOKEN"}

    out = {
        "ok": True,
        "fetched_at": "",
        "now": _now_from(_call_retry(token, "now-time-info")),
        "points": _points_from(_call_retry(token, "query-my-account")),
    }

    # 门店：必须带 beType + searchType，且 city/keyword 至少一个非空
    store_args = {"beType": 1, "searchType": 2}
    if keyword:
        store_args["keyword"] = keyword
    if city:
        store_args["city"] = city
    stores = []
    if keyword or city:
        stores = _stores_from(_call_retry(token, "query-nearby-stores", store_args))
    out["stores"] = stores

    out["coupons"] = payload_coupons(_call_retry(token, "available-coupons"))[:8]
    out["campaigns"] = payload_campaigns(_call_retry(token, "campaign-calendar"))[:6]
    out["lottery"] = _lottery_from(_call_retry(token, "query-lottery-info"))

    n_ok = sum(bool(out[k]) for k in ("now", "points", "stores", "coupons", "campaigns", "lottery"))
    out["ok"] = n_ok >= 2
    out["fetched_at"] = (out["now"] or {}).get("datetime", "")
    if not out["ok"]:
        out["reason"] = "只读接口均未取到真实数据（可能限流或 Token 失效）"
    return out


# ───────────────────────── 真实数据 → 今日落地 ─────────────────────────
def pick_coupon(real: dict, wish: str = "") -> dict:
    """从可领券里挑一张最贴合今日点单的：标题命中关键词优先，否则取第一张。"""
    coupons = (real or {}).get("coupons") or []
    if not coupons:
        return {}
    keys = [k for k in re.split(r"[配和或/、]", wish or "") if len(k) >= 2]
    for k in keys:
        for c in coupons:
            if k in c.get("title", ""):
                return c
    return coupons[0]


def nearest_store(real: dict) -> dict:
    stores = (real or {}).get("stores") or []
    if not stores:
        return {}
    return sorted(stores, key=lambda s: (s.get("distance") is None, s.get("distance") or 0))[0]


def today_campaign(real: dict) -> dict:
    camps = (real or {}).get("campaigns") or []
    for c in camps:
        if "今日" in (c.get("tag") or ""):
            return c
    return camps[0] if camps else {}


def build_yiji(real: dict, wish: str = "") -> dict:
    """用真实 MCP 数据重塑「今日宜忌」（覆盖离线版）。数据不实不回退编造。"""
    if not real or not real.get("ok"):
        return {}
    yi, ji = [], []
    st = nearest_store(real)
    cp = pick_coupon(real, wish)
    cmp_ = today_campaign(real)

    if st:
        dist = st.get("distance")
        dist_txt = f"{dist} 米" if isinstance(dist, int) and dist < 1000 else (
            f"{dist / 1000:.1f} 公里" if isinstance(dist, int) else "附近")
        yi.append(f"去 {dist_txt} 的{st['name'].replace('麦当劳', '').replace('餐厅', '')}吃")
    if cp:
        yi.append(f"领「{cp['title']}」，今天有便宜占")
    if cmp_:
        yi.append(f"顺手看一眼「{cmp_['title'][:14]}」")
    pts = real.get("points") or {}
    if pts.get("available"):
        yi.append(f"卡里还有 {pts['available']} 积分，别放过期")
    elif pts.get("accumulative"):
        yi.append(f"累计已攒 {pts['accumulative']} 积分，接着攒")

    ji.append("空着手出门")
    if st and st.get("close"):
        ji.append(f"别等过了 {st['close']} 再去")
    return {"yi": yi[:5], "ji": ji[:3], "source": "real"}


if __name__ == "__main__":
    res = consult()
    print(json.dumps(res, ensure_ascii=False, indent=2))
