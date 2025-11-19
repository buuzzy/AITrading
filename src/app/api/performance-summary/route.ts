
import { NextResponse } from 'next/server';

 

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
    const endpoint = `${url}/rest/v1/daily_metrics?symbol=eq.${encodeURIComponent(stock_code)}&order=date.asc`;
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
    const sinceInceptionValues = rows.map(r => ({
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
