'use client';

import { useEffect, useState, useMemo, use, useRef } from 'react';
import { createClient } from '@supabase/supabase-js';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useTranslations, useLocale } from 'next-intl';
import dynamic from 'next/dynamic';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface TradePlan {
  date: string;
  model: string;
  symbol: string;
  signal: 'buy' | 'sell' | 'hold' | 'close';
  quantity: string;
  entry_price: string;
  confidence: string;
  stop_loss?: string;
  reasoning?: string;
  technical_analysis?: string;
  position_total?: number | null;
  profit?: number | null;
}

interface PerformanceSummary {
  modelId: string;
  currentEquity: number;
  change24h: number;
  sharpe: number;
  winRate: number;
}

interface SinceInceptionValue {
  timestamp: string;
  equity: number;
  signal: string;
}

interface KlineData {
  ohlc: {
    trade_date: string;
    open: number;
    high: number;
    low: number;
    close: number;
  }[];
  signals: {
    trade_date: string;
    signal: string;
    quantity: number;
    price: number;
  }[];
}

interface Cashflow {
  date: string;
  amount: number;
}

export default function TradingPage({ params }: { params: Promise<{ stock_code: string }> }) {
  const { stock_code } = use(params);
  const t = useTranslations('TradingPage');
  const locale = useLocale();
  const isZhLocale = String(locale || '').toLowerCase().startsWith('zh');
  const hdrDate = isZhLocale ? '日期' : 'Date';
  const hdrSignal = isZhLocale ? '信号' : 'Signal';
  const hdrQuantity = isZhLocale ? '数量' : 'Quantity';
  const hdrEntryPrice = isZhLocale ? '入场价' : 'Entry Price';
  const hdrPosition = isZhLocale ? '持仓' : 'Position';
  const hdrProfit = isZhLocale ? '当日盈亏' : 'Profit';
  const hdrTA = isZhLocale ? '技术分析' : 'T-A';
  const [tradePlans, setTradePlans] = useState<TradePlan[]>([]);
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [chartData, setChartData] = useState<SinceInceptionValue[]>([]);
  const [klineData, setKlineData] = useState<KlineData | null>(null);
  const [cashflows, setCashflows] = useState<Cashflow[]>([]);
  const xRangeRef = useRef<[string, string] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [showHold, setShowHold] = useState(false);
  const [modalTitle, setModalTitle] = useState<string>("");
  const [modalContent, setModalContent] = useState<string>("");
  const [showEquity, setShowEquity] = useState(true);
  const [showReturn, setShowReturn] = useState(true);

  const isStale = useMemo(() => {
    if (!chartData || chartData.length === 0) return false;
    const latest = new Date(chartData[chartData.length - 1].timestamp).getTime();
    const now = Date.now();
    return now - latest > 24 * 60 * 60 * 1000; // 超过24小时未更新
  }, [chartData]);

  const itemsPerPage = 20;
  const filteredTradePlans = showHold ? tradePlans : tradePlans.filter(p => p.signal !== 'hold');
  const totalPages = Math.ceil(filteredTradePlans.length / itemsPerPage);
  const paginatedTradePlans = filteredTradePlans.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const initialLoadRef = useRef(true);
  const lastFetchTsRef = useRef(0);

  const fetchAll = async (skipLoading?: boolean) => {
    try {
      if (!skipLoading) {
        setLoading(true);
      }
      const [perfResponse, plansResponse, klineResponse] = await Promise.all([
        fetch(`/api/performance-summary?stock_code=${stock_code}`, { cache: 'no-store' }),
        fetch(`/api/trading-data?stock_code=${stock_code}`, { cache: 'no-store' }),
        fetch(`/api/kline-data?stock_code=${stock_code}`, { cache: 'no-store' })
      ]);
      if (!perfResponse.ok) {
        const errorData = await perfResponse.json();
        throw new Error(errorData.error || t('error', { error: 'Failed to fetch performance summary' }));
      }
      const perfResult = await perfResponse.json();
      setSummary(perfResult.summary);
      setChartData(perfResult.sinceInceptionValues);
      if (!plansResponse.ok) {
        const errorData = await plansResponse.json();
        throw new Error(errorData.error || t('error', { error: 'Failed to fetch trade plans' }));
      }
      const plansResult = await plansResponse.json();
      const sortedPlans = (plansResult.data || []).sort((a: TradePlan, b: TradePlan) => new Date(b.date).getTime() - new Date(a.date).getTime());
      setTradePlans(sortedPlans);
      if (!klineResponse.ok) {
        const errorData = await klineResponse.json();
        throw new Error(errorData.error || t('error', { error: 'Failed to fetch K-line data' }));
      }
      const klineResult = await klineResponse.json();
      setKlineData(klineResult);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
      initialLoadRef.current = false;
    }
  };

  const fetchCashflows = async () => {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL as string;
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_KEY as string;
    if (!supabaseUrl || !supabaseKey) return;
    const supabase = createClient(supabaseUrl, supabaseKey);
    const { data, error } = await supabase
      .from('cashflows')
      .select('date,amount')
      .eq('symbol', stock_code)
      .order('date', { ascending: false })
      .limit(50);
    if (!error && Array.isArray(data)) {
      const rows = data.map((r: any) => ({ date: String(r.date), amount: Number(r.amount) }));
      setCashflows(rows);
    }
  };

  useEffect(() => {
    fetchAll(false);
    fetchCashflows();
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL as string;
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_KEY as string;
    if (supabaseUrl && supabaseKey) {
      const supabase = createClient(supabaseUrl, supabaseKey);
      const channel = supabase
        .channel('realtime:trading')
        .on('postgres_changes', { event: '*', schema: 'public', table: 'daily_metrics', filter: `symbol=eq.${stock_code}` }, () => {
          const now = Date.now();
          if (now - lastFetchTsRef.current > 1500) {
            lastFetchTsRef.current = now;
            fetchAll(true);
          }
        })
        .on('postgres_changes', { event: '*', schema: 'public', table: 'trades', filter: `symbol=eq.${stock_code}` }, () => {
          const now = Date.now();
          if (now - lastFetchTsRef.current > 1500) {
            lastFetchTsRef.current = now;
            fetchAll(true);
          }
        })
        .on('postgres_changes', { event: '*', schema: 'public', table: 'ohlc', filter: `symbol=eq.${stock_code}` }, () => {
          const now = Date.now();
          if (now - lastFetchTsRef.current > 1500) {
            lastFetchTsRef.current = now;
            fetchAll(true);
          }
        })
        .on('postgres_changes', { event: '*', schema: 'public', table: 'cashflows', filter: `symbol=eq.${stock_code}` }, () => {
          const now = Date.now();
          if (now - lastFetchTsRef.current > 1500) {
            lastFetchTsRef.current = now;
            fetchCashflows();
          }
        })
        .subscribe();
      return () => {
        try { supabase.removeChannel(channel); } catch {}
      };
    } else {
      const id = setInterval(fetchAll, 60000);
      return () => clearInterval(id);
    }
  }, [stock_code]);

  const formatCurrency = (value: number) => new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(value);
  const formatYAxis = (tick: number) => `${(tick / 10000).toFixed(1)}万`;
  const formatPct = (v: number) => `${v.toFixed(2)}%`;

  const openModal = (title: string, content: string) => {
    setModalTitle(title);
    setModalContent(content);
    const dlg = document.getElementById('trade_modal') as HTMLDialogElement | null;
    dlg?.showModal();
  };

  const getTicks = () => {
    if (chartData.length === 0) return [];
    const first = chartData[0].timestamp;
    const last = chartData[chartData.length - 1].timestamp;
    const yearEnd = new Date(new Date(first).getFullYear(), 11, 30).toISOString();
    const ticks = [first, last];
    if (yearEnd !== first && yearEnd !== last) {
      ticks.push(yearEnd);
    }
    return Array.from(new Set(ticks)).sort();
  };

  const chartWithReturn = useMemo(() => {
    if (!chartData || chartData.length === 0) return [] as (SinceInceptionValue & { return_pct: number })[];
    const initial = chartData[0].equity || 1;
    return chartData.map(d => ({
      ...d,
      return_pct: ((d.equity / initial) - 1) * 100,
    }));
  }, [chartData]);

  const equityRange = useMemo(() => {
    if (!chartWithReturn.length) return { min: 0, max: 0 };
    let min = chartWithReturn[0].equity;
    let max = chartWithReturn[0].equity;
    for (const d of chartWithReturn) {
      if (d.equity < min) min = d.equity;
      if (d.equity > max) max = d.equity;
    }
    const pad = Math.max((max - min) * 0.05, 10000);
    return { min: min - pad, max: max + pad };
  }, [chartWithReturn]);

  const returnRange = useMemo(() => {
    if (!chartWithReturn.length) return { min: 0, max: 0 };
    let min = chartWithReturn[0].return_pct;
    let max = chartWithReturn[0].return_pct;
    for (const d of chartWithReturn) {
      if (d.return_pct < min) min = d.return_pct;
      if (d.return_pct > max) max = d.return_pct;
    }
    const span = max - min;
    const pad = Math.max(span * 0.1, 1);
    return { min: min - pad, max: max + pad };
  }, [chartWithReturn]);

  const labelEquity = isZhLocale ? '资金' : 'Equity';
  const labelReturn = isZhLocale ? '收益率' : 'Return';

  const renderLegend = (props: any) => {
    const items = [
      { key: 'equity', color: '#8884d8', name: labelEquity, active: showEquity },
      { key: 'return_pct', color: '#82ca9d', name: labelReturn, active: showReturn },
    ];
    return (
      <div className="w-full flex justify-center items-center gap-6 text-sm">
        {items.map(it => (
          <button
            key={it.key}
            className={`flex items-center gap-2 ${it.active ? '' : 'opacity-50'}`}
            onClick={() => {
              if (it.key === 'equity') setShowEquity(v => !v);
              if (it.key === 'return_pct') setShowReturn(v => !v);
            }}
          >
            <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: it.color }} />
            <span>{it.name}</span>
          </button>
        ))}
      </div>
    );
  };

  const defaultXRange = useMemo(() => {
    if (!klineData || !klineData.ohlc || klineData.ohlc.length === 0) return null;
    const times = klineData.ohlc.map(d => new Date(d.trade_date).getTime());
    const firstTs = times[0];
    const lastTs = times[times.length - 1];
    const ninetyDays = 90 * 24 * 60 * 60 * 1000;
    const startTs = Math.max(firstTs, lastTs - ninetyDays);
    return [new Date(startTs).toISOString(), new Date(lastTs).toISOString()] as [string, string];
  }, [klineData]);

  return (
    <div className="container mx-auto py-10 space-y-8">
      <h1 className="text-3xl font-bold">{t('title', { stock_code })}</h1>

      {loading && <p>{t('loading')}</p>}
      {error && <p className="text-red-500">{t('error', { error })}</p>}

      {!loading && !error && summary && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="bg-background">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('initialCapital')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(chartData[0]?.equity ?? 100000)}</div>
            </CardContent>
          </Card>
          <Card className="bg-background">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('currentEquity')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(summary.currentEquity)}</div>
            </CardContent>
          </Card>
          <Card className="bg-background">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{isZhLocale ? '上一个交易日变动' : 'Prev Trading Day Change'}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${summary.change24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {formatCurrency(summary.change24h)}
              </div>
              {chartData.length > 1 && (
                <div className="mt-1 text-xs text-muted-foreground">
                  {isZhLocale ? '上一个交易日：' : 'Prev day:'} {new Date(chartData[chartData.length - 2].timestamp).toLocaleDateString(isZhLocale ? 'zh-CN' : 'en-CA')} ，{isZhLocale ? '资金' : 'Equity'}：{formatCurrency(chartData[chartData.length - 2].equity)}
                </div>
              )}
            </CardContent>
          </Card>
          <Card className="bg-background">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{isZhLocale ? '资金事件' : 'Cashflows'}</CardTitle>
            </CardHeader>
            <CardContent>
              {cashflows.length > 0 ? (
                <div className={`text-2xl font-bold ${cashflows[0].amount >= 0 ? 'text-green-500' : 'text-red-500'}`}>{formatCurrency(cashflows[0].amount)}</div>
              ) : (
                <div className="text-2xl font-bold">{isZhLocale ? '无' : 'None'}</div>
              )}
              {cashflows.length > 0 && (
                <div className="mt-1 text-xs text-muted-foreground">
                  {(isZhLocale ? '最近一次：' : 'Latest: ') + new Date(cashflows[0].date).toLocaleDateString(isZhLocale ? 'zh-CN' : 'en-CA')}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {!loading && !error && chartData.length > 0 && (
        <Card className="bg-background">
          <CardHeader>
            <CardTitle>{t('sinceInceptionEquity')}</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartWithReturn}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(str) => new Date(str).toLocaleDateString('en-CA')}
                  ticks={getTicks()}
                  domain={['dataMin', 'dataMax']}
                  type="category"
                />
                <YAxis yAxisId="left" tickFormatter={formatYAxis} domain={[equityRange.min, equityRange.max]} />
                <YAxis yAxisId="right" orientation="right" tickFormatter={formatPct} domain={[returnRange.min, returnRange.max]} />
                <Tooltip 
                  labelFormatter={(label) => new Date(label).toLocaleDateString('en-CA')}
                  formatter={(value: number, name: string) => {
                    if (name === 'equity' || name === labelEquity) return [formatCurrency(value), labelEquity];
                    return [formatPct(value), labelReturn];
                  }}
                />
                <Legend content={renderLegend} />
                <Line yAxisId="left" name={labelEquity} hide={!showEquity} type="monotone" dataKey="equity" stroke="#8884d8" dot={false} activeDot={{ r: 8 }} />
                <Line yAxisId="right" name={labelReturn} hide={!showReturn} type="monotone" dataKey="return_pct" stroke="#82ca9d" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {!loading && !error && klineData && (
        <Card className="bg-background">
          <CardHeader>
            <CardTitle>{t('klineTitle')}</CardTitle>
          </CardHeader>
          <CardContent>
                      <Plot
                        data={[
                          {
                            x: klineData.ohlc.map(d => d.trade_date),
                            open: klineData.ohlc.map(d => d.open),
                            high: klineData.ohlc.map(d => d.high),
                            low: klineData.ohlc.map(d => d.low),
                            close: klineData.ohlc.map(d => d.close),
                            type: 'candlestick',
                            name: stock_code,
                            increasing: { line: { color: '#22c55e' } },
                            decreasing: { line: { color: '#ef4444' } },
                          },
                          {
                            x: klineData.signals.filter(s => s.signal === 'buy').map(s => s.trade_date),
                            y: klineData.signals.filter(s => s.signal === 'buy').map(s => s.price),
                            mode: 'markers',
                            type: 'scatter',
                            name: 'Buy',
                            marker: { color: 'green', size: 10, symbol: 'triangle-up' },
                          },
                          {
                            x: klineData.signals.filter(s => s.signal === 'sell').map(s => s.trade_date),
                            y: klineData.signals.filter(s => s.signal === 'sell').map(s => s.price),
                            mode: 'markers',
                            type: 'scatter',
                            name: 'Sell',
                            marker: { color: 'red', size: 10, symbol: 'triangle-down' },
                          },
                          {
                            x: klineData.signals.filter(s => s.signal === 'close').map(s => s.trade_date),
                            y: klineData.signals.filter(s => s.signal === 'close').map(s => s.price),
                            mode: 'markers',
                            type: 'scatter',
                            name: 'Close',
                            marker: { color: 'blue', size: 10, symbol: 'x' },
                          },
                        ]}
                        layout={{
                          height: 500,
                          title: { text: t('klineTitle') },
                          template: 'plotly_dark' as unknown as Plotly.Template,
                          paper_bgcolor: 'rgba(0,0,0,0)',
                          plot_bgcolor: 'rgba(0,0,0,0)',
                          xaxis: {
                            rangeslider: { visible: true },
                            range: (xRangeRef.current || defaultXRange || undefined),
                          },
                          yaxis: { 
                            title: { text: 'Price' },
                            gridcolor: 'rgba(255,255,255,0.2)'
                          },
                          uirevision: stock_code,
                          legend: {
                            font: {
                              color: 'white'
                            }
                          }
                        }}
                        config={{ responsive: true }}
                        onRelayout={(e: any) => {
                          const r0 = e['xaxis.range[0]'];
                          const r1 = e['xaxis.range[1]'];
                          if (r0 && r1) {
                            xRangeRef.current = [r0, r1];
                          }
                        }}
                        useResizeHandler={true}
                        style={{ width: '100%', height: '100%' }}
                      />
                    </CardContent>        </Card>
      )}

      {!loading && !error && (
        <Card className="bg-background">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>{t('plansTitle')}</CardTitle>
            <Button variant="outline" size="sm" onClick={() => { setShowHold(v => !v); setCurrentPage(1); }}>
              {showHold ? '隐藏 hold' : '显示 hold'}
            </Button>
          </CardHeader>
          <CardContent>
            {filteredTradePlans.length === 0 ? (
              <div className="py-10 text-center text-muted-foreground whitespace-pre-line">
                {showHold ? 'LLM当前暂无交易决策' : 'LLM当前暂无交易决策\n你可点击“显示 hold”查看更多决策信息”'}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[14.285%] pr-4">{hdrDate}</TableHead>
                    <TableHead className="w-[14.285%] pr-4">{hdrSignal}</TableHead>
                    <TableHead className="w-[14.285%] text-right pr-6">{hdrQuantity}</TableHead>
                    <TableHead className="w-[14.285%] text-right pr-6">{hdrEntryPrice}</TableHead>
                    <TableHead className="w-[14.285%] text-right pr-6">{hdrPosition}</TableHead>
                    <TableHead className="w-[14.285%] text-right pr-6">{hdrProfit}</TableHead>
                    <TableHead className="w-[14.285%] pr-4">{hdrTA}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedTradePlans.map((plan, index) => (
                    <TableRow key={index}>
                      <TableCell>{plan.date}</TableCell>
                      <TableCell>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium ${
                            plan.signal === 'buy'
                              ? 'bg-green-100 text-green-800'
                              : plan.signal === 'sell'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {plan.signal}
                        </span>
                      </TableCell>
                      <TableCell className="text-right pr-6">{plan.quantity}</TableCell>
                      <TableCell className="text-right pr-6">{plan.entry_price}</TableCell>
                      <TableCell className="text-right pr-6">{plan.position_total != null ? plan.position_total : ''}</TableCell>
                      <TableCell className="text-right pr-6">
                        {plan.profit != null ? (
                          <span className={plan.profit >= 0 ? 'text-red-500 font-medium' : 'text-green-500 font-medium'}>
                            {formatCurrency(plan.profit)}
                          </span>
                        ) : ''}
                      </TableCell>
                      <TableCell className="pr-4">
                        <button
                          className="btn btn-sm btn-ghost"
                          onClick={() => openModal('Technical Analysis', plan.technical_analysis || '暂无内容')}
                        >
                          查看
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
          {filteredTradePlans.length > 0 && (
            <CardFooter className="flex items-center justify-between">
              <div className="text-xs text-muted-foreground">
                {t('pagination', { currentPage, totalPages })}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                >
                  {t('prevPage')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                >
                  {t('nextPage')}
                </Button>
              </div>
            </CardFooter>
          )}
        </Card>
      )}

      {!loading && !error && (
        <Card className="bg-background">
          <CardHeader>
            <CardTitle>{isZhLocale ? '资金事件明细' : 'Cashflow Details'}</CardTitle>
          </CardHeader>
          <CardContent>
            {cashflows.length === 0 ? (
              <div className="py-10 text-center text-muted-foreground">{isZhLocale ? '暂无资金事件' : 'No cashflows'}</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-1/2 pr-4">{isZhLocale ? '日期' : 'Date'}</TableHead>
                    <TableHead className="w-1/2 text-right pr-6">{isZhLocale ? '金额' : 'Amount'}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {cashflows.slice(0, 10).map((cf, idx) => (
                    <TableRow key={idx}>
                      <TableCell>{new Date(cf.date).toLocaleDateString(isZhLocale ? 'zh-CN' : 'en-CA')}</TableCell>
                      <TableCell className={`text-right pr-6 ${cf.amount >= 0 ? 'text-green-500' : 'text-red-500'}`}>{formatCurrency(cf.amount)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
      <dialog id="trade_modal" className="modal">
        <div className="modal-box w-11/12 max-w-5xl h-[70vh] overflow-y-auto">
          <form method="dialog">
            <button className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
          </form>
          <h3 className="text-lg font-bold">{modalTitle}</h3>
          <p className="py-4 whitespace-pre-wrap leading-relaxed">{modalContent}</p>
        </div>
        <form method="dialog" className="modal-backdrop">
          <button className="sr-only">close</button>
        </form>
      </dialog>
    </div>
  );
}
