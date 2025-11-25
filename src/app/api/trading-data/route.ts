import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const stock_code = searchParams.get('stock_code');

  if (!stock_code) {
    return NextResponse.json({ error: 'Missing stock_code parameter.' }, { status: 400 });
  }

  const url = (process.env.AITRADE_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL) as string;
  const key = (process.env.AITRADE_SUPABASE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY) as string;
  if (!url || !key) {
    return NextResponse.json({ error: 'Supabase env missing.' }, { status: 500 });
  }
  try {
    const tradesEndpoint = `${url}/rest/v1/trades?symbol=eq.${encodeURIComponent(stock_code)}&order=date.asc`;
    const metricsEndpoint = `${url}/rest/v1/daily_metrics?symbol=eq.${encodeURIComponent(stock_code)}&order=date.asc`;
    const [resp, mresp] = await Promise.all([
      fetch(tradesEndpoint, {
        headers: {
          apikey: key,
          Authorization: `Bearer ${key}`,
          Accept: 'application/json',
        },
        cache: 'no-store',
      }),
      fetch(metricsEndpoint, {
        headers: {
          apikey: key,
          Authorization: `Bearer ${key}`,
          Accept: 'application/json',
        },
        cache: 'no-store',
      }),
    ]);
    if (!resp.ok) {
      return NextResponse.json({ error: `Supabase trades read failed: ${resp.status}` }, { status: 502 });
    }
    if (!mresp.ok) {
      return NextResponse.json({ error: `Supabase metrics read failed: ${mresp.status}` }, { status: 502 });
    }
    const rows: any[] = await resp.json();
    const mrows: any[] = await mresp.json();
    const mByDate: Record<string, any> = {};
    for (const r of mrows) {
      try {
        const d = new Date(r.date).toISOString().slice(0, 10);
        mByDate[d] = r;
      } catch {}
    }
    let modelName = '';
    try {
      const p = path.join(process.cwd(), 'specs', 'backtest', String(stock_code), `progress_${String(stock_code)}.json`);
      const txt = fs.readFileSync(p, 'utf-8');
      const obj = JSON.parse(txt);
      if (obj && typeof obj.model_name === 'string') {
        modelName = obj.model_name;
      }
    } catch {}

    let llmByDate: Record<string, any> = {};
    try {
      const llmPath = path.join(process.cwd(), 'specs', 'backtest', String(stock_code), `llm_${String(stock_code)}.json`);
      const llmTxt = fs.readFileSync(llmPath, 'utf-8');
      const llmObj = JSON.parse(llmTxt);
      if (llmObj && typeof llmObj === 'object') {
        llmByDate = llmObj as Record<string, any>;
      }
    } catch {}
    function stripHtml(s: string) {
      return s.replace(/<[^>]+>/g, "");
    }
    function normalizeText(s: string) {
      return s
        .replace(/[\t ]+/g, " ")
        .replace(/\r\n/g, "\n")
        .replace(/\n{3,}/g, "\n\n")
        .trim();
    }
    function markdownToPlain(s: string) {
      let text = s;
      text = text.replace(/```[\s\S]*?```/g, "");
      text = text.replace(/`([^`]+)`/g, "$1");
      text = text.replace(/^#{1,6}\s*(.+)$/gm, "\n【$1】\n\n");
      text = text.replace(/\*\*(.+?)\*\*/g, "【$1】");
      text = text.replace(/(^|\n)\s*[-*]\s+/g, "$1• ");
      // 列表块前后分段
      text = text.replace(/(\n• .+)(\n(• .+))+?/g, (m) => `\n${m}\n\n`);
      text = text.replace(/\n{3,}/g, "\n\n");
      text = text.replace(/【{2,}/g, "【");
      text = text.replace(/】{2,}/g, "】");
      return text;
    }
    function addSentenceBreaks(s: string) {
      let t = s;
      // 中文句子分隔
      t = t.replace(/([。！？])(?![”’）\)])/g, '$1\n');
      // 英文句子分隔：在句末标点后、下一句以大写字母开头时换行
      t = t.replace(/([.!?])\s+(?=[A-Z])/g, '$1\n');
      // 保持项目符号整行
      t = t.replace(/\n\s*•\s+/g, '\n• ');
      // 合并多余换行
      t = t.replace(/\n{3,}/g, '\n\n');
      return t.trim();
    }
    function extractTA(s: string) {
      let text = stripHtml(s);
      let start = text.indexOf("EXTERNAL TECHNICAL ANALYSIS");
      if (start >= 0) {
        text = text.slice(start);
        text = text.replace(/^.*EXTERNAL TECHNICAL ANALYSIS[^\n]*\n?/, "");
      }
      const stops = [
        "DATA FOR ",
        "PORTFOLIO SNAPSHOT",
        "BACKTEST STATE",
        "STRATEGY FLAGS",
        "STRATEGY CORRECTIONS",
      ];
      const stopIndexes = stops
        .map((m) => text.indexOf(m))
        .filter((i) => i >= 0);
      if (stopIndexes.length > 0) {
        const end = Math.min(...stopIndexes);
        text = text.slice(0, end);
      }
      text = markdownToPlain(text);
      text = addSentenceBreaks(text);
      return normalizeText(text);
    }

    const data = rows.map(r => {
      const llm = llmByDate[String(r.date)] || {};
      const rawReasoning = (llm?.decision?.reasoning ?? llm?.reasoning ?? '') as string;
      const rawTA = (llm?.market_prompt ?? '') as string;
      const reasoning = normalizeText(stripHtml(rawReasoning));
      const technical_analysis = extractTA(rawTA);
      let position_total: number | null = null;
      let profit: number | null = null;
      try {
        const dkey = new Date(r.date).toISOString().slice(0, 10);
        const cur = mByDate[dkey];
        if (cur) {
          if (cur.position !== undefined && cur.position !== null) {
            position_total = Number(cur.position);
          }
          if (cur.daily_return !== undefined && cur.daily_return !== null) {
            profit = Number(cur.daily_return);
          } else if (cur.equity !== undefined && cur.equity !== null) {
            const prevDate = Object.keys(mByDate)
              .filter(k => k < dkey)
              .sort()
              .pop();
            if (prevDate) {
              const prev = mByDate[prevDate];
              if (prev && prev.equity !== undefined && prev.equity !== null) {
                profit = Number(cur.equity) - Number(prev.equity);
              }
            }
          }
        }
      } catch {}
      return {
        date: r.date,
        model: modelName,
        symbol: stock_code,
        signal: String(r.side).toLowerCase(),
        quantity: String(r.qty ?? ''),
        entry_price: String((r.effective_price ?? r.price) ?? ''),
        confidence: '',
        stop_loss: '',
        reasoning,
        technical_analysis,
        position_total,
        profit,
      };
    });
    return NextResponse.json({ data }, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to process trading data.' }, { status: 500 });
  }
}