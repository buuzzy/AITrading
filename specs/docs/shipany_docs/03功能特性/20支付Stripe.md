ShipAny 支持使用 Stripe 进行支付，可用于产品付款、会员订阅、购买积分等场景。

Stripe 设置
注册一个 Stripe 账户
在 Stripe 后台 创建店铺
选择店铺，设置店铺经营信息
在 Stripe 开发者中心 创建 Standard keys，包括 Publishable key 和 Secret key
ShipAny 配置
在 ShipAny 项目配置文件中，填写 Stripe 相关的配置信息。

开发环境配置文件 .env.development
生产环境配置文件 .env.production / wrangler.toml
NEXT_PUBLIC_WEB_URL = "http://localhost:3000"
NEXT_PUBLIC_PAY_SUCCESS_URL = "/my-orders"
NEXT_PUBLIC_PAY_FAIL_URL = "/pricing"
NEXT_PUBLIC_PAY_CANCEL_URL = "/pricing"
PAY_PROVIDER = "stripe"
STRIPE_PUBLIC_KEY = "pk_test_xxx"
STRIPE_PRIVATE_KEY = "sk_test_xxx"
STRIPE_WEBHOOK_SECRET = "whsec_cexxx"

NEXT_PUBLIC_PAY_SUCCESS_URL 支付成功后跳转的页面路径
NEXT_PUBLIC_PAY_FAIL_URL 支付失败后跳转的页面路径
NEXT_PUBLIC_PAY_CANCEL_URL 支付取消后跳转的页面路径
页面路径可以填相对路径，也可以填绝对路径。如果填的是相对路径，跳转时会自动拼接 NEXT_PUBLIC_WEB_URL 配置的网站地址，并带上多语言参数。

比如按照以上配置，在中文页面支付成功后的跳转路径是：http://localhost:3000/zh/my-orders

PAY_PROVIDER 支付提供商，默认是 stripe
STRIPE_PUBLIC_KEY Stripe Publishable key
STRIPE_PRIVATE_KEY Stripe Secret key
STRIPE_WEBHOOK_SECRET Stripe 支付通知验证密钥，在 Stripe 后台 配置 Webhook 地址 后，进入 Webhook 地址的管理页面，复制 Signing secret。
价格表支付
ShipAny 模板内置了一个价格表和对应的支付逻辑，你可以根据自己的需求，简单修改即可快速实现支付功能。

配置价格表内容
ShipAny 模板内置的价格表配置文件位于：src/i18n/pages/pricing 目录下，支持多语言，默认包含 en.json 和 zh.json 两个价格表配置文件。

比如英文价格表的默认配置为：

{
  "pricing": {
    "name": "pricing",
    "label": "Pricing",
    "title": "Pricing",
    "description": "Get all features of ShipAny, Ship your AI SaaS startups fast.",
    "groups": [],
    "items": [
      {
        "title": "Starter",
        "description": "Get started with your first SaaS startup.",
        "features_title": "Includes",
        "features": [
          "100 credits, valid for 1 month",
          "NextJS boilerplate",
          "SEO-friendly structure",
          "Payment with Stripe",
          "Data storage with Supabase",
          "Google Oauth & One-Tap Login",
          "i18n support"
        ],
        "interval": "one-time",
        "amount": 9900,
        "cn_amount": 69900,
        "currency": "USD",
        "price": "$99",
        "original_price": "$199",
        "unit": "USD",
        "is_featured": false,
        "tip": "Pay once. Build unlimited projects!",
        "button": {
          "title": "Get ShipAny",
          "url": "/#pricing",
          "icon": "RiFlashlightFill"
        },
        "product_id": "starter",
        "product_name": "ShipAny Boilerplate Starter",
        "credits": 100,
        "valid_months": 1
      },
      {
        "title": "Standard",
        "description": "Ship Fast with your SaaS Startups.",
        "label": "Popular",
        "features_title": "Everything in Starter, plus",
        "features": [
          "200 credits, valid for 3 month",
          "Deploy with Vercel or Cloudflare",
          "Generation of Privacy & Terms",
          "Google Analytics Integration",
          "Google Search Console Integration",
          "Discord community",
          "Technical support for your first ship",
          "Lifetime updates"
        ],
        "interval": "one-time",
        "amount": 19900,
        "cn_amount": 139900,
        "currency": "USD",
        "price": "$199",
        "original_price": "$299",
        "unit": "USD",
        "is_featured": true,
        "tip": "Pay once. Build unlimited projects!",
        "button": {
          "title": "Get ShipAny",
          "url": "/#pricing",
          "icon": "RiFlashlightFill"
        },
        "product_id": "standard",
        "product_name": "ShipAny Boilerplate Standard",
        "credits": 200,
        "valid_months": 3
      },
      {
        "title": "Premium",
        "description": "Ship Any AI SaaS Startups.",
        "features_title": "Everything in Standard, plus",
        "features": [
          "300 credits, valid for 1 year",
          "Business Functions with AI",
          "User Center",
          "Credits System",
          "API Sales for your SaaS",
          "Admin System",
          "Priority Technical Support"
        ],
        "interval": "one-time",
        "amount": 29900,
        "cn_amount": 199900,
        "currency": "USD",
        "price": "$299",
        "original_price": "$399",
        "unit": "USD",
        "is_featured": false,
        "tip": "Pay once. Build unlimited projects!",
        "button": {
          "title": "Get ShipAny",
          "url": "/#pricing",
          "icon": "RiFlashlightFill"
        },
        "product_id": "premium",
        "product_name": "ShipAny Boilerplate Premium",
        "credits": 300,
        "valid_months": 12
      }
    ]
  }
}

默认的价格表预览为:

price-table

你可以根据自己的需求，修改价格表配置文件中的内容。

修改价格表组件
默认的价格表组件位于：src/components/blocks/pricing/index.tsx

你可以根据自己的需求，修改价格表的展示形式。

修改价格表下单逻辑
默认的价格表下单逻辑位于：src/app/api/checkout/route.ts

你可以根据自己的需求，修改价格表的下单逻辑。

修改支付回调逻辑
在价格表下单逻辑中，默认配置的支付回调地址是：/api/pay/callback/stripe

用户支付后，会在浏览器跳转到这个地址，并带上包含支付信息的参数。

默认的支付回调处理逻辑位于：src/app/api/pay/callback/stripe/route.ts

你可以根据自己的需求，修改处理支付回调的逻辑，比如更新订单状态、给用户发送邮件通知、给用户赠送积分等。

支付回调是同步逻辑，依赖浏览器跳转到回调地址，才能处理支付结果。这种方式不太可靠，可能出现跳转过程中用户关闭了浏览器等情况，导致支付结果没有被正常处理。 更可靠的方式是通过 Webhook，配置支付结果异步通知。

修改支付通知逻辑
你需要先在 Stripe 后台 配置 Webhook 地址
比如把 Webhook 地址配置为：https://your-domain.com/api/pay/notify/stripe

监听的事件可以只选择以下两个：

checkout.session.completed
invoice.payment_succeeded
用户支付后，Stripe 会把支付信息推送到这个地址。

处理支付通知
默认的支付通知逻辑位于：src/app/api/pay/notify/stripe/route.ts

你可以根据自己的需求，修改处理支付通知的逻辑，比如更新订单状态、给用户发送邮件通知、给用户赠送积分等。

自定义支付
分组价格表
修改价格表配置文件，添加 groups 数据，配置多个价格分组。并在 pricing.items 下为每一个价格方案，设置一个 group 名称。



配置完成后，点击价格分组，将根据 group 字段，切换显示不同的价格方案。



订阅支付
ShipAny 模板使用 Stripe 支付时，默认支持三种支付方案

一次性扣费：one-time
按月订阅扣费：month
按年订阅扣费：year
你只需要修改价格表配置，把每个价格方案的 interval 字段，设置成上述三个值之一。

同时，按需修改价格(amount) / 积分(credits) / 有效期(valid_months) 等字段。

举例：按月订阅扣费，月付 $99，购买后得到 30 个积分，有效期 1 个月，则核心的价格表配置信息为：

"interval": "month",
"amount": 9900,
"currency": "USD",
"credits": 30,
"valid_months": 1

使用折扣码
在 Stripe 后台 创建折扣码。

修改 src/app/api/checkout/route.ts 文件，设置 Stripe 下单的 options 参数。

允许用户输入自定义的折扣码
options.allow_promotion_codes = true;
使用系统默认的折扣码
options.allow_promotion_codes = false;
options.discounts = [
  {
    coupon: "HAPPY-NEW-YEAR",
  },
];
不使用折扣
options.allow_promotion_codes = false;
options.discounts = [];
人民币支付
在 Stripe 后台 设置支付方式，开通支付宝和微信支付。

修改价格表配置文件，在每个价格方案下添加一个 cn_amount 字段，即可支持人民币支付。

比如，产品售价，$99，人民币支付价格为 699 元，核心配置信息为：

"amount": 9900,
"cn_amount": 69900,
"currency": "USD"

配置完成后，在价格表下单按钮上方，将会显示一个人民币支付图标。

本地测试
开启测试模式
在 Stripe 后台点击左上角的店铺打开下拉菜单，依次点击 Switch to sandbox -> Test mode，开启测试模式。

生成测试密钥
在测试模式下，进入开发者中心，设置 测试支付密钥，包括 Publishable key 和 Secret key。

测试支付通知
注册 ngrok 账号，按指示安装 ngrok 命令行工具。

启动 ngrok 服务，监听本地端口，并生成一个临时的域名。

ngrok http http://localhost:3000
在 Stripe 后台测试模式中，配置 Webhook 地址为 ngrok 生成的域名，并监听以下两个事件：

checkout.session.completed
invoice.payment_succeeded
Endpoint 填写支付通知地址，比如 https://xxx.ngrok-free.app/api/pay/notify/stripe。



添加 Webhook 地址后，在 Webhook 管理页面，复制 Signing secret，



跟支付密钥一起填入 .env.development 文件中。

STRIPE_PUBLIC_KEY = "pk_test_xxx"
STRIPE_PRIVATE_KEY = "sk_test_xxx"
STRIPE_WEBHOOK_SECRET = "whsec_xxx"

测试支付
在本地启动项目，访问 /pricing 页面，点击下单按钮，下单成功后跳转到支付页面。

使用 Stripe 测试卡 支付，支付成功后浏览器跳转到支付回调地址，监听的地址收到支付通知。

参考
Stripe 官方文档
Stripe Webhook 配置