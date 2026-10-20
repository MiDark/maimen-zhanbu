# MCP 接入说明（MCP_INTEGRATION.md）

## 一、使用的麦当劳 MCP Server

| 项 | 值 |
|---|---|
| Server 名称 | `mcd-mcp` |
| 接入地址 | `https://mcp.mcd.cn`（根域名即端点，**非** `https://mcp.mcd.cn/mcp`，后者返回 404） |
| 传输协议 | Streamable HTTP（`type: streamablehttp`） |
| 鉴权 | `Authorization: Bearer <MCP_TOKEN>` |
| MCP 协议版本 | `2024-11-05` |
| Server 版本 | `mcd-mcp v1.0.0` |
| 限流 | 600 次 / 分钟（超 429） |

## 二、实际使用的 Tool（仅只读查询类）

本项目定位「决策辅助 + 趣味命理」，**只调用以下只读工具**，不触发任何写操作：

| Tool | 用途 | 命理映射 |
|---|---|---|
| `query-my-account` | 查询积分账户 | 财运 / 财帛宫 |
| `campaign-calendar` | 当月营销活动日历 | 吉日 / 运势时间维度 |
| `available-coupons` | 可领取的麦麦省优惠券 | 宜领券 / 财运指引 |
| `query-store-coupons` | 指定门店+订单类型可用券 | 按门店宜领券 |
| `query-my-coupons` | 卡包已有券资产 | 财运现状 |
| `query-nearby-stores` | 到店可点餐门店 | 今日至尊福地 |
| `list-nutrition-foods` | 餐品营养成分 / 热量 | 宜吃 / 忌吃依据 |
| `now-time-info` | 当前服务器时间 | 黄道吉时 |
| `query-lottery-info` / `query-my-prizes` | 积分抽奖信息 / 已得奖品 | 宜抽奖（点缀） |

**明确不调用**（写操作 / 下单风险）：`create-order`、`party-order-create`、`mall-create-order`、
`cancel-order`、`draw-lottery`、`auto-bind-coupons`、`delivery-create-address`、`calculate-price`、各类订单/地址/派对写操作。

## 三、调用流程（业务价值）

在 WorkBuddy 里跑（主路径，MCP 由连接器调用）：

```
用户说「帮我算今日麦门运势」（已启用 mcd-mcp 连接器，Token 是使用者自己的）
  → 连接器调只读工具：积分 / 活动 / 券 / 门店 / 时间 / 营养
  → Agent 把真实返回按固定结构写成 real.json（缺的省掉，不编造）
  → fortune_engine.py 离线算卦：梅花时间卦（本卦/互卦/变卦/动爻/体用生克）、语言→五行、外应、抽卡
  → demo_offline.py --real real.json 把真实门店与券落到宜忌（去 420 米那家 / 领 10 元券）
  → 出 麦门命卡.html：自包含、零外链、file:// 双击直开，可存图发小红书
```

本地/离线等价路径（CLI、快照生成、调试用，不参与技能运行时）：

```
mcp_client.py 用标准库直连同一端点，Token 只从环境变量读
  → consult() 拿到原始返回 → build_yiji() 重塑宜忌 → fetch_real.py 落成前端快照
  → 任一查询失败标注「某数据暂缺」；无 Token 整体降级为纯命理映射 + 抽卡
```

**引擎输出的结构化字段**（三端同源，供上层润色时取用）：

| 字段 | 含义 |
|---|---|
| `meihua.ben_* / hu_* / bian_*` | 本卦 / 互卦 / 变卦的名称、上下卦、卦象符号、断语 |
| `meihua.dong_yao` | 动爻（1–6，余零取六） |
| `meihua.*_lines` | 三卦的六爻卦画（自下而上，1 阳 0 阴） |
| `tiyong` | 体用生克：`ti_name/ti_element`、`yong_name/yong_element`、`relation`（比和/用生体/体生用/体克用/用克体）、`verdict`、`luck`（72/84/58/70/44） |
| `wai_ying` | 由 commit / bug / 加班导出的外应条目 |
| `card` | 抽中的麦门命卡（名 / 星曜 / blessing） |
| `score` | 总评（基准分与体用之气的加权，夹 30–96） |
| `yiji` | 宜忌（本卦与变卦断语 + 体用 + 外应 + 五行共同推导） |

**真实数据如何驱动宜忌（业务闭环）**：`mcp_client.consult()` 返回各只读工具文本；`build_yiji(real)`
据此生成落地式宜忌（赴就近福地领券、宜领麦麦省券、宜参当月活动）；若数据含工具说明/字段 schema 噪音则自动回退离线宜忌，
**绝不把未经校验的原始响应直接塞进命卡**。命理口吻的最终批命由 Skill 在 WorkBuddy 内二次润色，本仓库代码只产出结构化依据。

**业务价值**：把麦当劳 MCP 的「门店 / 优惠 / 积分 / 营养」真实能力，包裹进「程序员命理」的趣味外壳，
降低普通用户（尤其是程序员及其身边人）使用麦当劳开放能力的门槛，兼具 1024 程序员节话题性与传播性。

## 四、返回形态与解析（2026-10-20 实测，重要）

麦当劳 MCP 有两类返回，必须分开解析，否则会把真实数据误判成噪音：

| 类型 | 特征 | 解析方式 |
|---|---|---|
| **JSON 类**（时间 / 积分 / 门店 / 抽奖） | 一段「`# API Response Information` + 字段说明」，末尾跟 `{"success":true,...,"data":{...}}` | 从末尾的 `{"success"` 起做花括号配平，取出最后一个完整 JSON（`payload_json`） |
| **Markdown 类**（券 / 活动日历） | 直接是可读文本：券是 `- 优惠券标题：X \ 状态：Y` 列表；活动是 `#### 日期 + 活动标题` | 正则分词（`payload_coupons` / `payload_campaigns`），无需 JSON |

> **曾经的坑**：旧版把整段返回丢给 `_looks_real()` 判断，而返回开头永远是
> "API Response Information"（在 `_JUNK` 名单里），于是真实数据 100% 被判为噪音，
> MCP 明明调通了、界面上却一条都看不到。现在改为**先抽载荷、再判有效性**：
> 抽不出结构化内容才算「暂缺」。

另外两个接口细节：

- `query-nearby-stores` 必传 `beType`（1 到店 / 5 得来速）与 `searchType`，且 `city` 与 `keyword` **至少一个非空**，否则返回 `code: 600058 城市名或者关键词不能为空`。传 `keyword` 时定位更准。
- `mcp.mcd.cn` 偶发 `502 Bad Gateway`，`_call_retry()` 重试三次（间隔 1.5s）基本能过。

## 五、MCP 的边界：谁能调、谁不能调

| 形态 | 谁在调 MCP | 数据性质 |
|---|---|---|
| **WorkBuddy 技能（参赛主体）** | WorkBuddy 的 MCP 连接器，用**使用者自己的 Token**，对话运行时按需调用 | 实时、个人化（自己的积分、附近门店、可领券） |
| **网页版** | 浏览器 → **站点自带中转**（`server/server.js`，已托管部署）→ MCP；服务端内置一份只读 Token，使用者也可在「我的」页填自己的 | **开页即实时**；中转不可达才退回快照（页脚标城市与抓取时间） |
| **小红书小工具** | **谁都不能调** | 服务端定时刷新后打进包里的快照 |

### 两条实测硬约束（2026-10-20）

**1. MCP 端点不支持浏览器跨域。** 带 `Origin` 的请求：

```
OPTIONS https://mcp.mcd.cn  → 403，无任何 Access-Control-* 头
POST    https://mcp.mcd.cn  → 200 OK（Token 有效时），同样无 Access-Control-* 头
```

所以浏览器里 `fetch` 必被拦，**Token 再对也发不出请求**。这不是安全取舍，是协议现状。
要直连只能加一层中转补 CORS。

**2. 小红书小工具容器禁网。** 官方文档（2026-10-13 版）§4.2：

> 网络请求：`fetch` / `XMLHttpRequest`、加载外部图片 / 字体 / 媒体等网页联网请求。
> 所有资源须打包在内

FAQ 原文：「能不能请求我自己的服务端接口？网页不能通过 `fetch`、`XMLHttpRequest`
等方式请求外部服务。」平台 API 只有 `xhs.miniTool.*`（存相册 / 文件 / 本地存储）和
`xhs.AI`（文本生成），**没有任何请求代理能力**。

结论：小工具里「填 Token 查实时」物理上做不到，也**不做假的输入框**。小工具用快照，
并在「我的」页如实写明为什么。

**3. 小工具也没有「打开网页」和「复制链接」。** 同一份文档禁了 `window.open`、
`target="_blank"`、跳转站外 URL、`<iframe>`，也禁了 `navigator.clipboard` /
`execCommand('copy')`；API 清单（§3.2「列出的即为全部可用 JS API」）里没有任何
`setClipboardData` 一类能力。所以「点按钮跳网页」「点按钮复制地址」都不可实现，
只能：① 页内二维码（另一台手机扫）；② `writeTempFile` + `saveImageToPhotosAlbum`
存二维码到相册，再用微信「扫一扫 → 相册」识别；③ 展示可选中文本的地址；
④ 9.49+ 用 `interactionOpenApi` 把地址作为评论草稿带到评论区。
实现见 `scripts/build_minitool.py` 的 `MINITOOL_LIVE_BLOCK`，二维码由 `scripts/make_qr.py` 生成。

技能里的数据流是这样闭合的：连接器调工具 → Agent 把结果按固定结构写成 `real.json`
（格式见 `skill/SKILL.md` 第 1.5 步）→ `demo_offline.py --real real.json` 渲染命卡。
**没有 `real.json` 就退回纯离线**，不会编数据。

## 六、静态页面如何用上真实数据

三条来源，页面按优先级用：

### 1）实时查询（网页版，开页自动 + 可换自己的 Token）

页面加载完先出卦，随即静默查一次真实数据（约 5–20 秒），拿到就原地换源、重算宜忌。

- 默认走**站点自带中转** `https://maimen-mcp-proxy.app.workbuddy.host/mcp?sharecode=…`
  （`web/mcd_live.js` 的 `DEFAULT_PROXY`），中转里内置一份只读 Token，所以**不填任何东西也能查**。
- 想查**自己账号**的积分 / 我的券：「我的」页 → 接入真实数据 → 填 `MCP Token`（可留空）
  + 城市 / 地标 → 点查询。Token 存本机 `localStorage`，只发给中转。
- 查询走同样几个只读工具，结果与快照**同形**，渲染层零改动换源，页脚标「刚查的实时数据」。

中转（`server/server.js`，零依赖 Node 单文件）的硬边界：只转发 `mcp.mcd.cn`、只放行
`tools/call` 的只读白名单（下单 / 领券 / 抽奖 403）、单 IP 10 分钟 90 次、单请求 32KB。
自建见 README「服务端中转」；Cloudflare Worker 备选版是 `tools/mcp-proxy-worker.js`（不带 Token，需浏览器自带）。

### 2）服务端定时刷新（所有形态）

```bash
MCD_MCP_TOKEN=你的TOKEN python3 scripts/fetch_real.py --city 成都 --keyword 春熙路
# → web/mcd_data.js（网页 <script src>）
# → assets/mcd_data.js（命卡）
# → miniprogram/data/mcd_real.js（小程序 / 小工具 require）
```

GitHub Actions（`.github/workflows/refresh-mcd-data.yml`）每 3 小时自动跑一次，
用仓库 secret `MCD_MCP_TOKEN`，无变化不提交，Pages 随提交自动更新。

- 快照里带 `fetched_at`，页面显示「抓取于 …」，**明确是快照而非实时**。
- 默认全脱敏：个人积分三项一律写 `null`，页面显示不显示个人积分。要全量加 `--with-account`，但别提交进仓库。
- 页面读不到快照时显示「这会儿没读到数据」，其余功能（起卦 / 命卡 / 建议）照常。

### 3）小工具离线包

打包时把当时的快照复制进 `minitool/dist/mcd_data.js`。包是离线的，数据不会自己变新，
所以每次发版前重新跑一次上面两条命令再打包。

## 七、实测依据

完整 35 工具清单、端点坑、限流与 session 行为见 `references/mcd_mcp_tools.md`（2026-10-19 实测）。
