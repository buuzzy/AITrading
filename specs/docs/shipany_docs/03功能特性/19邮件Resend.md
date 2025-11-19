ShipAny 支持使用 Resend 发送邮件，可用于发送邮件验证码、发送支付通知、发送营销邮件等场景。

Resend 设置
在 Resend 网站注册账号并登录后台

在 Resend 后台 添加域名，设置 DNS 记录，验证域名

在 Resend 后台 创建 API 密钥，并复制 API 密钥

ShipAny 配置
在 ShipAny 项目配置文件中，填写 Resend 相关的配置信息。

开发环境配置文件 .env.development
生产环境配置文件 .env.production / wrangler.toml
RESEND_API_KEY = "re_xxx"
RESEND_SENDER_EMAIL = "contact@mail.shipany.ai"

RESEND_API_KEY 在 Resend 后台创建的 API 密钥
RESEND_SENDER_EMAIL 发件人邮箱，前缀可以自定义，域名需要先在 Resend 后台添加并验证
比如在 Resend 后台配置的邮件域名是 mail.shipany.ai，则发件人邮箱可以配置为 contact@mail.shipany.ai / test@mail.shipany.ai / info@mail.shipany.ai 等。

发送邮件
在需要发邮件的地方，根据具体场景，选择合适的发送方式。

发送文本邮件
import { Resend } from "resend";
 
const resend = new Resend(process.env.RESEND_API_KEY!);
 
const result = await resend.emails.send({
  from: process.env.RESEND_SENDER_EMAIL!,
  to: ["test@mail.shipany.ai"],
  subject: "Hello from ShipAny with Resend",
  text: "Hello World.",
});
 
console.log("send email result", result);

发送 HTML 邮件
import { Resend } from "resend";
 
const resend = new Resend(process.env.RESEND_API_KEY!);
 
const result = await resend.emails.send({
  from: process.env.RESEND_SENDER_EMAIL!,
  to: ["test@mail.shipany.ai"],
  subject: "Hello from ShipAny with Resend",
  html: "<p style='color: red;'>Hello from <a href='https://shipany.ai'>ShipAny</a>.</p>",
});
 
console.log("send email result", result);

发送模板邮件
先创建一个邮件模板，比如在： @/components/email-templates/verify-code.tsx 中写入内容：
export function VerifyCode({ code }: { code: string }) {
  return (
    <div>
      <h1>Verify Code</h1>
      <p style={{ color: "red" }}>Your verification code is: {code}</p>
    </div>
  );
}

引入模板发送邮件：
import { Resend } from "resend";
import { VerifyCode } from "@/components/email-templates/verify-code";
 
const resend = new Resend(process.env.RESEND_API_KEY!);
 
const result = await resend.emails.send({
  from: process.env.RESEND_SENDER_EMAIL!,
  to: ["test@mail.shipany.ai"],
  subject: "Hello from ShipAny with Resend",
  react: VerifyCode({ code: "123456" }),
});
 
console.log("send email result", result);

使用 React Email
React Email 内置大量邮件组件，可以让你更轻松创建邮件模板。

安装 React Email 组件库
pnpm add resend @react-email/components
创建邮件模板
比如在 @/components/email-templates/react-email.tsx 中写入内容：

import * as React from "react";
import { Html, Button } from "@react-email/components";
 
export function ReactEmail(props: { url: string }) {
  const { url } = props;
 
  return (
    <Html lang="en">
      <Button href={url}>Click me</Button>
    </Html>
  );
}

引入模板发送邮件：
import { Resend } from "resend";
import { ReactEmail } from "@/components/email-templates/react-email";
 
const resend = new Resend(process.env.RESEND_API_KEY!);
 
const result = await resend.emails.send({
  from: process.env.RESEND_SENDER_EMAIL!,
  to: ["test@mail.shipany.ai"],
  subject: "Hello from ShipAny with Resend",
  react: ReactEmail({ url: "https://shipany.ai" }),
});
 
console.log("send email result", result);

除了自己实现邮件模板，你也可以在 React Email 模板市场 选择一个模板，修改后直接使用。

参考
Resend 接入文档
React Email 接入文档
