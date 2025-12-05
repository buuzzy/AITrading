
import { NextResponse } from 'next/server';

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
          }
        }
      } catch (e) { }
    }

    let ohlcEndpoint = `${url}/rest/v1/ohlc?symbol=eq.${encodeURIComponent(stock_code)}&order=date.asc`;
    let tradesEndpoint = `${url}/rest/v1/trades?symbol=eq.${encodeURIComponent(stock_code)}&order=date.asc`;
    
    if (targetRunId) {
      ohlcEndpoint += `&run_id=eq.${targetRunId}`;
      tradesEndpoint += `&run_id=eq.${targetRunId}`;
    }
    if (filterStart) {
      ohlcEndpoint += `&date=gte.${filterStart}`;
      tradesEndpoint += `&date=gte.${filterStart}`;
    }
    if (filterEnd) {
      ohlcEndpoint += `&date=lte.${filterEnd}`;
      tradesEndpoint += `&date=lte.${filterEnd}`;
    }

    const [ohlcResp, tradesResp] = await Promise.all([
      fetch(ohlcEndpoint, { headers: { apikey: key, Authorization: `Bearer ${key}`, Accept: 'application/json' }, cache: 'no-store' }),
      fetch(tradesEndpoint, { headers: { apikey: key, Authorization: `Bearer ${key}`, Accept: 'application/json' }, cache: 'no-store' }),
    ]);
    if (!ohlcResp.ok) {
      return NextResponse.json({ error: `Supabase ohlc read failed: ${ohlcResp.status}` }, { status: 502 });
    }
    if (!tradesResp.ok) {
      return NextResponse.json({ error: `Supabase trades read failed: ${tradesResp.status}` }, { status: 502 });
    }
    const oRows: any[] = await ohlcResp.json();
    const tRows: any[] = await tradesResp.json();

    // Deduplicate OHLC
    const oMap = new Map();
    oRows.forEach(r => oMap.set(new Date(r.date).toISOString().slice(0, 10), r));
    const uniqueOhlc = Array.from(oMap.values()).sort((a: any, b: any) => new Date(a.date).getTime() - new Date(b.date).getTime());

    // Deduplicate Trades
    const tMap = new Map();
    tRows.forEach(r => tMap.set(new Date(r.date).toISOString().slice(0, 10), r));
    const uniqueTrades = Array.from(tMap.values()).sort((a: any, b: any) => new Date(a.date).getTime() - new Date(b.date).getTime());

    const ohlc = uniqueOhlc.map(r => ({
      trade_date: new Date(r.date).toISOString(),
      open: Number(r.open ?? 0),
      high: Number(r.high ?? 0),
      low: Number(r.low ?? 0),
      close: Number(r.close ?? 0),
    }));
    const signals = uniqueTrades
      .filter(r => ['buy','sell','close'].includes(String(r.side).toLowerCase()))
      .map(r => ({
        trade_date: new Date(r.date).toISOString(),
        signal: String(r.side),
        quantity: Number(r.qty ?? 0),
        price: Number((r.effective_price ?? r.price) ?? 0),
      }));
    return NextResponse.json({ ohlc, signals }, { headers: { 'Cache-Control': 'no-store' } });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to process K-line data.' }, { status: 500 });
  }
}
