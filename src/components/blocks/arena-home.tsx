import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ChevronRight, Rocket, Bot, LineChart, Terminal, ArrowUpRight, Sparkles, Activity } from "lucide-react";
import { createClient } from "@supabase/supabase-js";
import { SHOWCASE_USER_ID } from "@/services/constant";

type Props = {
  locale: string;
};

export default async function ArenaHome({ locale }: Props) {
  const t = await getTranslations("ArenaHome");

  const manualLiveCodes: string[] = ["512480"];
  let backtestRuns: any[] = [];
  
  const url = (process.env.AITRADE_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL) as string;
  const key = (process.env.AITRADE_SUPABASE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY) as string;
  
  if (url && key) {
    try {
      const supabase = createClient(url, key);
      const { data, error } = await supabase
        .from("runs")
        .select("run_id, stock_code, start_date")
        .eq("user_id", SHOWCASE_USER_ID)
        .eq("status", "completed")
        .order("created_at", { ascending: false })
        .limit(12);

      if (!error && data) {
        backtestRuns = data;
      }
    } catch (e) {
      console.error("Failed to fetch showcase runs", e);
    }
  }

  const toTrading = (code: string, runId?: string) => {
    let path = `/${locale}/trading/${code}`;
    if (runId) {
      path += `?run_id=${runId}`;
    }
    return path;
  };

  const isZh = locale === "zh";
  const heroTitle = isZh ? "A 股实盘 AI 交易" : "Autonomous AI Trading";
  const heroSub = isZh ? "完全由 LLM 进行自主交易决策" : "Next-gen quantitative strategies driven by Large Language Models.";
  const btnText = isZh ? "开始体验" : "Start Trading";
  const btnBacktest = isZh ? "进入回测" : "Run Simulation";

  // Features content
  const features = [
    {
      icon: <Activity className="size-5" />,
      title: isZh ? "挑战不可能" : "The Challenge",
      desc: isZh ? "挑战使用小资金在 A 股盈利，每只股票提供 10 万元资金" : "Aim to profit in A-shares with minimal capital allocation."
    },
    {
      icon: <Bot className="size-5" />,
      title: isZh ? "AI 模型驱动" : "AI Driven",
      desc: isZh ? "完全由 LLM 自主决策，交易完全遵循 A 股规则和基础数据" : "Autonomous decisions respecting all market rules and data constraints."
    },
    {
      icon: <LineChart className="size-5" />,
      title: isZh ? "严谨模拟" : "Rigorous Backtest",
      desc: isZh ? "基于浮点价格成交，计入各类交易手续费，模拟真实交易" : "Float-price execution with full fee simulation for realism."
    }
  ];

  const liveCodes = manualLiveCodes; 
  const primaryLiveHref = toTrading('512480');

  return (
    <div className="min-h-screen bg-base-100 text-base-content font-sans selection:bg-primary/10">
      
      {/* Hero Section */}
      <section className="relative min-h-[65vh] flex flex-col justify-end pb-20 pt-32 overflow-hidden border-b border-base-100">
        {/* Background Glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-[1000px] h-[600px] bg-primary/3 blur-[100px] rounded-full pointer-events-none" />
        
        <div className="container mx-auto px-6 relative z-10 text-center max-w-5xl">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-base-100 border border-base-200 shadow-sm text-[11px] uppercase tracking-widest font-semibold text-base-content/50 mb-8 animate-fade-in-up hover:border-primary/20 transition-colors cursor-default">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
            </span>
            Live on A-Share Market
          </div>
          
          <h1 className="text-6xl md:text-8xl font-black tracking-tighter mb-8 text-base-content leading-[0.9]">
            {heroTitle}
          </h1>
          <p className="text-xl md:text-2xl text-base-content/50 max-w-2xl mx-auto mb-12 font-normal leading-relaxed">
            {heroSub}
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-5">
            <Link href={primaryLiveHref} className="btn btn-primary h-14 px-10 rounded-full text-lg font-bold tracking-wide shadow-xl shadow-primary/20 hover:shadow-primary/30 hover:scale-105 transition-all duration-300">
              {btnText}
            </Link>
            <Link href="/backtest" className="btn btn-ghost h-14 px-10 rounded-full text-lg font-medium text-base-content/70 hover:bg-base-200/50 hover:text-base-content transition-all">
              {btnBacktest}
            </Link>
          </div>
        </div>
      </section>

      {/* Live Strategies */}
      <section className="py-24 border-t border-base-100">
        <div className="container mx-auto px-6 max-w-7xl">
          <div className="flex items-center justify-between mb-12">
            <div>
              <h2 className="text-2xl font-bold flex items-center gap-3">
                <Terminal className="size-6 text-primary" strokeWidth={2} />
                {isZh ? "实盘运行" : "Live Strategies"}
              </h2>
              <p className="text-base-content/50 mt-2 text-sm">Real-time performance tracking.</p>
            </div>
          </div>
          
          {liveCodes.length === 0 ? (
            <div className="p-12 text-center border border-dashed border-base-300 rounded-2xl bg-base-50/50">
              <span className="text-base-content/40">{t("empty")}</span>
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {liveCodes.map((code) => (
                <Link key={code} href={toTrading(code)} className="group block">
                  <div className="relative p-6 bg-base-100 border border-base-200 hover:border-primary/30 rounded-2xl transition-all duration-300 hover:shadow-xl hover:shadow-base-200/50 h-full">
                    <div className="flex justify-between items-start mb-8">
                      <div className="p-2 bg-base-100 border border-base-100 shadow-sm rounded-lg group-hover:scale-110 transition-transform">
                        <Activity className="size-6 text-emerald-500" />
                      </div>
                      <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
                        <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                        Active
                      </span>
                    </div>
                    <div>
                      <h3 className="text-3xl font-mono font-bold tracking-tight mb-1">{code}</h3>
                      <div className="flex items-center gap-2 text-sm text-base-content/50">
                        <span>A-Share</span>
                        <span className="size-1 rounded-full bg-base-300"></span>
                        <span>AI Managed</span>
                      </div>
                    </div>
                    <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0">
                      <ArrowUpRight className="size-5 text-primary" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Backtest Showcase */}
      <section className="py-24 bg-base-50/50 border-t border-base-100">
        <div className="container mx-auto px-6 max-w-7xl">
          <div className="flex items-center gap-4 mb-12">
            <div>
              <h2 className="text-2xl font-bold flex items-center gap-3">
                <LineChart className="size-6 text-secondary" strokeWidth={2} />
                {t("quickLinks")}
              </h2>
              <p className="text-base-content/50 mt-2 text-sm">Historical performance simulations.</p>
            </div>
          </div>

          {backtestRuns.length === 0 ? (
            <div className="p-12 text-center border border-dashed border-base-300 rounded-2xl">
              <span className="text-base-content/40">{t("empty")}</span>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {backtestRuns.map((run) => (
                <Link key={run.run_id} href={toTrading(run.stock_code, run.run_id)} className="group block h-full">
                  <div className="p-5 bg-base-100 border border-base-200 hover:border-base-300 rounded-xl transition-all hover:shadow-md h-full flex flex-col justify-between">
                    <div className="flex justify-between items-start mb-4">
                      <div className="font-mono font-bold text-lg text-base-content/80 group-hover:text-primary transition-colors">
                        {run.stock_code}
                      </div>
                      <div className="badge badge-sm badge-ghost text-[10px] font-medium opacity-60">BACKTEST</div>
                    </div>
                    <div className="text-xs text-base-content/40 font-mono mt-auto pt-4 border-t border-base-100 flex justify-between items-center">
                      <span>{run.start_date}</span>
                      <ChevronRight className="size-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 border-t border-base-100">
        <div className="container mx-auto px-6 max-w-7xl">
          <div className="grid gap-8 md:grid-cols-3">
            {features.map((feature, idx) => (
              <div key={idx} className="p-8 rounded-2xl bg-base-50 border border-base-100 hover:border-base-200 transition-colors">
                <div className="size-12 bg-base-100 rounded-xl border border-base-200 flex items-center justify-center mb-6 text-base-content/80 shadow-sm">
                  {feature.icon}
                </div>
                <h3 className="text-lg font-bold mb-3">{feature.title}</h3>
                <p className="text-sm text-base-content/60 leading-relaxed">
                  {feature.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}