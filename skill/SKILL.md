---
name: maimen-zhanbu
display_name: 麦门占卜·程序员麦占
display_name_en: MaiMen Divination
description: "给程序员算今日麦门运势：以当前时辰起梅花易数时间卦（零输入，不碰生辰八字），批今日宜忌、抽一张命卡，并用麦当劳 MCP 只读数据落到「今天去哪个店、领哪张券」，最后交付一张和网页版同款单页网页。触发场景：麦门占卜、麦门命理、程序员麦占、程序员运势、今天吃哪个汉堡、代码命格、给程序员算命、1024 程序员节。"
description_zh: "梅花易数时间卦给程序员算今天吃哪份：一卦给关键词/动爻/三段走势/体用/幸运物/点单，接麦当劳 MCP 只读数据落到门店与券，交付与网页版同款的单页网页"
description_en: "Daily I-Ching (Meihua) reading for programmers: today's keywords, moving line, three-stage trend, five-element luck items and a meal pick, grounded by McDonald's read-only MCP store and coupon data, delivered as the same single-page web app as the product site."
category: fun
version: 1.2.0
author: 墨喵
allowed-tools: Bash,Read,Write,Glob,Grep,AskUserQuestion
---

# 麦门占卜 · 程序员麦占

一句话：**起一卦，告诉程序员今天点哪份**，最后交付一张网页——版式与线上产品完全一致
（今日 / 卦象 / 门店 / 我的 四页），不是另一张卡片、不是另一个风格。

## 〇、三条铁律

1. **代码优先，不许心算**：卦象、分数、宜忌、命卡一律由 `scripts/fortune_engine.py` 算出，
   你只做解读，不改数、不重算。
2. **全程只读**：只调麦当劳 MCP 的查询类工具，**绝不**下单 / 领券 / 抽奖 / 改地址。
   查不到就说查不到，不许编数据填空。
3. **不许静默降级**：没有数据通道时，必须先问用户（见第 0 步），不能自己找本机凭据、
   也不能默默出一张「看起来有数据」的页面。

---

## 第 0 步 · 先确认数据通道（每次都做，不能跳）

先判断：本会话能不能调用 `mcd-mcp` 的只读工具（例如 `query-nearby-stores`）。

- **能调通** → 直接进第 1 步。
- **不能 / 报错 / 没有 Token** → **停下来**，用 AskUserQuestion 让用户选，不要自己决定：

| 选项 | 你接下来做什么 |
|---|---|
| **教我怎么接（推荐）** | 按「接入指引」的格式回给用户（见下方模板），强调格式一条不少：先说影响、链接加粗可点击、配置 JSON 原样。贴完点「信任/启用」，回来说一声「好了」，再从第 1 步重来。 |
| **先看效果** | 用 `templates/demo_data.js` 的示例数据出页面，并**在回复第一行写明**「示例数据（成都），不是你的实时数据」。 |
| **用我本机已有的凭证** | 只有用户明确同意才读 `~/.mcd_token`，只读查一次；说明「用完不落盘」。用户名下没有这个文件就别提这个选项。 |

### 接入指引（回复用户时照这个格式，不许缩成一句）

**第一段必须先说清影响**（加粗）：

> **没接 MCP 不影响占卜本身**——卦象、麦气分、宜忌、点单、命卡全都在本地起卦，照常出。
> 接上它只是为了把「附近门店、可领的券、今日活动」换成**你的城市实时数据**。

**然后给三步操作**（链接必须加粗且可点击）：

**第 1 步 · 领 Token（免费、只读）**：打开 **[open.mcd.cn/mcp](https://open.mcd.cn/mcp)** → 手机号登录 → 右上角「**控制台**」→ 激活 → 复制 Token。

**第 2 步 · 填配置**：WorkBuddy **设置 → 连接器 → 自定义连接器 → 配置 MCP**，粘贴（把 `你的Token` 换成刚复制的）：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer 你的Token" }
    }
  }
}
```

**第 3 步 · 启用**：保存后点「**信任 / 启用**」，回来说一声「好了」，重新起卦——这次门店和券就是你的实时数据了。

Token 免费、只读，只查不买、不代下单。

---

## 第 1 步 · 问三件事（一次问完，允许跳）

用 **一次** AskUserQuestion 问清，别连环追问：

1. **在哪个城市 / 靠近哪个地标**（决定门店与距离；不给就按示例城市）
2. **今天主要写什么语言**（默认 python，只影响五行与点单）
3. **今天提交几次、出几个错、加不加班**（可只答一项，也可以全跳）

用户嫌烦时直接跳过，按「纯凭天时」算——不要为了凑答案反复问。

## 第 2 步 · 取数（只读）

按第四节的工具清单查：门店（`query-nearby-stores`，`beType=1`、`searchType=2`，
`city`/`keyword` 至少给一个）、可领券（`available-coupons`）、当月活动（`campaign-calendar`）、
积分（`query-my-account`，可缺）、当前时间（`now-time-info`）。

查完把结果写成工作目录的 `real.json`（**只写真实返回的，缺就整段省，距离拿不到写 null 不估**）：

```json
{
  "ok": true, "city": "重庆", "keyword": "解放碑", "fetched_at": "2026-10-20 13:53",
  "stores": [{"name": "麦当劳重庆金鹰财富中心餐厅", "address": "…", "distance": 73,
              "open": "07:00", "close": "23:59", "open_now": true, "reservation": true}],
  "coupons": [{"title": "11.9元麦辣鸡腿堡", "status": "可领取"}],
  "campaigns": [{"title": "超值早餐两件套…", "tag": "今日", "date": "2026-10-20"}]
}
```

- `distance` 是相对 `keyword` 那个地标算的，**不是用户手机的实时定位**；批命时要点明，
  别让人误以为读了他手机。
- 三个数组全空 = 没有真实数据，第 3 步会退回离线版，但回复里要说明。

## 第 3 步 · 起卦

```bash
python3 scripts/fortune_engine.py --lang python --commits 0 --bugs 0 --out fortune.json
# 用户报了外应就带上：--lang rust --commits 30 --bugs 3 --overtime
```

读 `fortune.json` 的 `meihua` / `tiyong` / `card` / `score` / `yiji` / `lucky`，**不要改数**。

## 第 4 步 · 出页面（交付物只有这一个）

```bash
python3 scripts/render_page.py --real real.json --out 麦门占卜-今日.html
# 没有 real.json 就省掉 --real
```

产出的就是**线上同款单页应用**：宣纸底、四页 Tab（今日 / 卦象 / 门店 / 我的）、
起卦仪式、点单结论、真实门店与券、可调外应。数据焊在文件里，双击即开，断网可看。

- 文件名固定 `麦门占卜-今日.html`，不要另起名字，也不要再生成第二份文件。
- 页面「我的」页已经能调外应（改完立即重算），**不用**再教用户改参数。

## 第 5 步 · 怎么跟用户说

三段话，别多：

1. **结论**：卦名 + 一句人话 + 麦气分 + 今天点什么。
2. **落地**：最近那家多远、能不能预约、有没有券；注明数据城市与抓取时间。
   - **用了示例数据 / 没接通道时，必须在这里补一句**（加粗）：「**没接 MCP 只影响门店和券，占卜结果（卦象 / 麦气 / 宜忌 / 点单 / 命卡）完全不受影响**」，然后按第 0 步「接入指引」的格式给出接入方式——影响说明 + 三步操作 + 加粗可点击的 Token 链接，**不许缩成一句带过**。
3. **下一步**：双击打开页面；想更准就去「我的」补语言/提交/加班（点单会跟着变）；右下角可存网页或存图。

批命口吻照旧：**坐堂先生批命**，术语照用（坤、动爻、比和、禄存），结论必须说人话。
禁词：引擎、脚本、程序、参数、字段、结构化、文件名、路径、口径、复核。

---

## 三、红线

1. 绝不静默下单（只查询、只建议）。
2. 查不到就明说「今日门店/券暂不可得」，不编造。
3. Token 不许写进任何文件、不许放进网页；只在进程环境里用。
4. 玩笑有度，不贬低麦当劳品牌。
5. 没有数据通道时先问用户（第 0 步），不许默默降级。
6. 金额与单位按接口返回照抄，不口算。

## 四、MCP 工具（只读）

接入 `https://mcp.mcd.cn`（`streamablehttp`，`Authorization: Bearer <Token>`）。

| 工具 | 用来做什么 |
|---|---|
| `query-nearby-stores` | 最近门店、营业时间、能不能预约 |
| `available-coupons` | 今天能领的券 |
| `campaign-calendar` | 当月活动、今日活动 |
| `query-my-account` | 积分（可缺） |
| `now-time-info` | 当前时间 |

**绝不碰**：`create-order`、`mall-create-order`、`party-order-create`、`cancel-order`、
`draw-lottery`、`auto-bind-coupons`、`delivery-create-address`、`calculate-price`。

## 五、文件

| 文件 | 作用 |
|---|---|
| `scripts/fortune_engine.py` | 时间卦 + 体用 + 外应宜忌 + 抽卡 |
| `scripts/mcp_client.py` | 只读客户端（包装文本解析、重试） |
| `scripts/render_page.py` | 把单页应用打成自包含 HTML，真实数据内联 |
| `templates/app.html` | 单页应用模板（与线上产品同一套） |
| `templates/demo_data.js` | 示例数据（成都），没有数据通道时预览用 |
| `references/mcd_mcp_tools.md` | 35 个工具实测清单与坑 |

## 六、为什么只有技能能拿到实时数据

网页版/小程序是静态托管：没有安全的地方放 Token，浏览器也拿不到定位，那边只能是一次抓取的快照。
**实时 + 个人化的数据只有技能这一侧成立**——这也是本技能存在的意义。
把 Token 塞进前端、或让浏览器直连 MCP，等于把凭证公开，坚决不做。
