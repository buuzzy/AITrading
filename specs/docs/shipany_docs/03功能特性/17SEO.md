ShipAny 做了很多 SEO 优化，可以让你的项目在搜索引擎中获得更好的排名。

项目上线前，你需要对网站内容做一些配置：

设置多语言文案
在 i18n/messages 目录下，通过 [locale].json 文件配置页面内容，默认支持中文和英文，在 i18n/messages/ 目录下，可以看到 en.json 和 zh.json 两个文件，在项目发布之前，修改成跟你项目相符合的文案即可。

可以让 AI 辅助生成内容：

Prompt

update content of this file, for my new project "Flux AI", which is an AI Image Generator, with keywords "flux ai, ai image generator"
i18n-message

设置站点地图
修改 public/sitemap.xml 文件，配置成你自己的站点信息

public/sitemap.xml

<?xml version='1.0' encoding='utf-8' standalone='yes'?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://shipany.ai/</loc>
    <lastmod>2024-12-24T10:00:00+00:00</lastmod>
  </url>
</urlset>
按需修改 public/robots.txt 内容

public/robots.txt

User-agent: *
Disallow: /*?*q=
Disallow: /privacy-policy
Disallow: /terms-of-service
网页 SEO 走查
下载 AITDK 浏览器插件

检查网站首页的 title / description / Canonical 是否合理

aitdk1

调整关键词密度
用 AI 辅助修改 i18n/pages/landing 下 json 文件对应的网页内容，调整网站主打的关键词密度。(3% 左右比较合理)

aitdk2

查看网页结构
ShipAny 对默认的 landing page 做了内容结构优化。如果你有自定义页面组件，需要检查页面的结构是否合理。

aitdk3

SSR 检测
在 AITDK 插件的 Issues 面板开启 SSR Check，检测网页是否是服务端渲染。

aitdk4

Metadata 配置
如果你有创建新的页面路由 (page.tsx)，可以配置一下新页面的 Metadata 信息。

为子页面设置独立的 title / description / canonical 信息，有利于 SEO。

app/[locale]/(default)/posts/page.tsx

import { getTranslations } from "next-intl/server";
 
export async function generateMetadata({
  params: { locale },
}: {
  params: { locale: string };
}) {
  const t = await getTranslations();
 
  let canonicalUrl = `${process.env.NEXT_PUBLIC_WEB_URL}/posts`;
 
  if (locale !== "en") {
    canonicalUrl = `${process.env.NEXT_PUBLIC_WEB_URL}/${locale}/posts`;
  }
 
  return {
    title: t("blog.title"),
    description: t("blog.description"),
    alternates: {
      canonical: canonicalUrl,
    },
  };
}
metadata

接入 GSC
网站上站后，在 Google Search Console 中添加你的站点，可以查看网站的搜索流量和排名情况。

手动提交一下站点地图：

gsc

Last updated on 2025年1月24日