Landing Page 是 ShipAny 的特色功能之一，你可以通过简单的配置，自定义 Landing Page 的样式和内容。

修改 Landing Page 内容
ShipAny 内置一个 Landing Page 页面，通过 JSON 文件定义了页面上的全部内容。

默认支持多语言，英文 Landing Page 文件位于 i18n/pages/landing/en.json 文件中。

中文 Landing Page 文件位于 i18n/pages/landing/zh.json 文件中。

你可以在 i18n/pages/landing 目录下，添加其他语言的 Landing Page 文件。

Landing Page 文件包括以下几部分内容，你可以根据自己的需求，修改成对应的内容。

i18n/pages/landing/en.json

{
  "template": "shipany-template-one",
  "theme": "light",
  "header": {},
  "hero": {},
  "branding": {},
  "introduce": {},
  "benefit": {},
  "usage": {},
  "feature": {},
  "showcase": {},
  "stats": {},
  "pricing": {},
  "testimonial": {},
  "faq": {},
  "cta": {},
  "footer": {}
}
使用 AI 编辑器生成新的 Landing Page 内容
你可以在 AI 编辑器 Cursor 中，输入你的新网站主题，通过 AI 对话，指定参考资料，生成新网站的 Landing Page 内容。

参考 Prompt：

Prompt

I want to build a landing page for my product named "Flux AI Image Generator", please update the landing page json file, content reference @Web @https://www.flux.ai/
update-landing

使用 AI 对话产品，生成新的 Landing Page 内容
你可以复制默认的 Landing Page 内容，使用 AI 对话产品，比如：ThinkAny / v0 / Claude / ChatGPT / Kimi 等， 生成新的 Landing Page 内容。

参考 Prompt：

Prompt

rewrite this json file with new content for my product, focus on topic "Flux AI Image Generator"
claude-landing

修改 Landing Page 页面结构
默认的 Landing Page 布局文件位于 app/[locale]/(default)/layout.tsx 文件中。

app/[locale]/(default)/layout.tsx

export default async function DefaultLayout({
  children,
  params: { locale },
}: {
  children: ReactNode;
  params: { locale: string };
}) {
  const page = await getLandingPage(locale);
 
  return (
    <>
      {page.header && <Header header={page.header} />}
      <main className="overflow-x-hidden">{children}</main>
      {page.footer && <Footer footer={page.footer} />}
    </>
  );
}
首页的内容结构位于 app/[locale]/(default)/page.tsx 文件中。

app/[locale]/(default)/page.tsx

export default async function LandingPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  const page = await getLandingPage(locale);
 
  return (
    <>
      {page.hero && <Hero hero={page.hero} />}
      {page.branding && <Branding section={page.branding} />}
      {page.introduce && <Feature1 section={page.introduce} />}
      {page.benefit && <Feature2 section={page.benefit} />}
      {page.usage && <Feature3 section={page.usage} />}
      {page.feature && <Feature section={page.feature} />}
      {page.showcase && <Showcase section={page.showcase} />}
      {page.stats && <Stats section={page.stats} />}
      {page.pricing && <Pricing pricing={page.pricing} />}
      {page.testimonial && <Testimonial section={page.testimonial} />}
      {page.faq && <FAQ section={page.faq} />}
      {page.cta && <CTA section={page.cta} />}
    </>
  );
}
你可以根据新网站的需求，自行修改。比如删除部分组件，或者添加一些新组件。

每个组件支持传递的参数，请在组件文档部分查看。

Last updated on 2025年1月5日