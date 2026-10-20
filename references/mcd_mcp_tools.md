# 麦当劳 MCP 实测工具清单（2026-10-19 实测）

- 端点：`https://mcp.mcd.cn`（根域名即端点，不带 `/mcp`，`/mcp` 返回 404）
- 协议：MCP `2024-11-05`，server `mcd-mcp v1.0.0`，`type: streamablehttp`
- 鉴权：`Authorization: Bearer <Token>`
- 总工具数：**35**

## 一、本项目选用（只读查询类，决策辅助定位）

| 工具名 | 说明 | 命理映射用途 |
|---|---|---|
| `query-my-account` | 积分账户详情 | 财运 / 财帛宫 |
| `campaign-calendar` | 当月营销活动日历 | 吉日 / 运势时间维度 |
| `available-coupons` | 可领取的麦麦省优惠券 | 宜领券 / 财运指引 |
| `query-store-coupons` | 指定门店+订单类型可用券 | 宜领券（按门店） |
| `query-my-coupons` | 卡包已有券资产 | 财运现状 |
| `query-nearby-stores` | 到店可点餐门店 | 今日至尊福地 |
| `list-nutrition-foods` | 餐品营养成分/热量 | 宜吃 / 忌吃依据 |
| `now-time-info` | 当前服务器时间 | 黄道吉时 |
| `query-lottery-info` | 积分抽奖活动信息 | 宜抽奖（点缀） |
| `query-my-prizes` | 抽奖获得奖品 | 宜抽奖（点缀） |

## 二、坚决不碰（写操作 / 下单风险）

`create-order`、`party-order-create`、`mall-create-order`、`cancel-order`、
`draw-lottery`、`auto-bind-coupons`、`delivery-create-address`、`calculate-price`、
`delivery-query-addresses`、`delivery-query-stores`、`query-meal-assistance`、
`query-meals`、`query-meal-detail`、`query-order`、`order-list`、
`mall-product-detail`、`mall-order-list`、`mall-order-detail`、`mall-points-products`、
`query-survey-coupon`、`query-promotions`、`query-party-city`、`query-party-store`、
`query-party-store-date`、`query-party-store-session`。

> 本项目定位「决策辅助 + 趣味命理」，只做只读查询，绝不触发任何下单 / 领券 / 抽奖写操作。

## 三、实测坑（来自 2026-10-19 探测）

- 端点必须是 `https://mcp.mcd.cn`，不是 `https://mcp.mcd.cn/mcp`（后者 404）。
- `initialize` 响应不返回 `Mcp-Session-Id`（stateless 风格），后续 `tools/list` 不带 session 也能 200。
- 限流：600 次/分钟，超 429；自测控制频率。
- `now-time-info` 返回服务器时间，命理「吉时」以它为准，不本地取时。
