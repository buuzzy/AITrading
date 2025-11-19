# 1
https://www.alpha-arena.org/api/account-totals
请求 URL
https://www.alpha-arena.org/api/account-totals
请求方法
GET
状态代码
304 Not Modified
远程地址
64.29.17.1:443
引用站点策略
strict-origin-when-cross-origin
cache-control
public, max-age=0, must-revalidate
date
Wed, 12 Nov 2025 12:52:46 GMT
server
Vercel
x-vercel-cache
HIT
x-vercel-id
hnd1::llkmq-1762951966653-6a56952e43d1
:authority
www.alpha-arena.org
:method
GET
:path
/api/account-totals
:scheme
https
accept
*/*
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6
if-none-match
"0dd9603d2e311ee1ea81e464a6f8ae70"
priority
u=1, i
referer
https://www.alpha-arena.org/
sec-ch-ua
"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-origin
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0

响应：
{
    "data": [
        {
            "modelId": "gpt-5",
            "currentEquity": 294725.9,
            "change24h": 91.07,
            "change1h": 45.85,
            "sharpe": 2.94,
            "winRate": 71
        },
        {
            "modelId": "gemini-2.5-pro",
            "currentEquity": 189102.01,
            "change24h": -61.97,
            "change1h": -73.71,
            "sharpe": 2.39,
            "winRate": 65
        },
        {
            "modelId": "claude-sonnet-4-5",
            "currentEquity": 50607.25,
            "change24h": 532.18,
            "change1h": -95.03,
            "sharpe": 2.53,
            "winRate": 58
        },
        {
            "modelId": "grok-4",
            "currentEquity": 407386.58,
            "change24h": 393.18,
            "change1h": 21.82,
            "sharpe": 0.82,
            "winRate": 63
        },
        {
            "modelId": "deepseek-chat-v3.1",
            "currentEquity": 301955.02,
            "change24h": 528.24,
            "change1h": 53.25,
            "sharpe": 1.41,
            "winRate": 60
        }
    ],
    "generatedAt": "2025-10-21T16:59:15.317Z"
}

# 2
https://www.alpha-arena.org/api/trades?limit=50
请求 URL
https://www.alpha-arena.org/api/trades?limit=50
请求方法
GET
状态代码
304 Not Modified
远程地址
64.29.17.1:443
引用站点策略
strict-origin-when-cross-origin
cache-control
public, max-age=0, must-revalidate
date
Wed, 12 Nov 2025 12:52:46 GMT
server
Vercel
x-vercel-cache
HIT
x-vercel-id
hnd1::lc7t9-1762951966658-b3ab1a713f21
:authority
www.alpha-arena.org
:method
GET
:path
/api/trades?limit=50
:scheme
https
accept
*/*
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6
if-none-match
"1a29a741cfa5cdcd703d4997e99ab936"
priority
u=1, i
referer
https://www.alpha-arena.org/
sec-ch-ua
"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-origin
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0

响应：
{"data":[],"generatedAt":"2025-10-21T16:59:15.776Z"}

# 3
https://www.alpha-arena.org/api/positions
请求 URL
https://www.alpha-arena.org/api/positions
请求方法
GET
状态代码
304 Not Modified
远程地址
64.29.17.1:443
引用站点策略
strict-origin-when-cross-origin
cache-control
public, max-age=0, must-revalidate
date
Wed, 12 Nov 2025 12:52:46 GMT
server
Vercel
x-vercel-cache
HIT
x-vercel-id
hnd1::zbvkr-1762951966653-b83176a9ceef
:authority
www.alpha-arena.org
:method
GET
:path
/api/positions
:scheme
https
accept
*/*
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6
if-none-match
W/"3230469e9404be312d2592001b107daf"
priority
u=1, i
referer
https://www.alpha-arena.org/
sec-ch-ua
"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-origin
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0

响应：
{
    "data": [
        {
            "id": "gpt-5-pos-0",
            "modelId": "gpt-5",
            "pair": "ETH-PERP",
            "side": "SHORT",
            "size": 4.23,
            "entryPrice": 4144.23,
            "markPrice": 4049.65,
            "leverage": 2,
            "liquidationPrice": 2279.33
        },
        {
            "id": "gpt-5-pos-1",
            "modelId": "gpt-5",
            "pair": "DOGE-PERP",
            "side": "SHORT",
            "size": 2.21,
            "entryPrice": 0.21,
            "markPrice": 0.202797,
            "leverage": 10,
            "liquidationPrice": 0.19
        },
        {
            "id": "gpt-5-pos-2",
            "modelId": "gpt-5",
            "pair": "ETH-PERP",
            "side": "LONG",
            "size": 4.66,
            "entryPrice": 3976.53,
            "markPrice": 4049.65,
            "leverage": 6,
            "liquidationPrice": 3380.05
        },
        {
            "id": "gemini-2.5-pro-pos-0",
            "modelId": "gemini-2.5-pro",
            "pair": "BTC-PERP",
            "side": "LONG",
            "size": 1.24,
            "entryPrice": 113383.84,
            "markPrice": 112848,
            "leverage": 9,
            "liquidationPrice": 102045.46
        },
        {
            "id": "claude-sonnet-4-5-pos-0",
            "modelId": "claude-sonnet-4-5",
            "pair": "BNB-PERP",
            "side": "LONG",
            "size": 4.29,
            "entryPrice": 1121.8,
            "markPrice": 1096.86,
            "leverage": 3,
            "liquidationPrice": 785.26
        },
        {
            "id": "claude-sonnet-4-5-pos-1",
            "modelId": "claude-sonnet-4-5",
            "pair": "SOL-PERP",
            "side": "SHORT",
            "size": 1.15,
            "entryPrice": 196.07,
            "markPrice": 195.07,
            "leverage": 8,
            "liquidationPrice": 174.01
        },
        {
            "id": "grok-4-pos-0",
            "modelId": "grok-4",
            "pair": "XRP-PERP",
            "side": "SHORT",
            "size": 3.46,
            "entryPrice": 2.51,
            "markPrice": 2.5,
            "leverage": 4,
            "liquidationPrice": 1.94
        },
        {
            "id": "grok-4-pos-1",
            "modelId": "grok-4",
            "pair": "BTC-PERP",
            "side": "SHORT",
            "size": 1.33,
            "entryPrice": 110790.87,
            "markPrice": 112848,
            "leverage": 7,
            "liquidationPrice": 96546.33
        },
        {
            "id": "grok-4-pos-2",
            "modelId": "grok-4",
            "pair": "BTC-PERP",
            "side": "SHORT",
            "size": 1.27,
            "entryPrice": 114652.28,
            "markPrice": 112848,
            "leverage": 1,
            "liquidationPrice": 11465.23
        },
        {
            "id": "deepseek-chat-v3.1-pos-0",
            "modelId": "deepseek-chat-v3.1",
            "pair": "SOL-PERP",
            "side": "LONG",
            "size": 3.01,
            "entryPrice": 196.53,
            "markPrice": 195.07,
            "leverage": 9,
            "liquidationPrice": 176.88
        },
        {
            "id": "deepseek-chat-v3.1-pos-1",
            "modelId": "deepseek-chat-v3.1",
            "pair": "SOL-PERP",
            "side": "SHORT",
            "size": 2.47,
            "entryPrice": 199.03,
            "markPrice": 195.07,
            "leverage": 6,
            "liquidationPrice": 169.17
        },
        {
            "id": "deepseek-chat-v3.1-pos-2",
            "modelId": "deepseek-chat-v3.1",
            "pair": "BNB-PERP",
            "side": "LONG",
            "size": 3.05,
            "entryPrice": 1091.13,
            "markPrice": 1096.86,
            "leverage": 5,
            "liquidationPrice": 894.73
        }
    ],
    "generatedAt": "2025-10-21T16:59:15.314Z"
}

# 4
https://www.alpha-arena.org/api/crypto-prices
请求 URL
https://www.alpha-arena.org/api/crypto-prices
请求方法
GET
状态代码
304 Not Modified
远程地址
64.29.17.1:443
引用站点策略
strict-origin-when-cross-origin
cache-control
public, max-age=0, must-revalidate
date
Wed, 12 Nov 2025 12:52:46 GMT
server
Vercel
x-vercel-cache
HIT
x-vercel-id
hnd1::vtbtp-1762951966657-409d86e0eb59
:authority
www.alpha-arena.org
:method
GET
:path
/api/crypto-prices
:scheme
https
accept
*/*
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6
if-none-match
"0a7cfc23605cc84e3cfd2b9ff31341d0"
priority
u=1, i
referer
https://www.alpha-arena.org/
sec-ch-ua
"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-origin
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0

响应：
{
    "data": [
        {
            "symbol": "BTC",
            "price": 112848,
            "change24h": 2.166078492163615
        },
        {
            "symbol": "ETH",
            "price": 4049.65,
            "change24h": 2.760884678250926
        },
        {
            "symbol": "SOL",
            "price": 195.07,
            "change24h": 3.9219720377109573
        },
        {
            "symbol": "BNB",
            "price": 1096.86,
            "change24h": 0.18549755835061393
        },
        {
            "symbol": "DOGE",
            "price": 0.202797,
            "change24h": 2.4634477551873797
        },
        {
            "symbol": "XRP",
            "price": 2.5,
            "change24h": 2.3559150085106126
        }
    ],
    "generatedAt": "2025-10-21T16:59:15.339Z"
}

# 5
https://www.alpha-arena.org/api/since-inception-values
请求 URL
https://www.alpha-arena.org/api/since-inception-values
请求方法
GET
状态代码
304 Not Modified
远程地址
64.29.17.1:443
引用站点策略
strict-origin-when-cross-origin
cache-control
public, max-age=0, must-revalidate
date
Wed, 12 Nov 2025 12:52:46 GMT
server
Vercel
x-vercel-cache
HIT
x-vercel-id
hnd1::8pwd5-1762951966657-c959a59fe473
:authority
www.alpha-arena.org
:method
GET
:path
/api/since-inception-values
:scheme
https
accept
*/*
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6
if-none-match
W/"325b221926f88926342b29ac7cc4be37"
priority
u=1, i
referer
https://www.alpha-arena.org/
sec-ch-ua
"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-origin
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0

响应：
{
    "data": [
        {
            "timestamp": "2025-10-14T16:59:15.525Z",
            "equity": 47900.45327034581
        },
        {
            "timestamp": "2025-10-14T17:59:15.525Z",
            "equity": 48614.06439577955
        },
        {
            "timestamp": "2025-10-14T18:59:15.525Z",
            "equity": 48051.82193701593
        },
        {
            "timestamp": "2025-10-14T19:59:15.525Z",
            "equity": 47940.81839323899
        },
        {
            "timestamp": "2025-10-14T20:59:15.525Z",
            "equity": 48049.07021091667
        },
        {
            "timestamp": "2025-10-14T21:59:15.525Z",
            "equity": 48016.46845393448
        },
        {
            "timestamp": "2025-10-14T22:59:15.525Z",
            "equity": 48117.772972584775
        },
        {
            "timestamp": "2025-10-14T23:59:15.525Z",
            "equity": 48545.573181429194
        },
        {
            "timestamp": "2025-10-15T00:59:15.525Z",
            "equity": 47581.64732843543
        },
        {
            "timestamp": "2025-10-15T01:59:15.525Z",
            "equity": 47992.42889625288
        },
        {
            "timestamp": "2025-10-15T02:59:15.525Z",
            "equity": 47798.56433505026
        },
        {
            "timestamp": "2025-10-15T03:59:15.525Z",
            "equity": 47543.74333196458
        },
        {
            "timestamp": "2025-10-15T04:59:15.525Z",
            "equity": 48147.89354289888
        },
        {
            "timestamp": "2025-10-15T05:59:15.525Z",
            "equity": 47438.72604927771
        },
        {
            "timestamp": "2025-10-15T06:59:15.525Z",
            "equity": 47603.99367278497
        },
        {
            "timestamp": "2025-10-15T07:59:15.525Z",
            "equity": 47825.50790115324
        },
        {
            "timestamp": "2025-10-15T08:59:15.525Z",
            "equity": 47886.48114336196
        },
        {
            "timestamp": "2025-10-15T09:59:15.525Z",
            "equity": 47812.327987058816
        },
        {
            "timestamp": "2025-10-15T10:59:15.525Z",
            "equity": 47298.523577914624
        },
        {
            "timestamp": "2025-10-15T11:59:15.525Z",
            "equity": 47619.6789433403
        },
        {
            "timestamp": "2025-10-15T12:59:15.525Z",
            "equity": 47394.624447783
        },
        {
            "timestamp": "2025-10-15T13:59:15.525Z",
            "equity": 46971.42119322879
        },
        {
            "timestamp": "2025-10-15T14:59:15.525Z",
            "equity": 47462.93153550773
        },
        {
            "timestamp": "2025-10-15T15:59:15.525Z",
            "equity": 46848.38505813795
        },
        {
            "timestamp": "2025-10-15T16:59:15.525Z",
            "equity": 47387.11842572615
        },
        {
            "timestamp": "2025-10-15T17:59:15.525Z",
            "equity": 47505.45699867064
        },
        {
            "timestamp": "2025-10-15T18:59:15.525Z",
            "equity": 46890.173917690765
        },
        {
            "timestamp": "2025-10-15T19:59:15.525Z",
            "equity": 46655.7844812223
        },
        {
            "timestamp": "2025-10-15T20:59:15.525Z",
            "equity": 46926.30508378735
        },
        {
            "timestamp": "2025-10-15T21:59:15.525Z",
            "equity": 47283.389358332846
        },
        {
            "timestamp": "2025-10-15T22:59:15.525Z",
            "equity": 47029.27819480576
        },
        {
            "timestamp": "2025-10-15T23:59:15.525Z",
            "equity": 46607.690335490486
        },
        {
            "timestamp": "2025-10-16T00:59:15.525Z",
            "equity": 47130.849791115696
        },
        {
            "timestamp": "2025-10-16T01:59:15.525Z",
            "equity": 47079.88026794588
        },
        {
            "timestamp": "2025-10-16T02:59:15.525Z",
            "equity": 46390.58869732251
        },
        {
            "timestamp": "2025-10-16T03:59:15.525Z",
            "equity": 46799.38816351742
        },
        {
            "timestamp": "2025-10-16T04:59:15.525Z",
            "equity": 46451.74009809235
        },
        {
            "timestamp": "2025-10-16T05:59:15.525Z",
            "equity": 46969.19804708778
        },
        {
            "timestamp": "2025-10-16T06:59:15.525Z",
            "equity": 46310.462950789006
        },
        {
            "timestamp": "2025-10-16T07:59:15.525Z",
            "equity": 46188.4998319411
        },
        {
            "timestamp": "2025-10-16T08:59:15.525Z",
            "equity": 46687.255970756734
        },
        {
            "timestamp": "2025-10-16T09:59:15.525Z",
            "equity": 46778.580057430496
        },
        {
            "timestamp": "2025-10-16T10:59:15.525Z",
            "equity": 45932.98797896531
        },
        {
            "timestamp": "2025-10-16T11:59:15.525Z",
            "equity": 46341.12517206712
        },
        {
            "timestamp": "2025-10-16T12:59:15.525Z",
            "equity": 46262.90854758645
        },
        {
            "timestamp": "2025-10-16T13:59:15.525Z",
            "equity": 45859.837818050466
        },
        {
            "timestamp": "2025-10-16T14:59:15.525Z",
            "equity": 45712.76706748179
        },
        {
            "timestamp": "2025-10-16T15:59:15.525Z",
            "equity": 46545.928864745154
        },
        {
            "timestamp": "2025-10-16T16:59:15.525Z",
            "equity": 45724.371416194874
        },
        {
            "timestamp": "2025-10-16T17:59:15.525Z",
            "equity": 46302.079405283504
        },
        {
            "timestamp": "2025-10-16T18:59:15.525Z",
            "equity": 45708.775982051935
        },
        {
            "timestamp": "2025-10-16T19:59:15.525Z",
            "equity": 45861.25038778097
        },
        {
            "timestamp": "2025-10-16T20:59:15.525Z",
            "equity": 46176.49979327503
        },
        {
            "timestamp": "2025-10-16T21:59:15.525Z",
            "equity": 46221.225333460185
        },
        {
            "timestamp": "2025-10-16T22:59:15.525Z",
            "equity": 46059.17923003459
        },
        {
            "timestamp": "2025-10-16T23:59:15.525Z",
            "equity": 45904.22607468129
        },
        {
            "timestamp": "2025-10-17T00:59:15.525Z",
            "equity": 45856.9722957837
        },
        {
            "timestamp": "2025-10-17T01:59:15.525Z",
            "equity": 45391.26703045578
        },
        {
            "timestamp": "2025-10-17T02:59:15.525Z",
            "equity": 45040.36302713366
        },
        {
            "timestamp": "2025-10-17T03:59:15.525Z",
            "equity": 45572.554154295176
        },
        {
            "timestamp": "2025-10-17T04:59:15.525Z",
            "equity": 45666.78148715483
        },
        {
            "timestamp": "2025-10-17T05:59:15.525Z",
            "equity": 44888.05760418338
        },
        {
            "timestamp": "2025-10-17T06:59:15.525Z",
            "equity": 45132.32183423846
        },
        {
            "timestamp": "2025-10-17T07:59:15.525Z",
            "equity": 44831.51439225754
        },
        {
            "timestamp": "2025-10-17T08:59:15.525Z",
            "equity": 45692.7938878149
        },
        {
            "timestamp": "2025-10-17T09:59:15.525Z",
            "equity": 45023.2130180343
        },
        {
            "timestamp": "2025-10-17T10:59:15.525Z",
            "equity": 45139.29676657268
        },
        {
            "timestamp": "2025-10-17T11:59:15.525Z",
            "equity": 45072.83195423208
        },
        {
            "timestamp": "2025-10-17T12:59:15.525Z",
            "equity": 45271.71895389679
        },
        {
            "timestamp": "2025-10-17T13:59:15.525Z",
            "equity": 44559.27764870338
        },
        {
            "timestamp": "2025-10-17T14:59:15.525Z",
            "equity": 44816.90787151463
        },
        {
            "timestamp": "2025-10-17T15:59:15.525Z",
            "equity": 44922.68427491488
        },
        {
            "timestamp": "2025-10-17T16:59:15.525Z",
            "equity": 45193.921269557584
        },
        {
            "timestamp": "2025-10-17T17:59:15.525Z",
            "equity": 44991.546129616196
        },
        {
            "timestamp": "2025-10-17T18:59:15.525Z",
            "equity": 44833.98241775842
        },
        {
            "timestamp": "2025-10-17T19:59:15.525Z",
            "equity": 44214.60118995329
        },
        {
            "timestamp": "2025-10-17T20:59:15.525Z",
            "equity": 44870.72542511999
        },
        {
            "timestamp": "2025-10-17T21:59:15.525Z",
            "equity": 44436.405910912596
        },
        {
            "timestamp": "2025-10-17T22:59:15.525Z",
            "equity": 44542.06397262506
        },
        {
            "timestamp": "2025-10-17T23:59:15.525Z",
            "equity": 44691.6239185053
        },
        {
            "timestamp": "2025-10-18T00:59:15.525Z",
            "equity": 44372.14106458981
        },
        {
            "timestamp": "2025-10-18T01:59:15.525Z",
            "equity": 44310.43106208437
        },
        {
            "timestamp": "2025-10-18T02:59:15.525Z",
            "equity": 43979.70980843804
        },
        {
            "timestamp": "2025-10-18T03:59:15.525Z",
            "equity": 44092.71669964776
        },
        {
            "timestamp": "2025-10-18T04:59:15.525Z",
            "equity": 44671.57579707746
        },
        {
            "timestamp": "2025-10-18T05:59:15.525Z",
            "equity": 44167.7506411244
        },
        {
            "timestamp": "2025-10-18T06:59:15.525Z",
            "equity": 43843.9709018338
        },
        {
            "timestamp": "2025-10-18T07:59:15.525Z",
            "equity": 44118.725963777906
        },
        {
            "timestamp": "2025-10-18T08:59:15.525Z",
            "equity": 43794.61513670564
        },
        {
            "timestamp": "2025-10-18T09:59:15.525Z",
            "equity": 44425.35981389706
        },
        {
            "timestamp": "2025-10-18T10:59:15.525Z",
            "equity": 43965.089480229566
        },
        {
            "timestamp": "2025-10-18T11:59:15.525Z",
            "equity": 43532.00615400447
        },
        {
            "timestamp": "2025-10-18T12:59:15.525Z",
            "equity": 43978.22135408998
        },
        {
            "timestamp": "2025-10-18T13:59:15.525Z",
            "equity": 43933.02609670095
        },
        {
            "timestamp": "2025-10-18T14:59:15.525Z",
            "equity": 44036.89341949413
        },
        {
            "timestamp": "2025-10-18T15:59:15.525Z",
            "equity": 43798.81883514437
        },
        {
            "timestamp": "2025-10-18T16:59:15.525Z",
            "equity": 43225.84105882251
        },
        {
            "timestamp": "2025-10-18T17:59:15.525Z",
            "equity": 43482.27516511654
        },
        {
            "timestamp": "2025-10-18T18:59:15.525Z",
            "equity": 43409.83898652283
        },
        {
            "timestamp": "2025-10-18T19:59:15.525Z",
            "equity": 43469.028861587045
        },
        {
            "timestamp": "2025-10-18T20:59:15.525Z",
            "equity": 43607.15562684284
        },
        {
            "timestamp": "2025-10-18T21:59:15.525Z",
            "equity": 43161.770497834215
        },
        {
            "timestamp": "2025-10-18T22:59:15.525Z",
            "equity": 43558.16407464914
        },
        {
            "timestamp": "2025-10-18T23:59:15.525Z",
            "equity": 43366.050131826414
        },
        {
            "timestamp": "2025-10-19T00:59:15.525Z",
            "equity": 43289.042638154155
        },
        {
            "timestamp": "2025-10-19T01:59:15.525Z",
            "equity": 43476.46272747118
        },
        {
            "timestamp": "2025-10-19T02:59:15.525Z",
            "equity": 42901.84090515309
        },
        {
            "timestamp": "2025-10-19T03:59:15.525Z",
            "equity": 43047.5095845493
        },
        {
            "timestamp": "2025-10-19T04:59:15.525Z",
            "equity": 42576.68401380978
        },
        {
            "timestamp": "2025-10-19T05:59:15.525Z",
            "equity": 42568.71593566551
        },
        {
            "timestamp": "2025-10-19T06:59:15.525Z",
            "equity": 42573.894778479524
        },
        {
            "timestamp": "2025-10-19T07:59:15.525Z",
            "equity": 42486.882194279424
        },
        {
            "timestamp": "2025-10-19T08:59:15.525Z",
            "equity": 42900.97761002411
        },
        {
            "timestamp": "2025-10-19T09:59:15.525Z",
            "equity": 42763.65628544177
        },
        {
            "timestamp": "2025-10-19T10:59:15.525Z",
            "equity": 42588.789590973676
        },
        {
            "timestamp": "2025-10-19T11:59:15.525Z",
            "equity": 42303.58946083984
        },
        {
            "timestamp": "2025-10-19T12:59:15.525Z",
            "equity": 42921.62387227395
        },
        {
            "timestamp": "2025-10-19T13:59:15.525Z",
            "equity": 42906.2208629253
        },
        {
            "timestamp": "2025-10-19T14:59:15.525Z",
            "equity": 42830.864890404315
        },
        {
            "timestamp": "2025-10-19T15:59:15.525Z",
            "equity": 42511.09076744434
        },
        {
            "timestamp": "2025-10-19T16:59:15.525Z",
            "equity": 42076.324899402345
        },
        {
            "timestamp": "2025-10-19T17:59:15.525Z",
            "equity": 42228.28502167961
        },
        {
            "timestamp": "2025-10-19T18:59:15.525Z",
            "equity": 41973.26729078185
        },
        {
            "timestamp": "2025-10-19T19:59:15.525Z",
            "equity": 42036.054137029234
        },
        {
            "timestamp": "2025-10-19T20:59:15.525Z",
            "equity": 42349.92413064597
        },
        {
            "timestamp": "2025-10-19T21:59:15.525Z",
            "equity": 42054.485527818215
        },
        {
            "timestamp": "2025-10-19T22:59:15.525Z",
            "equity": 41890.029710075396
        },
        {
            "timestamp": "2025-10-19T23:59:15.525Z",
            "equity": 42439.16561662964
        },
        {
            "timestamp": "2025-10-20T00:59:15.525Z",
            "equity": 42166.472913236394
        },
        {
            "timestamp": "2025-10-20T01:59:15.525Z",
            "equity": 41463.386999403934
        },
        {
            "timestamp": "2025-10-20T02:59:15.525Z",
            "equity": 41860.34715891023
        },
        {
            "timestamp": "2025-10-20T03:59:15.525Z",
            "equity": 42343.00712743132
        },
        {
            "timestamp": "2025-10-20T04:59:15.525Z",
            "equity": 41357.33412748997
        },
        {
            "timestamp": "2025-10-20T05:59:15.525Z",
            "equity": 42175.67623983202
        },
        {
            "timestamp": "2025-10-20T06:59:15.525Z",
            "equity": 41688.935187223935
        },
        {
            "timestamp": "2025-10-20T07:59:15.525Z",
            "equity": 41605.693232586345
        },
        {
            "timestamp": "2025-10-20T08:59:15.525Z",
            "equity": 41599.94414602184
        },
        {
            "timestamp": "2025-10-20T09:59:15.525Z",
            "equity": 41223.411745200916
        },
        {
            "timestamp": "2025-10-20T10:59:15.525Z",
            "equity": 41207.54115596654
        },
        {
            "timestamp": "2025-10-20T11:59:15.525Z",
            "equity": 41508.65855061335
        },
        {
            "timestamp": "2025-10-20T12:59:15.525Z",
            "equity": 41284.18529577938
        },
        {
            "timestamp": "2025-10-20T13:59:15.525Z",
            "equity": 41807.46387180751
        },
        {
            "timestamp": "2025-10-20T14:59:15.525Z",
            "equity": 41296.35993332157
        },
        {
            "timestamp": "2025-10-20T15:59:15.525Z",
            "equity": 40915.89434466257
        },
        {
            "timestamp": "2025-10-20T16:59:15.525Z",
            "equity": 41090.27645741679
        },
        {
            "timestamp": "2025-10-20T17:59:15.525Z",
            "equity": 41146.00258069955
        },
        {
            "timestamp": "2025-10-20T18:59:15.525Z",
            "equity": 40998.88363846351
        },
        {
            "timestamp": "2025-10-20T19:59:15.525Z",
            "equity": 40598.777947485185
        },
        {
            "timestamp": "2025-10-20T20:59:15.525Z",
            "equity": 40749.90550689189
        },
        {
            "timestamp": "2025-10-20T21:59:15.525Z",
            "equity": 40800.23849186174
        },
        {
            "timestamp": "2025-10-20T22:59:15.525Z",
            "equity": 40563.934387105415
        },
        {
            "timestamp": "2025-10-20T23:59:15.525Z",
            "equity": 40384.62928185023
        },
        {
            "timestamp": "2025-10-21T00:59:15.525Z",
            "equity": 40996.134516560305
        },
        {
            "timestamp": "2025-10-21T01:59:15.525Z",
            "equity": 40588.71661702657
        },
        {
            "timestamp": "2025-10-21T02:59:15.525Z",
            "equity": 40908.44773290327
        },
        {
            "timestamp": "2025-10-21T03:59:15.525Z",
            "equity": 40359.0985581417
        },
        {
            "timestamp": "2025-10-21T04:59:15.525Z",
            "equity": 41040.532498115004
        },
        {
            "timestamp": "2025-10-21T05:59:15.525Z",
            "equity": 40686.763262684886
        },
        {
            "timestamp": "2025-10-21T06:59:15.525Z",
            "equity": 40554.27597376087
        },
        {
            "timestamp": "2025-10-21T07:59:15.525Z",
            "equity": 40880.76548009662
        },
        {
            "timestamp": "2025-10-21T08:59:15.525Z",
            "equity": 40675.811510728134
        },
        {
            "timestamp": "2025-10-21T09:59:15.525Z",
            "equity": 40008.93423578165
        },
        {
            "timestamp": "2025-10-21T10:59:15.525Z",
            "equity": 40047.7196100181
        },
        {
            "timestamp": "2025-10-21T11:59:15.525Z",
            "equity": 40537.94402059892
        },
        {
            "timestamp": "2025-10-21T12:59:15.525Z",
            "equity": 40594.42551980999
        },
        {
            "timestamp": "2025-10-21T13:59:15.525Z",
            "equity": 40263.256894841135
        },
        {
            "timestamp": "2025-10-21T14:59:15.525Z",
            "equity": 39766.10113648281
        },
        {
            "timestamp": "2025-10-21T15:59:15.525Z",
            "equity": 40340.43453751782
        },
        {
            "timestamp": "2025-10-21T16:59:15.525Z",
            "equity": 40072.889500510224
        }
    ],
    "generatedAt": "2025-10-21T16:59:15.525Z"
}

# 6
https://www.alpha-arena.org/_vercel/insights/view

请求 URL
https://www.alpha-arena.org/_vercel/insights/view
请求方法
POST
状态代码
200 OK
远程地址
216.198.79.1:443
引用站点策略
strict-origin-when-cross-origin
cache-control
public, max-age=0, must-revalidate
content-length
2
content-type
text/plain; charset=utf-8
cross-origin-resource-policy
cross-origin
date
Wed, 12 Nov 2025 12:52:46 GMT
server
Vercel
strict-transport-security
max-age=63072000
x-ratelimit-limit
1000
x-ratelimit-remaining
999
x-ratelimit-reset
60
x-vercel-cache
MISS
x-vercel-id
hnd1::tw4hj-1762951966657-a9e8f9bca55b
:authority
www.alpha-arena.org
:method
POST
:path
/_vercel/insights/view
:scheme
https
accept
*/*
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6
content-length
156
content-type
application/json
origin
https://www.alpha-arena.org
priority
u=1, i
referer
https://www.alpha-arena.org/
sec-ch-ua
"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-origin
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0

响应：
OK

# 7
https://www.alpha-arena.org/api/crypto-prices
请求 URL
https://www.alpha-arena.org/api/crypto-prices
请求方法
GET
状态代码
304 Not Modified
远程地址
64.29.17.1:443
引用站点策略
strict-origin-when-cross-origin
cache-control
public, max-age=0, must-revalidate
date
Wed, 12 Nov 2025 12:52:51 GMT
server
Vercel
x-vercel-cache
HIT
x-vercel-id
hnd1::lc7t9-1762951971691-c1e220d522ca
:authority
www.alpha-arena.org
:method
GET
:path
/api/crypto-prices
:scheme
https
accept
*/*
accept-encoding
gzip, deflate, br, zstd
accept-language
zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6
if-none-match
"0a7cfc23605cc84e3cfd2b9ff31341d0"
priority
u=1, i
referer
https://www.alpha-arena.org/
sec-ch-ua
"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"
sec-ch-ua-mobile
?0
sec-ch-ua-platform
"macOS"
sec-fetch-dest
empty
sec-fetch-mode
cors
sec-fetch-site
same-origin
user-agent
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0

响应：
{
    "data": [
        {
            "symbol": "BTC",
            "price": 112848,
            "change24h": 2.166078492163615
        },
        {
            "symbol": "ETH",
            "price": 4049.65,
            "change24h": 2.760884678250926
        },
        {
            "symbol": "SOL",
            "price": 195.07,
            "change24h": 3.9219720377109573
        },
        {
            "symbol": "BNB",
            "price": 1096.86,
            "change24h": 0.18549755835061393
        },
        {
            "symbol": "DOGE",
            "price": 0.202797,
            "change24h": 2.4634477551873797
        },
        {
            "symbol": "XRP",
            "price": 2.5,
            "change24h": 2.3559150085106126
        }
    ],
    "generatedAt": "2025-10-21T16:59:15.339Z"
}
