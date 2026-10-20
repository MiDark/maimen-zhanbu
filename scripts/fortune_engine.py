#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦门占卜·程序员麦占 —— 梅花易数时间卦 + 体用生克 + 抽卡引擎（纯标准库，离线可跑）

不依赖麦当劳 MCP；MCP 只读真实数据由 mcp_client.py 注入本引擎产出的最终报告（宜忌/门店/券）。
输出结构化 JSON，供 assets/ming_card.html 渲染（命理全鉴同范式：结构化数据 → 模板）。

文风纪律（对标命理全鉴）：对外文案不得出现 引擎/脚本/程序/代码/参数/字段/口径/
复核/审查/勘误 等工程词；命理先生坐堂批命，断语在前依据在后。

核心方法：零输入梅花易数时间卦 —— 以「当前年+月+日+时」起卦，程序员今日指标（commit/bug/
语言/加班）作「外应」，映射到命理参数；抽一张麦门命卡。无需生辰八字等敏感重度信息。
"""

import json
import datetime
import argparse

# ───────────────────────── 八卦（先天数） ─────────────────────────
# 先天数：乾1 兑2 离3 震4 巽5 坎6 艮7 坤8；二进制用 (数-1) 的 3 位表示，便于翻爻算变卦
TRIGRAM = {
    1: ("乾", "金", "☰"),
    2: ("兑", "金", "☱"),
    3: ("离", "火", "☲"),
    4: ("震", "木", "☳"),
    5: ("巽", "木", "☴"),
    6: ("坎", "水", "☵"),
    7: ("艮", "土", "☶"),
    8: ("坤", "土", "☷"),
}

# 五行生克
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# ───────────────────────── 六十四卦（上卦,下卦）→ [卦名, 断语] ─────────────────────────
# 上/下卦用先天数 1..8 标注。断语走命理先生口吻，十余字一句，仅供娱乐。
GUA64 = {
    (1, 1): ["乾为天", "天时正好，宜一口气把活儿干完，忌嘴上一句「马上就好」"],
    (8, 8): ["坤为地", "地气够稳，宜老老实实吃顿饱的，忌硬撑着节食"],
    (6, 4): ["水雷屯", "开局就卡，宜先来份薯条垫垫，忌空着肚子改需求"],
    (7, 6): ["山水蒙", "脑子没开机，宜问清楚了再动手，忌瞎猜产品想要啥"],
    (6, 1): ["水天需", "还得再等等，宜先来个圆筒，忌催着上线"],
    (1, 6): ["天水讼", "容易抬杠，宜退半步吃口堡，忌在群里跟人对线"],
    (8, 6): ["地水师", "人多事也杂，宜分好工各点各的，忌一锅乱炖"],
    (6, 8): ["水地比", "人缘挺旺，宜拉个人拼个随心配，忌自己闷头吃"],
    (5, 1): ["风天小畜", "攒着点好，宜加个小食不加大，忌一顿点太多"],
    (1, 2): ["天泽履", "步步踩线，宜小心着提交，忌手一抖 force push"],
    (8, 1): ["地天泰", "通泰顺遂，宜照着计划走，忌临时给自己加戏"],
    (1, 8): ["天地否", "气有点堵，宜先搁着别硬推，忌今天硬上线"],
    (1, 3): ["天火同人", "合得来，宜结对子一起干，忌各改各的"],
    (3, 1): ["火天大有", "手气正旺，宜点份好的犒劳自己，忌一个人吃独食"],
    (8, 7): ["地山谦", "低调点好，宜闷声吃堡，忌发圈炫加班"],
    (4, 8): ["雷地豫", "心情不错，宜慢慢吃不着急，忌边吃边改 bug"],
    (2, 4): ["泽雷随", "跟着走就行，宜听安排，忌另开一摊"],
    (7, 5): ["山风蛊", "旧账要清，宜先收拾烂摊子，忌再堆新需求"],
    (8, 2): ["地泽临", "适合靠近点，宜当面聊两句，忌在文档里打太极"],
    (5, 8): ["风地观", "先看着别急，宜摸清底细，忌抢着表态"],
    (3, 4): ["火雷噬嗑", "有硬骨头，宜先啃最难的，忌拖到下班"],
    (7, 3): ["山火贲", "适合包装，宜把 demo 弄漂亮点，忌只剩个壳"],
    (7, 8): ["山地剥", "有点漏气，宜收着点，忌大改特改"],
    (8, 4): ["地雷复", "缓过来了，宜早睡补觉，忌熬夜硬扛"],
    (1, 4): ["天雷无妄", "别乱来，宜守规矩，忌顺手改别人的代码"],
    (7, 1): ["山天大畜", "劲攒足了，宜蓄着待发，忌现在就 all in"],
    (7, 4): ["山雷颐", "该补了，宜正经吃一顿，忌拿咖啡当饭"],
    (2, 5): ["泽风大过", "有点过头，宜适可而止，忌一口气点三份"],
    (6, 6): ["坎为水", "坑有点多，宜稳着走，忌硬闯"],
    (3, 3): ["离为火", "状态在线，宜多输出，忌光说不动手"],
    (2, 7): ["泽山咸", "容易来电，宜真诚点，忌端着架子"],
    (4, 5): ["雷风恒", "贵在坚持，宜按节奏来，忌干两天停三天"],
    (1, 7): ["天山遯", "该撤就撤，宜早点下班，忌死磕到底"],
    (4, 1): ["雷天大壮", "气势够足，宜趁热打铁，忌用力过猛"],
    (3, 8): ["火地晋", "往上升，宜主动争取，忌等着被发现"],
    (8, 3): ["地火明夷", "光被遮住，宜低调养着，忌抢风头"],
    (5, 3): ["风火家人", "适合收拾，宜整理下工位，忌管别人闲事"],
    (3, 2): ["火泽睽", "有点拧巴，宜求同存异，忌非要分个对错"],
    (6, 7): ["水山蹇", "路不好走，宜绕一绕，忌硬顶"],
    (4, 6): ["雷水解", "结开了，宜把拖着的事办掉，忌继续攒"],
    (7, 2): ["山泽损", "该减了，宜做减法，忌什么都想要"],
    (5, 4): ["风雷益", "有进益，宜顺手帮人一把，忌独占好处"],
    (2, 1): ["泽天夬", "该断了，宜果断砍需求，忌犹犹豫豫"],
    (1, 5): ["天风姤", "容易撞上，宜留个心眼，忌什么局都去"],
    (2, 8): ["泽地萃", "人聚齐了，宜组个饭局，忌各吃各的"],
    (8, 5): ["地风升", "慢慢往上，宜一步一步，忌想一步登天"],
    (2, 6): ["泽水困", "有点困住，宜先歇口气，忌硬求"],
    (6, 5): ["水风井", "井水不枯，宜复盘沉淀，忌原地打转"],
    (2, 3): ["泽火革", "该换了，宜推倒重来，忌修修补补"],
    (3, 5): ["火风鼎", "要上新，宜换套新方案，忌将就"],
    (4, 4): ["震为雷", "动静不小，宜开个新坑，忌犹豫半天"],
    (7, 7): ["艮为山", "该停了，宜收工走人，忌再改一版"],
    (5, 7): ["风山渐", "慢慢来，宜按部就班，忌跳步骤"],
    (4, 2): ["雷泽归妹", "别急着定，宜先说清楚，忌仓促答应"],
    (4, 3): ["雷火丰", "正当其时，宜趁势干票大的，忌过了头"],
    (3, 7): ["火山旅", "在外奔波，宜就近吃，忌跑太远"],
    (5, 5): ["巽为风", "润物无声，宜小步推进，忌硬刚"],
    (2, 2): ["兑为泽", "和气生财，宜好好说话，忌嘴上不饶人"],
    (5, 6): ["风水涣", "该散了，宜把心结解开，忌憋着"],
    (6, 2): ["水泽节", "有节制，宜量力点单，忌报复性消费"],
    (5, 2): ["风泽中孚", "讲信用，宜说到做到，忌画大饼"],
    (4, 7): ["雷山小过", "小事可为，宜小改小动，忌大动干戈"],
    (6, 3): ["水火既济", "事已成了，宜收尾查一遍，忌松劲"],
    (3, 6): ["火水未济", "还差一点，宜善始善终，忌最后翻车"],
}

# ───────────────────────── 编程语言 → 五行 + 批命断语 ─────────────────────────
LANG_WUXING = {
    "python": ("水", "水一样的语言，绕得过坎，最适合写业务逻辑"),
    "java": ("土", "厚土压得住场，企业级系统还得看它"),
    "c": ("金", "最贴机器的语言，硬核但不好伺候"),
    "c++": ("金", "一把锋利的刀，能砍硬骨头也能砍到自己"),
    "go": ("木", "长得快、并发多，云上跑得欢"),
    "rust": ("金", "炼得很纯的铁，编译器比你还操心"),
    "javascript": ("火", "点着就着，前端全靠它照亮"),
    "js": ("火", "点着就着，前端全靠它照亮"),
    "typescript": ("火", "给火加了个炉膛，烧得旺还不乱窜"),
    "php": ("土", "老土壤了，半个互联网都长在上面"),
    "ruby": ("木", "柔软好使，写着写着人就开心了"),
    "kotlin": ("土", "安卓的老底子，稳当还爱纳新"),
    "swift": ("金", "快得像风，果家的专属刀"),
    "lua": ("木", "轻得像叶子，嵌进哪儿都能活"),
}

# ───────────────────────── 麦门命卡池（名 / 星曜 / blessing 断语） ─────────────────────────
MING_CARDS = [
    ("巨无霸", "双层至尊", "两片牛肉夹住你今天的 KPI，吃它就等于给自己盖了个稳章"),
    ("麦辣鸡腿堡", "辣度担当", "一口下去思路就通了，辣是程序员的强制刷新"),
    ("麦旋风", "转圈大师", "脑子转不动就先吃口转的，转着转着就想通了"),
    ("薯条", "万恶之源", "一根接一根，进度和薯条一起见底，记得多要两包番茄酱"),
    ("麦乐鸡", "六块正好", "不多不少正好六块，够你撑到下一次提交"),
    ("吉士汉堡", "一片芝士", "朴素但顶饱，今天不折腾，稳稳收工"),
    ("板烧鸡腿堡", "不炸主义者", "不油炸也香，今天走温和路线，别硬刚"),
    ("圆筒冰淇淋", "甜筒收尾", "甜的先顶上，苦的放明天，一天才算完整"),
]

# 五行 → 今日点单池（麦门真有卖的品类；同池轮换：外应一变，点的就挪位）
ORDER_POOL = {
    "金": ["薯条配麦乐鸡", "麦香鱼配薯条", "麦乐鸡配玉米杯", "薯条配圆筒冰淇淋"],
    "木": ["板烧鸡腿堡配鲜蔬杯", "双吉汉堡配鲜煮咖啡", "麦香鱼配蔬菜色拉", "吉士汉堡配玉米杯"],
    "水": ["麦旋风配可乐", "圆筒冰淇淋配麦乐鸡", "麦乐鸡配冰咖啡", "冰咖啡配吉士汉堡"],
    "火": ["麦辣鸡腿堡", "麦辣鸡翅配可乐", "麦辣鸡腿堡配薯条", "麦辣鸡翅配麦乐鸡"],
    "土": ["巨无霸", "双层吉士汉堡配薯条", "巨无霸配麦乐鸡", "吉士汉堡配薯饼"],
}
# 用克体：这顿压着你，走清淡，辣的先放放
MILD_POOL = ["麦香鱼配薯条", "板烧鸡腿堡配鲜蔬杯", "吉士汉堡配可乐", "玉米杯配麦乐鸡"]
# 早餐时段（5–10 点）只卖早餐
BREAKFAST_POOL = ["猪柳蛋麦满分配薯饼", "吉士蛋麦满分配热香饼", "猪柳蛋麦满分配豆浆", "薯饼配热豆浆"]


def order_of(wx: str, rel: str, sub: dict, now: datetime.datetime) -> str:
    """今日点单：五行定池，外应与时辰定轮。

    种子带上 语言 / 提交 / 出错 / 加班 / 小时 —— 改任何一个输入，
    点单都会在池子里挪位，不再总是同一份（与网页、小程序三端同式）。
    """
    lang = (sub.get("lang") or "").lower()
    seed = (sub.get("commits", 0) * 3 + sub.get("bugs", 0) * 5
            + (7 if sub.get("overtime") else 0)
            + sum(map(ord, lang)) + now.hour)
    if 5 <= now.hour < 10:
        pool = BREAKFAST_POOL          # 早餐时段只卖早餐，优先于一切
    elif rel == "用克体":
        pool = MILD_POOL
    else:
        pool = ORDER_POOL.get(wx, ORDER_POOL["土"])
    return pool[seed % len(pool)]


# ───────────────────────── 卦象关键词（上,下）→ 三个词 ─────────────────────────
# 只做「一眼看懂这卦在说啥」，不追求术语准确度，供首页标签使用。
GUA_TAGS = {
    (1, 1): ["开足马力", "一次做完", "别嘴硬"], (8, 8): ["稳住", "吃饱", "别硬撑"],
    (6, 4): ["开局卡", "先垫一口", "别空肚改需求"], (7, 6): ["没开机", "先问清", "别瞎猜"],
    (6, 1): ["再等等", "先来口甜的", "别催上线"], (1, 6): ["易抬杠", "退半步", "别对线"],
    (8, 6): ["人多事杂", "分好工", "别一锅炖"], (6, 8): ["人缘好", "拉个伴", "别闷头吃"],
    (5, 1): ["攒着", "小份就够", "别点太多"], (1, 2): ["踩线", "小心提交", "别手抖"],
    (8, 1): ["顺", "按计划", "别加戏"], (1, 8): ["气堵", "先搁着", "别硬推"],
    (1, 3): ["合得来", "结对子", "别各改各的"], (3, 1): ["手气旺", "点份好的", "别吃独食"],
    (8, 7): ["低调", "闷声吃", "别炫加班"], (4, 8): ["心情好", "慢慢吃", "别边吃边改"],
    (2, 4): ["跟着走", "听安排", "别另开摊"], (7, 5): ["清旧账", "先收摊子", "别堆需求"],
    (8, 2): ["靠近点", "当面聊", "别打太极"], (5, 8): ["先看戏", "摸清底", "别抢表态"],
    (3, 4): ["硬骨头", "先啃难的", "别拖到下班"], (7, 3): ["好包装", "弄漂亮点", "别只剩壳"],
    (7, 8): ["漏气", "收着点", "别大改"], (8, 4): ["回血", "早睡", "别熬夜"],
    (1, 4): ["别乱来", "守规矩", "别动别人代码"], (7, 1): ["蓄力", "攒着待发", "别 all in"],
    (7, 4): ["该补了", "正经吃一顿", "别拿咖啡当饭"], (2, 5): ["过头", "适可而止", "别点三份"],
    (6, 6): ["坑多", "稳着走", "别硬闯"], (3, 3): ["在线", "多输出", "别光说"],
    (2, 7): ["来电", "真诚点", "别端架子"], (4, 5): ["长跑", "按节奏", "别三天打鱼"],
    (1, 7): ["该撤", "早点走", "别死磕"], (4, 1): ["气势足", "趁热打铁", "别用力过猛"],
    (3, 8): ["上升", "主动争取", "别等着被发现"], (8, 3): ["藏锋芒", "养着", "别抢风头"],
    (5, 3): ["收拾", "整工位", "别管闲事"], (3, 2): ["拧巴", "求同存异", "别争对错"],
    (6, 7): ["路难走", "绕一绕", "别硬顶"], (4, 6): ["解结", "办掉拖着的事", "别继续攒"],
    (7, 2): ["做减法", "让一点", "别什么都想要"], (5, 4): ["有进益", "帮人一把", "别独占"],
    (2, 1): ["该断", "砍需求", "别犹豫"], (1, 5): ["易撞上", "留心眼", "别什么局都去"],
    (2, 8): ["人聚齐", "组个饭局", "别各吃各的"], (8, 5): ["慢慢上", "一步一格", "别想一步登天"],
    (2, 6): ["困住", "歇口气", "别硬求"], (6, 5): ["不枯", "复盘沉淀", "别原地打转"],
    (2, 3): ["该换", "推倒重来", "别修补"], (3, 5): ["上新", "换新方案", "别将就"],
    (4, 4): ["动静大", "开个新坑", "别犹豫"], (7, 7): ["该停", "收工走人", "别再改一版"],
    (5, 7): ["慢慢来", "按部就班", "别跳步骤"], (4, 2): ["别急定", "先问清楚", "别仓促答应"],
    (4, 3): ["正当其时", "干票大的", "别过头"], (3, 7): ["在外跑", "就近吃", "别跑太远"],
    (5, 5): ["润物无声", "小步推进", "别硬刚"], (2, 2): ["和气", "好好说话", "别嘴上不饶人"],
    (5, 6): ["该散", "解开结", "别憋着"], (6, 2): ["有节制", "量力点单", "别报复性消费"],
    (5, 2): ["讲信用", "说到做到", "别画饼"], (4, 7): ["小事可为", "小改小动", "别大动干戈"],
    (6, 3): ["已成", "收尾查一遍", "别松劲"], (3, 6): ["差一点", "善始善终", "别最后翻车"],
}

# 八卦象意：名 → (自然象, 一句话性情)
TRIGRAM_XIANG = {
    1: ("天", "刚健、往上顶、爱硬碰"),
    2: ("泽", "喜悦、会说话、好交朋友"),
    3: ("火", "明亮、显眼、烧得快"),
    4: ("雷", "动、突然、说来就来"),
    5: ("风", "渗透、顺着走、无孔不入"),
    6: ("水", "险、绕、藏得深"),
    7: ("山", "停、稳、过不去就歇着"),
    8: ("地", "承载、厚、什么都接得住"),
}

# 五行 → 今日幸运物（颜色/数字/方位/时段/单品）
LUCKY = {
    "金": {"color": "白 / 银", "num": "4 和 9", "dir": "西边", "hour": "15–19 点", "item": "薯条"},
    "木": {"color": "青 / 绿", "num": "3 和 8", "dir": "东边", "hour": "7–11 点", "item": "板烧鸡腿堡"},
    "水": {"color": "黑 / 蓝", "num": "1 和 6", "dir": "北边", "hour": "21–1 点", "item": "麦旋风"},
    "火": {"color": "红 / 橙", "num": "2 和 7", "dir": "南边", "hour": "11–15 点", "item": "麦辣鸡腿堡"},
    "土": {"color": "黄 / 棕", "num": "5 和 10", "dir": "中间（就工位）", "hour": "13–17 点", "item": "巨无霸"},
}

# 动爻提示：爻位 × 阴阳。爻位讲「处在哪个阶段」，阴阳讲「你该动还是该守」。
YAO_POS = {
    1: ("刚起步", "今天才开头"),
    2: ("在自己那摊", "手上的活最要紧"),
    3: ("进退两难", "跨出去回不来，卡在中间"),
    4: ("到了门外", "事到临头，得问一句"),
    5: ("坐在主位", "今天你能拍板"),
    6: ("走到头了", "这一程该收了"),
}
YAO_MOOD = {
    1: ("阳爻动，宜主动出击，该说就说", "阴爻动，宜先守着，别抢出头"),
}


# ───────────────────────── 卦体工具 ─────────────────────────
def _lines(up: int, down: int) -> list:
    """上下卦 → 自下而上六爻（1 阳 0 阴）。

    先天数与爻象的对应：以 (先天数-1) 的三位二进制为 B2B1B0，
    则 **B2 位对应初爻、B0 位对应上爻**，且爻象与该位取值相反
    （乾1→000→阳阳阳，兑2→001→阳阳阴，艮7→110→阴阴阳）。
    故取第 i 爻（i=0 为初爻）时读第 (2-i) 位。
    """
    ls = [1 - (((down - 1) >> (2 - i)) & 1) for i in range(3)]
    ls += [1 - (((up - 1) >> (2 - i)) & 1) for i in range(3)]
    return ls


def _trigram_of(lines3: list) -> int:
    """三爻（自下而上）→ 先天数，与 _lines 严格互逆。"""
    bits = 0
    for i, v in enumerate(lines3):
        bits |= (1 - v) << (2 - i)
    return bits + 1


def _gua_label(up: int, down: int) -> str:
    """上下卦的读法：常卦称「X上Y」，八纯卦直接称卦名（坤为地，不是「坤上坤」）。"""
    if up == down:
        return GUA64[(up, down)][0]
    return f"{TRIGRAM[up][0]}上{TRIGRAM[down][0]}"


def meihua(dt: datetime.datetime) -> dict:
    """梅花易数时间卦：年+月+日 起上卦，加时辰 定下卦与动爻。

    取数：公历年、公历月日、十二时辰序数（子1…亥12）——属便用之法，古法当用农历与年支。
    上卦 =（年+月+日）÷8 取余，余零作八；下卦 =（年+月+日+时）÷8 取余；
    动爻 =（年+月+日+时）÷6 取余，余零作六。
    变卦由「六爻卦画翻动爻」回推上下卦，与本卦卦画强制同源。
    """
    y, mo, d, h = dt.year, dt.month, dt.day, dt.hour
    sum3 = y + mo + d
    shi = ((h + 1) // 2) % 12 + 1        # 时辰序数：子1 丑2 寅3 … 亥12
    sum4 = sum3 + shi
    up = sum3 % 8 or 8
    down = sum4 % 8 or 8
    dong = sum4 % 6 or 6                 # 1..6，余零取上爻

    ben = GUA64[(up, down)]

    # 六爻：本卦卦画（自下而上），互卦、变卦均由它派生，保证「画」与「名」同源
    ls = _lines(up, down)

    # 变卦：翻动爻所在之爻，再由六爻回推上下卦
    bl = list(ls)
    bl[dong - 1] = 1 - bl[dong - 1]
    down2 = _trigram_of(bl[0:3])
    up2 = _trigram_of(bl[3:6])
    bian = GUA64[(up2, down2)]

    # 互卦：取二三四爻为下卦、三四五爻为上卦
    hu_down = _trigram_of([ls[1], ls[2], ls[3]])
    hu_up = _trigram_of([ls[2], ls[3], ls[4]])
    hu = GUA64[(hu_up, hu_down)]

    return {
        "sum3": sum3,
        "sum4": sum4,
        "shi": shi,
        "up": up,
        "down": down,
        "up2": up2,
        "down2": down2,
        "hu_up": hu_up,
        "hu_down": hu_down,
        "ben_name": ben[0],
        "ben_gua": _gua_label(up, down),
        "ben_symbol": TRIGRAM[up][2] + TRIGRAM[down][2],
        "ben_verdict": ben[1],
        "bian_name": bian[0],
        "bian_gua": _gua_label(up2, down2),
        "bian_symbol": TRIGRAM[up2][2] + TRIGRAM[down2][2],
        "bian_verdict": bian[1],
        "hu_name": hu[0],
        "hu_gua": _gua_label(hu_up, hu_down),
        "hu_symbol": TRIGRAM[hu_up][2] + TRIGRAM[hu_down][2],
        "hu_verdict": hu[1],
        "dong_yao": dong,
        "yixiang": ben[1],
        "ben_lines": ls,
        "bian_lines": bl,
        "hu_lines": _lines(hu_up, hu_down),
        "ben_element": TRIGRAM[up][1],
        "bian_element": TRIGRAM[down2][1],
    }


def tiyong(m: dict) -> dict:
    """体用生克：动爻所在之卦为用，另一卦为体。"""
    dong = m["dong_yao"]
    yong_is_upper = dong > 3
    ti_num = m["down"] if yong_is_upper else m["up"]
    yong_num = m["up"] if yong_is_upper else m["down"]
    ti_el, yong_el = TRIGRAM[ti_num][1], TRIGRAM[yong_num][1]

    if ti_el == yong_el:
        rel, verdict, luck = "比和", "你俩一个调门，点什么都不会错，也别贪多。", 72
    elif SHENG[yong_el] == ti_el:
        rel, verdict, luck = "用生体", "这顿麦是来帮你的，点份好的，别客气。", 84
    elif SHENG[ti_el] == yong_el:
        rel, verdict, luck = "体生用", "你会为这顿多费点力气，点小份就够。", 58
    elif KE[ti_el] == yong_el:
        rel, verdict, luck = "体克用", "你压得住场面，多点一份也不慌。", 70
    else:
        rel, verdict, luck = "用克体", "这顿有点压你，清淡为主，别加辣。", 44

    return {
        "ti_name": TRIGRAM[ti_num][0],
        "ti_element": ti_el,
        "yong_name": TRIGRAM[yong_num][0],
        "yong_element": yong_el,
        "yong_is_upper": yong_is_upper,
        "relation": rel,
        "verdict": verdict,
        "luck": luck,
    }


def wai_ying(lang: str, commits: int, bugs: int, overtime: bool) -> list:
    """程序员今日指标 → 外应（梅花易数「外应」概念，佐证天时）。"""
    w = []
    if commits >= 15:
        w.append("今天提交得挺勤，状态一路往上")
    elif commits > 0:
        w.append(f"今日落笔 {commits} 次，手是热的")
    else:
        w.append("今天还没提交，先歇会儿再干")
    if bugs >= 3:
        w.append(f"错漏缠身 {bugs} 处，今天有点翻车，先别急着重构")
    elif bugs > 0:
        w.append(f"错漏 {bugs} 处，交之前多看一眼")
    if overtime:
        w.append("今天又加班了，早点回去睡")
    return w


def _parse_verdict(v: str):
    """断语「……，宜X，忌Y」→ 宜/忌 两组，去掉「宜」「忌」前缀。

    栏头已经写了「宜」「忌」，条目再带一遍就成了「宜：宜早睡补觉」。
    文案按动宾短语写（「一步一步来」「做减法」），去掉前缀也能独立成句。
    """
    yi, ji = [], []
    for part in v.split("，"):
        if part.startswith("宜"):
            yi.append(part[1:])
        elif part.startswith("忌"):
            ji.append(part[1:])
    return yi, ji


def build_yiji(m: dict, ty: dict, sub: dict, wx: str, now: datetime.datetime = None) -> dict:
    """由本卦/变卦断语 + 体用 + 外应 + 五行，合成今日宜忌（无 MCP 时用）。

    写法：先给卦理来的两条，再给「怎么点」的落地建议，全部说人话。
    """
    yi, ji = [], []
    b_yi, b_ji = _parse_verdict(m["ben_verdict"])
    n_yi, n_ji = _parse_verdict(m["bian_verdict"])
    yi += [x for x in b_yi[:1] if x]
    ji += [x for x in b_ji[:1] if x]
    yi += [x for x in n_yi[:1] if x not in yi]
    ji += [x for x in n_ji[:1] if x not in ji]

    rel = ty["relation"]
    if rel == "用生体":
        yi += ["拉个人一起点，今天有人替你分担", "点份带肉的，别只喝饮料"]
    elif rel == "用克体":
        ji += ["硬着头皮点最辣的", "在店里跟人抢座位"]
    elif rel == "体生用":
        ji += ["加钱加大，今天吃不完"]
    elif rel == "体克用":
        yi += ["多点一份，今天你压得住"]

    commits = sub.get("commits", 0)
    if commits >= 15:
        yi.append(f"加个小食，今天提交了 {commits} 次")
    if sub.get("bugs", 0) > 0:
        ji.append("带着没改完的错去吃饭")
    if sub.get("overtime"):
        ji.append("加班到店里都快打烊")
        yi.append("用麦乐送，别硬撑到店")

    # 今日点单：五行定池、外应与时辰定轮（用克体自动落清淡池，不碰辣）
    if now is None:
        now = datetime.datetime.now()
    order = order_of(wx, rel, sub, now)
    yi.append("点一份" + order)
    yi.append("拉个人拼 1+1 随心配，比单点划算")
    if sub.get("bugs", 0) >= 3:
        yi.append("来份麦旋风压压惊，别跟自己较劲")
    if len(ji) < 2:
        ji.append("点完就走，空着手出门")
    if len(ji) < 3:
        ji.append("边吃边改代码，油手打键盘")

    def _uniq(seq, cap=6):
        out = []
        for x in seq:
            if x and x not in out:
                out.append(x)
        return out[:cap]

    return {"yi": _uniq(yi), "ji": _uniq(ji), "order": order}


def mai_verdict(score: int, ty: dict, sub: dict) -> dict:
    """把分数翻译成「麦气等级 + 一句人话提醒」，三端共用这一套说法。"""
    grades = [
        (82, "上吉", "great", "今天麦气很足，点什么都不会错"),
        (72, "中吉", "good", "今天挺顺，按老规矩点就行"),
        (62, "小吉", "fair", "今天不差，稳着来"),
        (50, "平常", "plain", "今天不功不过，吃饱最要紧"),
        (0, "缓一缓", "slow", "今天差点意思，清淡为主"),
    ]
    grade, key, headline = "平常", "plain", "今天一般"
    for low, g, k, h in grades:
        if score >= low:
            grade, key, headline = g, k, h
            break

    if sub.get("overtime"):
        tip = "活是干不完的，先吃饭"
    elif sub.get("bugs", 0) >= 3:
        tip = "错已经出了，别拿饭赌气"
    elif sub.get("bugs", 0) > 0:
        tip = "小错先记着，吃完再改"
    elif sub.get("commits", 0) >= 15:
        tip = "今天干得够多，加个甜的犒劳下"
    else:
        tip = "别在工位上凑合，站起来去吃"

    return {
        "grade": grade, "grade_key": key, "headline": headline,
        "one_line": ty["verdict"], "tip": tip,
    }



def gua_tags(up: int, down: int) -> list:
    """卦象三个关键词（首页标签用）。"""
    return GUA_TAGS.get((up, down), ["照常", "别折腾", "稳着来"])


def lucky_of(wx: str) -> dict:
    """五行 → 今日幸运物。"""
    return dict(LUCKY.get(wx, LUCKY["土"]))


def yao_hint(m: dict) -> dict:
    """动爻所在的阶段 + 该动该守，翻成人话。"""
    pos = m["dong_yao"]
    line = m["ben_lines"][pos - 1]
    stage, stage_desc = YAO_POS[pos]
    yang_text, yin_text = YAO_MOOD[1]
    return {
        "pos": pos,
        "stage": stage,
        "stage_desc": stage_desc,
        "yin_yang": "阳" if line == 1 else "阴",
        "text": yang_text if line == 1 else yin_text,
    }


def hex_profile(m: dict) -> dict:
    """上下卦各自是什么自然象、什么脾气。"""
    up_n, down_n = m["up"], m["down"]
    ux, un = TRIGRAM_XIANG[up_n]
    dx, dn = TRIGRAM_XIANG[down_n]
    return {
        "up": {"name": TRIGRAM[up_n][0], "xiang": ux, "nature": un, "element": TRIGRAM[up_n][1]},
        "down": {"name": TRIGRAM[down_n][0], "xiang": dx, "nature": dn, "element": TRIGRAM[down_n][1]},
    }


def three_things(yiji: dict, ty: dict, sub: dict) -> dict:
    """首页三件事：一句话该做、一句话别做、一句提醒。"""
    do = yiji["yi"][0] if yiji.get("yi") else "照常点一份"
    dont = yiji["ji"][0] if yiji.get("ji") else "别折腾"
    if sub.get("overtime"):
        note = "加班了就点外卖，别硬撑到店里"
    elif sub.get("bugs", 0) >= 3:
        note = "今天错出得多，先吃饭再修"
    elif ty["relation"] == "用克体":
        note = "这顿有点压你，清淡为主"
    elif ty["relation"] == "用生体":
        note = "今天有人帮你，别一个人扛"
    else:
        note = "吃完再说，工作和饭都凉不得"
    return {"do": do, "dont": dont, "note": note}

def calc(lang: str = "python", commits: int = 0, bugs: int = 0,
         overtime: bool = False, seed: int = None,
         now: datetime.datetime = None) -> dict:
    """梅花易数时间卦 + 体用 + 外应 + 抽卡，返回结构化数据（供模板渲染）。"""
    if now is None:
        now = datetime.datetime.now()

    m = meihua(now)
    ty = tiyong(m)
    wx, wx_desc = LANG_WUXING.get((lang or "python").lower(),
                                  ("土", "话不多但靠得住，遇事不慌"))
    sub = {"lang": lang, "commits": commits, "bugs": bugs, "overtime": overtime}
    wai = wai_ying(lang, commits, bugs, overtime)

    # 抽卡：同一时辰同一指标必得同卡（与前端同式，便于两版互验）
    if seed is None:
        seed = (commits * 7 + bugs * 13 + (5 if overtime else 0)
                + now.year * 10000 + now.month * 100 + now.day * 10 + now.hour)
    card = MING_CARDS[seed % len(MING_CARDS)]

    # 综合评分：以今日落笔为基，再与体用之气相参
    base = 60 + min(commits, 20) * 1 - bugs * 4 - (8 if overtime else 0)
    base = max(30, min(96, base))
    score = round(base * 0.6 + ty["luck"] * 0.4)
    score = max(30, min(96, score))

    yiji = build_yiji(m, ty, sub, wx, now)

    return {
        "meta": {
            "title": "麦门占卜 · 程序员麦占",
            "generated_at": now.strftime("%Y-%m-%d %H:%M"),
            "date": now.strftime("%Y-%m-%d"),
            "hour": now.strftime("%H:%M"),
            "author": "墨喵",
            "method": "梅花易数时间卦（零输入，以当前时辰起卦）",
        },
        "subject": sub,
        "meihua": m,
        "tiyong": ty,
        "wai_ying": wai,
        "lang_wuxing": {"element": wx, "desc": wx_desc},
        "card": {"name": card[0], "star": card[1], "blessing": card[2]},
        "score": score,
        "mai": mai_verdict(score, ty, sub),
        "yiji": yiji,
        "tags": gua_tags(m["up"], m["down"]),
        "profile": hex_profile(m),
        "lucky": lucky_of(wx),
        "yao_hint": yao_hint(m),
        "three": three_things(yiji, ty, sub),
    }


def main():
    ap = argparse.ArgumentParser(description="麦门占卜·程序员麦占 引擎（梅花易数时间卦，离线）")
    ap.add_argument("--lang", default="python", help="主编程语言")
    ap.add_argument("--commits", type=int, default=0, help="今日 commit 数")
    ap.add_argument("--bugs", type=int, default=0, help="今日 bug 数")
    ap.add_argument("--overtime", action="store_true", help="是否加班")
    ap.add_argument("--seed", type=int, default=None, help="抽卡随机种子（复现用）")
    ap.add_argument("--out", default=None, help="输出 JSON 路径")
    a = ap.parse_args()
    data = calc(a.lang, a.commits, a.bugs, a.overtime, a.seed)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("written ->", a.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
