// 麦门占卜·程序员麦占 —— 小红书小程序页面逻辑
// 梅花易数时间卦（零输入）+ 体用生克 + 外应 + 抽卡；纯前端，无 Token。
// 与 scripts/fortune_engine.py 同源同式，勿单改。

const GUA64 = {
  "1,1":["乾为天","天时正好，宜一口气把活儿干完，忌嘴上一句「马上就好」"],
  "8,8":["坤为地","地气够稳，宜老老实实吃顿饱的，忌硬撑着节食"],
  "6,4":["水雷屯","开局就卡，宜先来份薯条垫垫，忌空着肚子改需求"],
  "7,6":["山水蒙","脑子没开机，宜问清楚了再动手，忌瞎猜产品想要啥"],
  "6,1":["水天需","还得再等等，宜先来个圆筒，忌催着上线"],
  "1,6":["天水讼","容易抬杠，宜退半步吃口堡，忌在群里跟人对线"],
  "8,6":["地水师","人多事也杂，宜分好工各点各的，忌一锅乱炖"],
  "6,8":["水地比","人缘挺旺，宜拉个人拼个随心配，忌自己闷头吃"],
  "5,1":["风天小畜","攒着点好，宜加个小食不加大，忌一顿点太多"],
  "1,2":["天泽履","步步踩线，宜小心着提交，忌手一抖 force push"],
  "8,1":["地天泰","通泰顺遂，宜照着计划走，忌临时给自己加戏"],
  "1,8":["天地否","气有点堵，宜先搁着别硬推，忌今天硬上线"],
  "1,3":["天火同人","合得来，宜结对子一起干，忌各改各的"],
  "3,1":["火天大有","手气正旺，宜点份好的犒劳自己，忌一个人吃独食"],
  "8,7":["地山谦","低调点好，宜闷声吃堡，忌发圈炫加班"],
  "4,8":["雷地豫","心情不错，宜慢慢吃不着急，忌边吃边改 bug"],
  "2,4":["泽雷随","跟着走就行，宜听安排，忌另开一摊"],
  "7,5":["山风蛊","旧账要清，宜先收拾烂摊子，忌再堆新需求"],
  "8,2":["地泽临","适合靠近点，宜当面聊两句，忌在文档里打太极"],
  "5,8":["风地观","先看着别急，宜摸清底细，忌抢着表态"],
  "3,4":["火雷噬嗑","有硬骨头，宜先啃最难的，忌拖到下班"],
  "7,3":["山火贲","适合包装，宜把 demo 弄漂亮点，忌只剩个壳"],
  "7,8":["山地剥","有点漏气，宜收着点，忌大改特改"],
  "8,4":["地雷复","缓过来了，宜早睡补觉，忌熬夜硬扛"],
  "1,4":["天雷无妄","别乱来，宜守规矩，忌顺手改别人的代码"],
  "7,1":["山天大畜","劲攒足了，宜蓄着待发，忌现在就 all in"],
  "7,4":["山雷颐","该补了，宜正经吃一顿，忌拿咖啡当饭"],
  "2,5":["泽风大过","有点过头，宜适可而止，忌一口气点三份"],
  "6,6":["坎为水","坑有点多，宜稳着走，忌硬闯"],
  "3,3":["离为火","状态在线，宜多输出，忌光说不动手"],
  "2,7":["泽山咸","容易来电，宜真诚点，忌端着架子"],
  "4,5":["雷风恒","贵在坚持，宜按节奏来，忌干两天停三天"],
  "1,7":["天山遯","该撤就撤，宜早点下班，忌死磕到底"],
  "4,1":["雷天大壮","气势够足，宜趁热打铁，忌用力过猛"],
  "3,8":["火地晋","往上升，宜主动争取，忌等着被发现"],
  "8,3":["地火明夷","光被遮住，宜低调养着，忌抢风头"],
  "5,3":["风火家人","适合收拾，宜整理下工位，忌管别人闲事"],
  "3,2":["火泽睽","有点拧巴，宜求同存异，忌非要分个对错"],
  "6,7":["水山蹇","路不好走，宜绕一绕，忌硬顶"],
  "4,6":["雷水解","结开了，宜把拖着的事办掉，忌继续攒"],
  "7,2":["山泽损","该减了，宜做减法，忌什么都想要"],
  "5,4":["风雷益","有进益，宜顺手帮人一把，忌独占好处"],
  "2,1":["泽天夬","该断了，宜果断砍需求，忌犹犹豫豫"],
  "1,5":["天风姤","容易撞上，宜留个心眼，忌什么局都去"],
  "2,8":["泽地萃","人聚齐了，宜组个饭局，忌各吃各的"],
  "8,5":["地风升","慢慢往上，宜一步一步来，忌想一步登天"],
  "2,6":["泽水困","有点困住，宜先歇口气，忌硬求"],
  "6,5":["水风井","井水不枯，宜复盘沉淀，忌原地打转"],
  "2,3":["泽火革","该换了，宜推倒重来，忌修修补补"],
  "3,5":["火风鼎","要上新，宜换套新方案，忌将就"],
  "4,4":["震为雷","动静不小，宜开个新坑，忌犹豫半天"],
  "7,7":["艮为山","该停了，宜收工走人，忌再改一版"],
  "5,7":["风山渐","慢慢来，宜按部就班，忌跳步骤"],
  "4,2":["雷泽归妹","别急着定，宜先说清楚，忌仓促答应"],
  "4,3":["雷火丰","正当其时，宜趁势干票大的，忌过了头"],
  "3,7":["火山旅","在外奔波，宜就近吃，忌跑太远"],
  "5,5":["巽为风","润物无声，宜小步推进，忌硬刚"],
  "2,2":["兑为泽","和气生财，宜好好说话，忌嘴上不饶人"],
  "5,6":["风水涣","该散了，宜把心结解开，忌憋着"],
  "6,2":["水泽节","有节制，宜量力点单，忌报复性消费"],
  "5,2":["风泽中孚","讲信用，宜说到做到，忌画大饼"],
  "4,7":["雷山小过","小事可为，宜小改小动，忌大动干戈"],
  "6,3":["水火既济","事已成了，宜收尾查一遍，忌松劲"],
  "3,6":["火水未济","还差一点，宜善始善终，忌最后翻车"]
};

const TRIGRAM = {
  1:["乾","金","☰"], 2:["兑","金","☱"], 3:["离","火","☲"], 4:["震","木","☳"],
  5:["巽","木","☴"], 6:["坎","水","☵"], 7:["艮","土","☶"], 8:["坤","土","☷"]
};
const SHENG = {木:"火",火:"土",土:"金",金:"水",水:"木"};
const KE    = {木:"土",土:"水",水:"火",火:"金",金:"木"};
const MCD_REAL = require("../../data/mcd_real.js");
/* 实时数据（可选）：Token 从 config/token.js 注入（不入库）；没有就整段退回快照。
 * require 全部防呆：对拍脚本会把计算区切到临时目录求值，缺模块时静默为 null。 */
var LIVE_REAL = null;
var MCD_CFG = null, MCD_API = null;
try { MCD_CFG = require("../../config/token.js"); } catch (e) { MCD_CFG = null; }
try { MCD_API = require("../../utils/mcd_api.js"); } catch (e) { MCD_API = null; }

const LANG_WUXING = {
  python:["水","水一样的语言，绕得过坎，最适合写业务逻辑"],
  java:["土","厚土压得住场，企业级系统还得看它"],
  c:["金","最贴机器的语言，硬核但不好伺候"],
  "c++":["金","一把锋利的刀，能砍硬骨头也能砍到自己"],
  go:["木","长得快、并发多，云上跑得欢"],
  rust:["金","炼得很纯的铁，编译器比你还操心"],
  javascript:["火","点着就着，前端全靠它照亮"],
  typescript:["火","给火加了个炉膛，烧得旺还不乱窜"],
  php:["土","老土壤了，半个互联网都长在上面"],
  ruby:["木","柔软好使，写着写着人就开心了"],
  kotlin:["土","安卓的老底子，稳当还爱纳新"],
  swift:["金","快得像风，果家的专属刀"],
  lua:["木","轻得像叶子，嵌进哪儿都能活"]
};
const LANGS = ["python", "java", "go", "rust", "typescript", "javascript", "c", "c++", "php", "ruby", "kotlin", "swift", "lua"];
const MING_CARDS = [
  ["巨无霸","双层至尊","两片牛肉夹住你今天的 KPI，吃它就等于给自己盖了个稳章"],
  ["麦辣鸡腿堡","辣度担当","一口下去思路就通了，辣是程序员的强制刷新"],
  ["麦旋风","转圈大师","脑子转不动就先吃口转的，转着转着就想通了"],
  ["薯条","万恶之源","一根接一根，进度和薯条一起见底，记得多要两包番茄酱"],
  ["麦乐鸡","六块正好","不多不少正好六块，够你撑到下一次提交"],
  ["吉士汉堡","一片芝士","朴素但顶饱，今天不折腾，稳稳收工"],
  ["板烧鸡腿堡","不炸主义者","不油炸也香，今天走温和路线，别硬刚"],
  ["圆筒冰淇淋","甜筒收尾","甜的先顶上，苦的放明天，一天才算完整"]
];
/* 今日点单池：五行定池，外应与时辰定轮（与 Python 引擎、网页版同式） */
const ORDER_POOL = {
  "金": ["薯条配麦乐鸡", "麦香鱼配薯条", "麦乐鸡配玉米杯", "薯条配圆筒冰淇淋"],
  "木": ["板烧鸡腿堡配鲜蔬杯", "双吉汉堡配鲜煮咖啡", "麦香鱼配蔬菜色拉", "吉士汉堡配玉米杯"],
  "水": ["麦旋风配可乐", "圆筒冰淇淋配麦乐鸡", "麦乐鸡配冰咖啡", "冰咖啡配吉士汉堡"],
  "火": ["麦辣鸡腿堡", "麦辣鸡翅配可乐", "麦辣鸡腿堡配薯条", "麦辣鸡翅配麦乐鸡"],
  "土": ["巨无霸", "双层吉士汉堡配薯条", "巨无霸配麦乐鸡", "吉士汉堡配薯饼"]
};
const MILD_POOL = ["麦香鱼配薯条", "板烧鸡腿堡配鲜蔬杯", "吉士汉堡配可乐", "玉米杯配麦乐鸡"];
const BREAKFAST_POOL = ["猪柳蛋麦满分配薯饼", "吉士蛋麦满分配热香饼", "猪柳蛋麦满分配豆浆", "薯饼配热豆浆"];
function orderOf(wx, rel, sub, dt) {
  var lang = (sub.lang || "").toLowerCase();
  var lh = 0;
  for (var i = 0; i < lang.length; i++) lh += lang.charCodeAt(i);
  var seed = sub.commits * 3 + sub.bugs * 5 + (sub.overtime ? 7 : 0) + lh + dt.getHours();
  var pool = (dt.getHours() >= 5 && dt.getHours() < 10) ? BREAKFAST_POOL
    : (rel === "用克体" ? MILD_POOL
    : (ORDER_POOL[wx] || ORDER_POOL["土"]));
  return pool[((seed % pool.length) + pool.length) % pool.length];
}
const ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"];
const GAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"];

/* ── 结果维度（与 Python 引擎同源） ── */
const GUA_TAGS = {
  "1,1": ["开足马力", "一次做完", "别嘴硬"],
  "8,8": ["稳住", "吃饱", "别硬撑"],
  "6,4": ["开局卡", "先垫一口", "别空肚改需求"],
  "7,6": ["没开机", "先问清", "别瞎猜"],
  "6,1": ["再等等", "先来口甜的", "别催上线"],
  "1,6": ["易抬杠", "退半步", "别对线"],
  "8,6": ["人多事杂", "分好工", "别一锅炖"],
  "6,8": ["人缘好", "拉个伴", "别闷头吃"],
  "5,1": ["攒着", "小份就够", "别点太多"],
  "1,2": ["踩线", "小心提交", "别手抖"],
  "8,1": ["顺", "按计划", "别加戏"],
  "1,8": ["气堵", "先搁着", "别硬推"],
  "1,3": ["合得来", "结对子", "别各改各的"],
  "3,1": ["手气旺", "点份好的", "别吃独食"],
  "8,7": ["低调", "闷声吃", "别炫加班"],
  "4,8": ["心情好", "慢慢吃", "别边吃边改"],
  "2,4": ["跟着走", "听安排", "别另开摊"],
  "7,5": ["清旧账", "先收摊子", "别堆需求"],
  "8,2": ["靠近点", "当面聊", "别打太极"],
  "5,8": ["先看戏", "摸清底", "别抢表态"],
  "3,4": ["硬骨头", "先啃难的", "别拖到下班"],
  "7,3": ["好包装", "弄漂亮点", "别只剩壳"],
  "7,8": ["漏气", "收着点", "别大改"],
  "8,4": ["回血", "早睡", "别熬夜"],
  "1,4": ["别乱来", "守规矩", "别动别人代码"],
  "7,1": ["蓄力", "攒着待发", "别 all in"],
  "7,4": ["该补了", "正经吃一顿", "别拿咖啡当饭"],
  "2,5": ["过头", "适可而止", "别点三份"],
  "6,6": ["坑多", "稳着走", "别硬闯"],
  "3,3": ["在线", "多输出", "别光说"],
  "2,7": ["来电", "真诚点", "别端架子"],
  "4,5": ["长跑", "按节奏", "别三天打鱼"],
  "1,7": ["该撤", "早点走", "别死磕"],
  "4,1": ["气势足", "趁热打铁", "别用力过猛"],
  "3,8": ["上升", "主动争取", "别等着被发现"],
  "8,3": ["藏锋芒", "养着", "别抢风头"],
  "5,3": ["收拾", "整工位", "别管闲事"],
  "3,2": ["拧巴", "求同存异", "别争对错"],
  "6,7": ["路难走", "绕一绕", "别硬顶"],
  "4,6": ["解结", "办掉拖着的事", "别继续攒"],
  "7,2": ["做减法", "让一点", "别什么都想要"],
  "5,4": ["有进益", "帮人一把", "别独占"],
  "2,1": ["该断", "砍需求", "别犹豫"],
  "1,5": ["易撞上", "留心眼", "别什么局都去"],
  "2,8": ["人聚齐", "组个饭局", "别各吃各的"],
  "8,5": ["慢慢上", "一步一格", "别想一步登天"],
  "2,6": ["困住", "歇口气", "别硬求"],
  "6,5": ["不枯", "复盘沉淀", "别原地打转"],
  "2,3": ["该换", "推倒重来", "别修补"],
  "3,5": ["上新", "换新方案", "别将就"],
  "4,4": ["动静大", "开个新坑", "别犹豫"],
  "7,7": ["该停", "收工走人", "别再改一版"],
  "5,7": ["慢慢来", "按部就班", "别跳步骤"],
  "4,2": ["别急定", "先问清楚", "别仓促答应"],
  "4,3": ["正当其时", "干票大的", "别过头"],
  "3,7": ["在外跑", "就近吃", "别跑太远"],
  "5,5": ["润物无声", "小步推进", "别硬刚"],
  "2,2": ["和气", "好好说话", "别嘴上不饶人"],
  "5,6": ["该散", "解开结", "别憋着"],
  "6,2": ["有节制", "量力点单", "别报复性消费"],
  "5,2": ["讲信用", "说到做到", "别画饼"],
  "4,7": ["小事可为", "小改小动", "别大动干戈"],
  "6,3": ["已成", "收尾查一遍", "别松劲"],
  "3,6": ["差一点", "善始善终", "别最后翻车"]
};
const TRIGRAM_XIANG = {
  1: ["天", "刚健、往上顶、爱硬碰"],
  2: ["泽", "喜悦、会说话、好交朋友"],
  3: ["火", "明亮、显眼、烧得快"],
  4: ["雷", "动、突然、说来就来"],
  5: ["风", "渗透、顺着走、无孔不入"],
  6: ["水", "险、绕、藏得深"],
  7: ["山", "停、稳、过不去就歇着"],
  8: ["地", "承载、厚、什么都接得住"]
};
const LUCKY_MAP = {"金": {"color": "白 / 银", "num": "4 和 9", "dir": "西边", "hour": "15–19 点", "item": "薯条"}, "木": {"color": "青 / 绿", "num": "3 和 8", "dir": "东边", "hour": "7–11 点", "item": "板烧鸡腿堡"}, "水": {"color": "黑 / 蓝", "num": "1 和 6", "dir": "北边", "hour": "21–1 点", "item": "麦旋风"}, "火": {"color": "红 / 橙", "num": "2 和 7", "dir": "南边", "hour": "11–15 点", "item": "麦辣鸡腿堡"}, "土": {"color": "黄 / 棕", "num": "5 和 10", "dir": "中间（就工位）", "hour": "13–17 点", "item": "巨无霸"}};
const YAO_POS = {"1": ["刚起步", "今天才开头"], "2": ["在自己那摊", "手上的活最要紧"], "3": ["进退两难", "跨出去回不来，卡在中间"], "4": ["到了门外", "事到临头，得问一句"], "5": ["坐在主位", "今天你能拍板"], "6": ["走到头了", "这一程该收了"]};

function tagsOf(up, down) {
  return GUA_TAGS[up + "," + down] || ["照常", "别折腾", "稳着来"];
}
function luckyOf(wx) {
  return LUCKY_MAP[wx] || LUCKY_MAP["土"];
}
function yaoHint(m) {
  var pos = m.dong, line = m.benLines[pos - 1], st = YAO_POS[String(pos)];
  return {
    pos: pos,
    posCn: ["一", "二", "三", "四", "五", "六"][pos - 1],
    stage: st[0],
    stageDesc: st[1],
    yinYang: line === 1 ? "阳" : "阴",
    text: line === 1 ? "阳爻动，宜主动出击，该说就说" : "阴爻动，宜先守着，别抢出头"
  };
}
function profileOf(m) {
  var yongUp = m.dong > 3;
  var tiN = yongUp ? m.down : m.up;
  var yoN = yongUp ? m.up : m.down;
  return {
    tiXiang: TRIGRAM_XIANG[tiN][0], tiNature: TRIGRAM_XIANG[tiN][1],
    yongXiang: TRIGRAM_XIANG[yoN][0], yongNature: TRIGRAM_XIANG[yoN][1]
  };
}
function noteOf(ty, sub) {
  if (sub.overtime) return "加班了就点外卖，别硬撑到店里";
  if (sub.bugs >= 3) return "今天错出得多，先吃饭再修";
  if (ty.rel === "用克体") return "这顿有点压你，清淡为主";
  if (ty.rel === "用生体") return "今天有人帮你，别一个人扛";
  return "吃完再说，工作和饭都凉不得";
}


/* ---------------- 卦体 ---------------- */
function pad2(n) { return n < 10 ? "0" + n : "" + n; }
function shiOf(h) { return (Math.floor((h + 1) / 2) % 12) + 1; }

/* 先天数 → 六爻：以 (数-1) 的三位二进制 B2B1B0 为准，
   B2 位对应初爻、B0 位对应上爻，爻象与位取值相反。
   故取第 i 爻（i=0 为初爻）时读第 (2-i) 位。 */
function linesOf(up, down) {
  var out = [], i;
  for (i = 0; i < 3; i++) out.push(1 - (((down - 1) >> (2 - i)) & 1));
  for (i = 0; i < 3; i++) out.push(1 - (((up - 1) >> (2 - i)) & 1));
  return out;
}
function trigramOf(l3) {
  var bits = 0, i;
  for (i = 0; i < 3; i++) bits |= (1 - l3[i]) << (2 - i);
  return bits + 1;
}
function hexRows(lines, dong) {
  var rows = [], i;
  for (i = 5; i >= 0; i--) {
    rows.push({ i: 5 - i, yin: lines[i] !== 1, dong: dong === i + 1, on: true });
  }
  return rows;
}
function guaLabel(up, down) {
  if (up === down) return GUA64[up + "," + down][0];
  return TRIGRAM[up][0] + "上" + TRIGRAM[down][0];
}

function meihua(dt) {
  var y = dt.getFullYear(), mo = dt.getMonth() + 1, d = dt.getDate(), h = dt.getHours();
  var sum3 = y + mo + d;
  var shi = shiOf(h);
  var sum4 = sum3 + shi;
  var up = (sum3 % 8) || 8;
  var down = (sum4 % 8) || 8;
  var dong = (sum4 % 6) || 6;

  var ben = GUA64[up + "," + down];

  // 六爻卦画（自下而上）：互卦、变卦均由它派生，保证「画」与「名」同源
  var ls = linesOf(up, down);
  var bl = ls.slice();
  bl[dong - 1] = 1 - bl[dong - 1];
  var down2 = trigramOf(bl.slice(0, 3));
  var up2 = trigramOf(bl.slice(3, 6));
  var bian = GUA64[up2 + "," + down2];

  var huDown = trigramOf([ls[1], ls[2], ls[3]]);
  var huUp = trigramOf([ls[2], ls[3], ls[4]]);
  var hu = GUA64[huUp + "," + huDown];

  return {
    y: y, mo: mo, d: d, h: h, shi: shi, sum3: sum3, sum4: sum4,
    up: up, down: down, up2: up2, down2: down2, huUp: huUp, huDown: huDown, dong: dong,
    benName: ben[0], benVerdict: ben[1], benGua: guaLabel(up, down),
    bianName: bian[0], bianVerdict: bian[1], bianGua: guaLabel(up2, down2),
    huName: hu[0], huVerdict: hu[1], huGua: guaLabel(huUp, huDown),
    benLines: ls, bianLines: bl, huLines: linesOf(huUp, huDown)
  };
}

function tiyong(m) {
  var yongIsUpper = m.dong > 3;
  var tiNum = yongIsUpper ? m.down : m.up;
  var yongNum = yongIsUpper ? m.up : m.down;
  var tiEl = TRIGRAM[tiNum][1], yongEl = TRIGRAM[yongNum][1];
  var rel, verdict, luck;
  if (tiEl === yongEl) {
    rel = "比和"; verdict = "你俩一个调门，点什么都不会错，也别贪多。"; luck = 72;
  } else if (SHENG[yongEl] === tiEl) {
    rel = "用生体"; verdict = "这顿麦是来帮你的，点份好的，别客气。"; luck = 84;
  } else if (SHENG[tiEl] === yongEl) {
    rel = "体生用"; verdict = "你会为这顿多费点力气，点小份就够。"; luck = 58;
  } else if (KE[tiEl] === yongEl) {
    rel = "体克用"; verdict = "你压得住场面，多点一份也不慌。"; luck = 70;
  } else {
    rel = "用克体"; verdict = "这顿有点压你，清淡为主，别加辣。"; luck = 44;
  }
  return {
    tiName: TRIGRAM[tiNum][0], tiEl: tiEl,
    yongName: TRIGRAM[yongNum][0], yongEl: yongEl,
    yongIsUpper: yongIsUpper, rel: rel, verdict: verdict, luck: luck
  };
}

/* ---------------- 外应 · 宜忌 · 命卡 · 麦气 ---------------- */
function waiYing(sub) {
  var w = [];
  if (sub.commits >= 15) w.push("今天提交得挺勤，状态一路往上");
  else if (sub.commits > 0) w.push("今天提交了 " + sub.commits + " 次，手是热的");
  else w.push("今天还没提交，先歇会儿再干");
  if (sub.bugs >= 3) w.push("今天翻车 " + sub.bugs + " 处，先别急着重构");
  else if (sub.bugs > 0) w.push("有 " + sub.bugs + " 处小错，交之前多看一眼");
  if (sub.overtime) w.push("今天又加班了，早点回去睡");
  return w;
}

function parseVerdict(v) {
  var yi = [], ji = [];
  v.split("，").forEach(function (p) {
    if (p.charAt(0) === "宜") yi.push(p.slice(1));
    else if (p.charAt(0) === "忌") ji.push(p.slice(1));
  });
  return { yi: yi, ji: ji };
}

function buildYiji(m, ty, sub, wx, dt) {
  var b = parseVerdict(m.benVerdict), n = parseVerdict(m.bianVerdict);
  var yi = b.yi.slice(0, 1);
  var ji = b.ji.slice(0, 1);
  n.yi.slice(0, 1).forEach(function (x) { if (yi.indexOf(x) < 0) yi.push(x); });
  n.ji.slice(0, 1).forEach(function (x) { if (ji.indexOf(x) < 0) ji.push(x); });

  if (ty.rel === "用生体") {
    yi.push("拉个人一起点，今天有人替你分担", "点份带肉的，别只喝饮料");
  } else if (ty.rel === "用克体") {
    ji.push("硬着头皮点最辣的", "在店里跟人抢座位");
  } else if (ty.rel === "体生用") {
    ji.push("加钱加大，今天吃不完");
  } else if (ty.rel === "体克用") {
    yi.push("多点一份，今天你压得住");
  }

  if (sub.commits >= 15) yi.push("加个小食，今天提交了 " + sub.commits + " 次");
  if (sub.bugs > 0) ji.push("带着没改完的错去吃饭");
  if (sub.overtime) {
    ji.push("加班到店里都快打烊");
    yi.push("用麦乐送，别硬撑到店");
  }

  var order = orderOf(wx, ty.rel, sub, dt);
  yi.push("点一份" + order);
  yi.push("拉个人拼 1+1 随心配，比单点划算");
  if (sub.bugs >= 3) yi.push("来份麦旋风压压惊，别跟自己较劲");
  if (ji.length < 2) ji.push("点完就走，空着手出门");
  if (ji.length < 3) ji.push("边吃边改代码，油手打键盘");

  function uniq(seq) {
    var out = [];
    seq.forEach(function (x) { if (x && out.indexOf(x) < 0) out.push(x); });
    return out.slice(0, 6);
  }
  return { yi: uniq(yi), ji: uniq(ji), order: order };
}

function cardIndexOf(sub, dt) {
  var seed = sub.commits * 7 + sub.bugs * 13 + (sub.overtime ? 5 : 0)
    + dt.getFullYear() * 10000 + (dt.getMonth() + 1) * 100 + dt.getDate() * 10 + dt.getHours();
  return ((seed % MING_CARDS.length) + MING_CARDS.length) % MING_CARDS.length;
}

function calcScore(sub, ty) {
  var base = 60 + Math.min(sub.commits, 20) - sub.bugs * 4 - (sub.overtime ? 8 : 0);
  base = Math.max(30, Math.min(96, base));
  return Math.max(30, Math.min(96, Math.round(base * 0.6 + ty.luck * 0.4)));
}

function maiVerdict(score, ty, sub) {
  var grades = [
    [82, "上吉", "今天麦气很足，点什么都不会错"],
    [72, "中吉", "今天挺顺，按老规矩点就行"],
    [62, "小吉", "今天不差，稳着来"],
    [50, "平常", "今天不功不过，吃饱最要紧"],
    [0, "缓一缓", "今天差点意思，清淡为主"]
  ];
  var grade = "平常", headline = "今天不功不过，吃饱最要紧", i;
  for (i = 0; i < grades.length; i++) {
    if (score >= grades[i][0]) { grade = grades[i][1]; headline = grades[i][2]; break; }
  }
  var tip;
  if (sub.overtime) tip = "活是干不完的，先吃饭";
  else if (sub.bugs >= 3) tip = "错已经出了，别拿饭赌气";
  else if (sub.bugs > 0) tip = "小错先记着，吃完再改";
  else if (sub.commits >= 15) tip = "今天干得够多，加个甜的犒劳下";
  else tip = "别在工位上凑合，站起来去吃";
  return { grade: grade, headline: headline, oneLine: ty.verdict, tip: tip };
}

/* ---------------- 页面 ---------------- */
Page({
  data: {
    asked: false,
    ritual: false,
    view: "today",
    cardOpen: false,
    tabs: [
      { k: "today", name: "今日" },
      { k: "gua", name: "卦象" },
      { k: "store", name: "门店" },
      { k: "me", name: "我的" }
    ],
    real: null,
    rHex: [],
    langs: LANGS,
    langIndex: 0,
    lang: "python",
    form: { commits: "0", bugs: "0" },
    overtime: false,
    dateStr: "",
    hourStr: "",
    ganzhi: "",
    wxEl: "水",
    wxDesc: "",
    openDetail: false,
    openForm: false,
    openNote: false,
    vm: null
  },

  onLoad: function () {
    this.refreshClock();
    this.refreshWx();
    this.fetchReal();
  },

  /* 实时只读咨询：拿到就换源重渲染；失败静默退回快照，不弹窗不打扰 */
  fetchReal: function () {
    var self = this;
    if (!MCD_CFG || !MCD_CFG.MCD_MCP_TOKEN || MCD_CFG.MCD_MCP_TOKEN.indexOf("粘贴") >= 0) return;
    MCD_API.consult(MCD_CFG.MCD_MCP_TOKEN, MCD_CFG.CITY, MCD_CFG.KEYWORD)
      .then(function (res) {
        if (!res || !res.ok) return;
        LIVE_REAL = res;
        if (self.data.asked) self.render(false);   /* 已出过卦：静默换实时数据 */
      });
  },

  refreshClock: function () {
    var now = new Date();
    var y = now.getFullYear();
    this.setData({
      dateStr: y + "-" + pad2(now.getMonth() + 1) + "-" + pad2(now.getDate()),
      hourStr: ZHI[shiOf(now.getHours()) - 1] + "时",
      ganzhi: GAN[(y - 4) % 10] + ZHI[(y - 4) % 12] + "年"
    });
  },

  refreshWx: function () {
    var pair = LANG_WUXING[this.data.lang] || ["土", "话不多但靠得住，遇事不慌"];
    var self = this;
    this.setData({ wxEl: pair[0], wxDesc: pair[1] }, function () {
      if (self.data.asked) self.render(false);
    });
  },

  onLang: function (e) {
    var i = parseInt(e.detail.value, 10) || 0;
    var self = this;
    this.setData({ langIndex: i, lang: LANGS[i] }, function () {
      self.refreshWx();
    });
  },

  onInput: function (e) {
    /* 模板里写的是 data-k，这里原来读 dataset.field → 永远是 undefined，
       等于输入框完全不起作用（填了也不进 form）。两个键都认，避免再错一次。 */
    var ds = e.currentTarget.dataset || {};
    var k = ds.k || ds.field;
    if (!k) return;
    var obj = {};
    obj["form." + k] = e.detail.value;
    var self = this;
    this.setData(obj, function () {
      if (!self.data.asked) return;
      clearTimeout(self._t);
      self._t = setTimeout(function () { self.render(false); }, 260);
    });
  },

  onOt: function (e) {
    var on = e.detail && typeof e.detail.value === "boolean" ? e.detail.value : !this.data.overtime;
    var self = this;
    this.setData({ overtime: on }, function () {
      if (self.data.asked) self.render(false);
    });
  },

  onRecalc: function () {
    this.render(false);
    if (typeof xhs !== "undefined" && xhs.showToast) xhs.showToast({ title: "按新数重批了一次", icon: "none" });
  },

  onCard: function () {
    if (!this.data.vm) return;
    this.setData({ cardOpen: true });
  },

  onCloseCard: function () {
    this.setData({ cardOpen: false });
  },

  noop: function () {},

  onAgain: function () {
    this.setData({ cardOpen: false });
    this.onGo();
  },

  onTab: function (e) {
    var v = e.currentTarget.dataset.v;
    if (!v) return;
    this.setData({ view: v });
    if (wx.pageScrollTo) wx.pageScrollTo({ scrollTop: 0, duration: 0 });
  },

  onFold: function (e) {
    var k = e.currentTarget.dataset.k;
    if (!k) return;
    var patch = {};
    patch[k] = !this.data[k];
    this.setData(patch);
  },

  onGo: function () {
    if (this.data.ritual) return;
    var self = this;
    var now = new Date();
    var m = meihua(now);
    this.refreshClock();

    var rows = hexRows(m.benLines, m.dong).map(function (r) {
      r.on = false;
      return r;
    });
    this.setData({ ritual: true, rHex: rows, openDetail: false });

    // 逐爻自下而上显现：rHex 自顶向下，故自 index 5 起
    var step = 0;
    var timer = setInterval(function () {
      var idx = 5 - step;
      if (idx < 0) { clearInterval(timer); return; }
      var patch = {};
      patch["rHex[" + idx + "].on"] = true;
      self.setData(patch);
      step++;
      if (step >= 6) {
        clearInterval(timer);
        setTimeout(function () {
          self.setData({ ritual: false });
          self.render(true);
        }, 420);
      }
    }, 150);
  },

  render: function (withRitual) {
    var now = new Date();
    var sub = {
      lang: this.data.lang,
      commits: Math.max(0, parseInt(this.data.form.commits, 10) || 0),
      bugs: Math.max(0, parseInt(this.data.form.bugs, 10) || 0),
      overtime: !!this.data.overtime
    };
    var pair = LANG_WUXING[sub.lang] || ["土", "话不多但靠得住，遇事不慌"];
    var wx = pair[0];

    var m = meihua(now);
    var ty = tiyong(m);
    var yj = buildYiji(m, ty, sub, wx, now);
    var card = MING_CARDS[cardIndexOf(sub, now)];
    var score = calcScore(sub, ty);
    var mv = maiVerdict(score, ty, sub);
    var wai = waiYing(sub);

    var vm = {
      benName: m.benName,
      benGua: m.benGua === m.benName ? "纯卦" : m.benGua,
      benSay: m.benVerdict,
      bianName: m.bianName,
      dong: m.dong,
      mai: { num: score, grade: mv.grade, head: mv.headline, tip: mv.tip, order: yj.order },
      hexMain: hexRows(m.benLines, m.dong),
      tris: [
        { label: "本卦 · 你的主食", now: true, hex: hexRows(m.benLines, m.dong), name: m.benName, gua: m.benGua === m.benName ? "纯卦" : m.benGua, say: m.benVerdict },
        { label: "过程 · 吃到一半", now: false, hex: hexRows(m.huLines, 0), name: m.huName, gua: m.huGua === m.huName ? "纯卦" : m.huGua, say: m.huVerdict },
        { label: "收尾 · 吃完之后", now: false, hex: hexRows(m.bianLines, 0), name: m.bianName, gua: m.bianGua === m.bianName ? "纯卦" : m.bianGua, say: m.bianVerdict }
      ],
      ti: {
        note: "动爻在第 " + m.dong + " 爻，" + (ty.yongIsUpper ? "上卦" : "下卦") + "是「这顿麦」，"
          + (ty.yongIsUpper ? "下卦" : "上卦") + "是「你」。" + ty.verdict,
        tiName: ty.tiName + " · 属" + ty.tiEl,
        yongName: ty.yongName + " · 属" + ty.yongEl,
        rel: ty.rel,
        luck: ty.luck
      },
      wai: wai,
      yi: yj.yi,
      ji: yj.ji,
      card: { name: card[0], star: card[1], blessing: card[2] },
      score: score,
      quote: "《" + m.benName + "》：" + m.benVerdict.split("，")[0] + "。",
      zhiShi: ZHI[m.shi - 1] + "时",
      hexMainGua: (m.benGua === m.benName ? "纯卦" : m.benGua) + " · " + ZHI[m.shi - 1] + "时起",
      tagLine: tagsOf(m.up, m.down).join(" · "),
      huName: m.huName,
      qi: {
        time: m.y + " 年 " + m.mo + " 月 " + m.d + " 日 " + ZHI[m.shi - 1] + "时",
        up: (m.sum3 % 8 || 8) + " → " + TRIGRAM[m.up][0] + "（" + TRIGRAM[m.up][1] + "）",
        down: (m.sum4 % 8 || 8) + " → " + TRIGRAM[m.down][0] + "（" + TRIGRAM[m.down][1] + "）",
        dong: m.sum4 + " ÷ 6 余 " + (m.sum4 % 6 || 6) + " → 第 " + m.dong + " 爻"
      },
      tags: tagsOf(m.up, m.down),
      yao: yaoHint(m),
      profile: profileOf(m),
      lucky: luckyOf(wx),
      note: noteOf(ty, sub),
      tiLabel: ty.tiName + " · " + profileOf(m).tiXiang,
      yongLabel: ty.yongName + " · " + profileOf(m).yongXiang
    };

    /* 真实数据：实时 MCP 优先，取不到退回内置快照 */
    var real = (LIVE_REAL && LIVE_REAL.ok) ? LIVE_REAL
      : (MCD_REAL && MCD_REAL.ok ? MCD_REAL : null);
    if (real) {
      var wish = yj.order || orderOf(wx, ty.rel, sub, now) || "巨无霸";
      var keys = wish.split(/[配和或/、]/).filter(function (k) { return k.length >= 2; });
      var cp = null;
      for (var ki = 0; ki < keys.length && !cp; ki++) {
        for (var ci = 0; ci < real.coupons.length; ci++) {
          if (real.coupons[ci].title.indexOf(keys[ki]) >= 0) { cp = real.coupons[ci]; break; }
        }
      }
      var ss = (real.stores || []).slice().sort(function (a, b) {
        return (a.distance == null ? 1e9 : a.distance) - (b.distance == null ? 1e9 : b.distance);
      });
      var st = ss.length ? ss[0] : null;
      var camp = null;
      for (var j2 = 0; j2 < real.campaigns.length; j2++) {
        if ((real.campaigns[j2].tag || "").indexOf("今日") >= 0) { camp = real.campaigns[j2]; break; }
      }
      if (!camp && real.campaigns.length) camp = real.campaigns[0];

      vm.real = {
        fetchedAt: (real.fetched_at || "").slice(5, 16),
        live: !!LIVE_REAL && LIVE_REAL.ok,
        coupon: cp ? cp.title : "",
        couponStatus: cp ? cp.status : "",
        store: st ? {
          name: (st.name || "").replace("麦当劳", "").replace("餐厅", ""),
          dist: st.distance,
          distText: st.distance < 1000 ? st.distance + "\u00A0米" : (st.distance / 1000).toFixed(1) + "\u00A0公里",
          open: st.open, close: st.close, address: st.address,
          openNow: st.open_now, reservation: st.reservation
        } : null,
        stores: ss.slice(1, 6).map(function (x) {
          return {
            name: (x.name || "").replace("麦当劳", ""),
            address: x.address,
            dist: x.distance < 1000 ? x.distance + "m" : (x.distance / 1000).toFixed(1) + "km"
          };
        }),
        coupons: real.coupons,
        campaigns: real.campaigns,
        points: real.points || null,
        pointsMasked: !real.points || (real.points.available == null && real.points.accumulative == null),
        campTitle: camp ? camp.title : ""
      };
      if (st) {
        vm.yi = ["去 " + vm.real.store.distText + " 那家，走过去不费劲"].concat(vm.yi.slice(0, 3));
      }
      if (cp) vm.yi = [vm.yi[0], "领「" + cp.title + "」，今天有便宜占"].concat(vm.yi.slice(2, 4));
    }

    var patch = { vm: vm, wxEl: wx, wxDesc: pair[1], real: real };
    if (withRitual) patch.asked = true;
    this.setData(patch);
  }
});
