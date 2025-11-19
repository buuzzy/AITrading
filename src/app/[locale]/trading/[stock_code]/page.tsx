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
import { useTranslations } from 'next-intl';
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

export default function TradingPage({ params }: { params: Promise<{ stock_code: string }> }) {
  const { stock_code } = use(params);
  const t = useTranslations('TradingPage');
  const [tradePlans, setTradePlans] = useState<TradePlan[]>([]);
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [chartData, setChartData] = useState<SinceInceptionValue[]>([]);
  const [klineData, setKlineData] = useState<KlineData | null>(null);
  const xRangeRef = useRef<[string, string] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [showHold, setShowHold] = useState(false);
  const [modalTitle, setModalTitle] = useState<string>("");
  const [modalContent, setModalContent] = useState<string>("");

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

  useEffect(() => {
    fetchAll(false);
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
              <div className="text-2xl font-bold">{formatCurrency(100000)}</div>
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
              <CardTitle className="text-sm font-medium">{t('change24h')}</CardTitle>
            </CardHeader>
            <CardContent>
              {isStale ? (
                <div className="text-2xl font-bold text-muted-foreground">—</div>
              ) : (
                <div className={`text-2xl font-bold ${summary.change24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {formatCurrency(summary.change24h)}
                </div>
              )}
              {isStale && (
                <div className="mt-1 text-xs text-muted-foreground">{t('staleNotice')}</div>
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
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="timestamp" 
                  tickFormatter={(str) => new Date(str).toLocaleDateString('en-CA')}
                  ticks={getTicks()}
                  domain={['dataMin', 'dataMax']}
                  type="category"
                />
                <YAxis 
                  tickFormatter={formatYAxis} 
                  domain={['dataMin - 10000', 'dataMax + 10000']} 
                />
                <Tooltip 
                  labelFormatter={(label) => new Date(label).toLocaleDateString('en-CA')}
                  formatter={(value: number) => [formatCurrency(value), t('currentEquity')]}
                />
                <Legend />
                <Line type="monotone" dataKey="equity" stroke="#8884d8" dot={false} activeDot={{ r: 8 }} />
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
                    <TableHead className="w-1/5 pr-4">{t('tableDate')}</TableHead>
                    <TableHead className="w-1/5 pr-4">{t('tableSignal')}</TableHead>
                    <TableHead className="w-1/5 text-right pr-6">{t('tableQuantity')}</TableHead>
                    <TableHead className="w-1/5 text-right pr-6">{t('tableEntryPrice')}</TableHead>
                    <TableHead className="w-1/5 pr-4">T-A</TableHead>
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