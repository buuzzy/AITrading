import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const stock_code = searchParams.get('stock_code');
  const run_id = searchParams.get('run_id');

  if (!stock_code) {
    return NextResponse.json({ error: 'Missing stock_code parameter.' }, { status: 400 });
  }

  const url = (process.env.AITRADE_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL) as string;
  const key = (process.env.AITRADE_SUPABASE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY) as string;
  if (!url || !key) {
    return NextResponse.json({ error: 'Supabase env missing.' }, { status: 500 });
  }
  try {
    let targetRunId = run_id;

    if (!targetRunId) {
      try {
        const runsRes = await fetch(`${url}/rest/v1/runs?stock_code=eq.${stock_code}&order=created_at.desc&limit=1&select=run_id`, {
          headers: { apikey: key, Authorization: `Bearer ${key}` },
          cache: 'no-store'
        });
        if (runsRes.ok) {
          const runsData = await runsRes.json();
          if (runsData && runsData.length > 0) {
            targetRunId = runsData[0].run_id;
          }
        }
      } catch (e) { }
    }

    let tradesEndpoint = `${url}/rest/v1/trades?symbol=eq.${encodeURIComponent(stock_code)}&order=date.asc`;
    let metricsEndpoint = `${url}/rest/v1/daily_metrics?symbol=eq.${encodeURIComponent(stock_code)}&order=date.asc`;
    
    if (targetRunId) {
      tradesEndpoint += `&run_id=eq.${targetRunId}`;
      metricsEndpoint += `&run_id=eq.${targetRunId}`;
    }

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
      // Model name is now better fetched from the run config in Supabase, but for now leave empty or minimal.
    } catch {}

    // LLM data is no longer fetched in bulk here. It is fetched on-demand via /api/trade-reasoning.
    let llmByDate: Record<string, any> = {};

    function stripHtml(s: string) {
      return s.replace(/<[^>]+>/g, "");
    }
    
    const data = rows.map(r => {
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
        reasoning: '', // Fetched on demand
        technical_analysis: '', // Fetched on demand
        position_total,
        profit,
      };
    });
    return NextResponse.json({ data }, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to process trading data.' }, { status: 500 });
  }
}