
import { NextResponse } from 'next/server';

 

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const stock_code = searchParams.get('stock_code');
  const run_id = searchParams.get('run_id');

  console.log(`[API] performance-summary | code=${stock_code} | run_id=${run_id}`);

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
    let filterStart = null;
    let filterEnd = null;

    if (targetRunId) {
        try {
            const runRes = await fetch(`${url}/rest/v1/runs?run_id=eq.${targetRunId}&select=start_date,end_date`, {
                headers: { apikey: key, Authorization: `Bearer ${key}` },
                cache: 'no-store'
            });
            if (runRes.ok) {
                const rows = await runRes.json();
                if (rows.length > 0) {
                    filterStart = rows[0].start_date;
                    filterEnd = rows[0].end_date;
                }
            }
        } catch (e) {}
    } else {
      // Auto-detect latest run
      try {
        const runsRes = await fetch(`${url}/rest/v1/runs?stock_code=eq.${stock_code}&order=created_at.desc&limit=1&select=run_id,start_date,end_date`, {
          headers: { apikey: key, Authorization: `Bearer ${key}` },
          cache: 'no-store'
        });
        if (runsRes.ok) {
          const runsData = await runsRes.json();
          if (runsData && runsData.length > 0) {
            targetRunId = runsData[0].run_id;
            filterStart = runsData[0].start_date;
            filterEnd = runsData[0].end_date;
            console.log(`[API] Auto-detected latest run_id: ${targetRunId}`);
          }
        }
      } catch (e) {
        console.warn("Failed to auto-detect latest run", e);
      }
    }

    let endpoint = `${url}/rest/v1/daily_metrics?symbol=eq.${encodeURIComponent(stock_code)}&order=date.asc`;
    if (targetRunId) {
      endpoint += `&run_id=eq.${targetRunId}`;
    } else {
      console.warn("[API] No run_id filter applied! This will return mixed data.");
    }
    
    if (filterStart) endpoint += `&date=gte.${filterStart}`;
    if (filterEnd) endpoint += `&date=lte.${filterEnd}`;
    
    console.log(`[API] Fetching metrics from: ${endpoint}`);
    
    const resp = await fetch(endpoint, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        Accept: 'application/json',
      },
      cache: 'no-store',
    });
    if (!resp.ok) {
      return NextResponse.json({ error: `Supabase daily_metrics read failed: ${resp.status}` }, { status: 502 });
    }
    const rows: any[] = await resp.json();
    
    // Deduplicate rows by date (keep the last one if duplicates exist)
    // This handles cases where Supabase might have duplicate entries if unique constraint is missing
    const uniqueRowsMap = new Map();
    rows.forEach(r => {
      const d = new Date(r.date).toISOString().slice(0, 10);
      uniqueRowsMap.set(d, r);
    });
    const uniqueRows = Array.from(uniqueRowsMap.values()).sort((a: any, b: any) => 
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    const sinceInceptionValues = uniqueRows.map(r => ({
      timestamp: new Date(r.date).toISOString(),
      equity: Number(r.equity ?? 0),
      signal: '',
      price: 0,
      quantity: 0,
    }));
    const latestEquity = sinceInceptionValues.length > 0 ? sinceInceptionValues[sinceInceptionValues.length - 1].equity : 0;
    const previousEquity = sinceInceptionValues.length > 1 ? sinceInceptionValues[sinceInceptionValues.length - 2].equity : latestEquity;
    const change24h = latestEquity - previousEquity;
    const summary = {
      modelId: 'deepseek',
      currentEquity: latestEquity,
      change24h,
      sharpe: 0,
      winRate: 0,
    };
    return NextResponse.json({
      summary,
      sinceInceptionValues,
      generatedAt: new Date().toISOString(),
    }, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to process performance summary.' }, { status: 500 });
  }
}
