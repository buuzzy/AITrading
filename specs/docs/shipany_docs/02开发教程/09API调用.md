创建 API
在 ShipAny 中创建新接口，跟 NextJS 框架创建新接口的规则一致。

在 app/api 目录下创建一个接口文件夹，新建 route.ts 文件

实现接口业务逻辑

app/api/ping/route.ts

import { respData, respErr } from "@/lib/resp";
 
export async function POST(req: Request) {
  try {
    const { message } = await req.json();
    if (!message) {
      return respErr("invalid params");
    }
 
    return respData({
      pong: `received message: ${message}`,
    });
  } catch (e) {
    console.log("test failed:", e);
    return respErr("test failed");
  }
}
调试 API
在终端使用 curl 命令调试 API
Terminal

curl -X POST -H "Content-Type: application/json" \
    -d '{"message": "hello"}' \
    http://localhost:3000/api/ping
或者通过 VS Code 的 REST Client 插件调试 API
ping-api

参考资料
NextJS 框架 API 处理
Last updated on 2025年1月5日