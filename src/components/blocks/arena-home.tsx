import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ChevronRight } from "lucide-react";

type Props = {
  locale: string;
};

// 极简首页组件：说明 + 从 Live 目录生成交易入口
export default async function ArenaHome({ locale }: Props) {
  const t = await getTranslations("ArenaHome");

  let stockCodes: string[] = [];
  const url = (process.env.AITRADE_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL) as string;
  const key = (process.env.AITRADE_SUPABASE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY) as string;
  if (url && key) {
    try {
      const dm = `${url}/rest/v1/daily_metrics?select=symbol`;
      const cp = `${url}/rest/v1/checkpoints?select=symbol`;
      const [dmResp, cpResp] = await Promise.all([
        fetch(dm, { headers: { apikey: key, Authorization: `Bearer ${key}`, Accept: "application/json" }, cache: "no-store" }),
        fetch(cp, { headers: { apikey: key, Authorization: `Bearer ${key}`, Accept: "application/json" }, cache: "no-store" }),
      ]);
      const dmRows: any[] = dmResp.ok ? await dmResp.json() : [];
      const cpRows: any[] = cpResp.ok ? await cpResp.json() : [];
      const set = new Set<string>();
      dmRows.forEach((r: any) => { if (r && typeof r.symbol === "string" && r.symbol) set.add(r.symbol); });
      cpRows.forEach((r: any) => { if (r && typeof r.symbol === "string" && r.symbol) set.add(r.symbol); });
      stockCodes = Array.from(set).sort();
    } catch {
      stockCodes = [];
    }
  }

  const toTrading = (code: string) => `/${locale}/trading/${code}`;
  const isZh = locale === "zh";
  const heroTitle = isZh ? "A 股实盘 AI 交易" : "AI Trading in real A-shares markets";
  const heroSub = isZh ? "完全由 LLM 进行自主交易决策" : "Fully autonomous decisions by LLM";
  const btnText = isZh ? "开始体验" : "Get Started";
  const card1Title = isZh ? "🚀 挑战不可能" : "🚀 Challenge the Impossible";
  const card1Desc = isZh
    ? "挑战使用小资金在 A 股盈利，每只股票提供 10 万元资金"
    : "Aim to profit in A-shares with small capital; ¥100,000 per stock";
  const card2Title = isZh ? "🤖 AI 模型驱动" : "🤖 AI Model Driven";
  const card2Desc = isZh
    ? "完全由 LLM 自主决策，交易完全遵循 A 股规则和基础数据"
    : "LLM makes autonomous decisions; trades comply with A-share rules and data";
  const card3Title = isZh ? "📊 严谨模拟回测" : "📊 Rigorous Backtesting";
  const card3Desc = isZh
    ? "基于浮点价格成交，计入各类交易手续费，模拟真实交易"
    : "Float-price fills, all fees applied, realistic trade simulation";

  return (
    <div>
      <section className="hero min-h-[30rem] rounded bg-base-200">
        <div className="text-center hero-content">
          <div className="max-w-2xl">
            <h3 className="text-5xl font-bold">{heroTitle}</h3>
            <p className="py-6 text-lg">{heroSub}</p>
            <Link href={`/${locale}/trading/600895`} className="btn btn-primary">{btnText}</Link>
          </div>
        </div>
      </section>

      <section className="container pb-20">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">{t("quickLinks")}</h2>
        </div>
        {stockCodes.length === 0 ? (
          <div className="mt-4 text-sm text-base-content/60">{t("empty")}</div>
        ) : (
          <div className="mt-6 grid gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {stockCodes.map((code) => (
              <Link key={code} href={toTrading(code)} className="group">
                <div className="tooltip tooltip-bottom w-full" data-tip={t("enter")}>
                  <div className="card bg-base-100 transition shadow-sm group-hover:shadow-xl">
                    <div className="card-body p-6">
                      <div className="flex items-center justify-between">
                        <span className="card-title font-mono text-lg">{code}</span>
                        <ChevronRight className="size-5 text-base-content/50 group-hover:text-primary" />
                      </div>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        <div data-theme="cupcake" className="mt-10">
          <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 justify-items-center">
          <div className="card w-full max-w-sm bg-gradient-to-br from-base-100 to-base-200 border-2 border-primary ring-1 ring-primary/30 shadow-xl hover:shadow-2xl transition hover:-translate-y-0.5">
            <div className="card-body p-6">
              <h3 className="text-2xl font-bold">{card1Title}</h3>
              <p className="text-base-content/80">{card1Desc}</p>
            </div>
          </div>
          <div className="card w-full max-w-sm bg-gradient-to-br from-base-100 to-base-200 border-2 border-primary ring-1 ring-primary/30 shadow-xl hover:shadow-2xl transition hover:-translate-y-0.5">
            <div className="card-body p-6">
              <h3 className="text-2xl font-bold">{card2Title}</h3>
              <p className="text-base-content/80">{card2Desc}</p>
            </div>
          </div>
          <div className="card w-full max-w-sm bg-gradient-to-br from-base-100 to-base-200 border-2 border-primary ring-1 ring-primary/30 shadow-xl hover:shadow-2xl transition hover:-translate-y-0.5">
            <div className="card-body p-6">
              <h3 className="text-2xl font-bold">{card3Title}</h3>
              <p className="text-base-content/80">{card3Desc}</p>
            </div>
          </div>
          </div>
        </div>
      </section>
    </div>
  );
}