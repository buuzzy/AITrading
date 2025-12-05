'use client';

import { useEffect, useState, useMemo, use, useRef } from 'react';
import { createClient } from '@supabase/supabase-js';
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
import { useTheme } from 'next-themes';
import { TrendingUp, Activity, Wallet, FileText, JapaneseYen } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

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
  thinking?: string;
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

interface DailyNav {
  timestamp: string;
  nav: number;
  equity: number;
}

export default function TradingPage({ params }: { params: Promise<{ stock_code: string }> }) {
  const { stock_code } = use(params);
  const searchParams = useSearchParams();
  const runId = searchParams.get('run_id');
  
  const { resolvedTheme } = useTheme();
  const t = useTranslations('TradingPage');
  const locale = useLocale();
  const isZhLocale = String(locale || '').toLowerCase().startsWith('zh');
  const hdrDate = isZhLocale ? '日期' : 'Date';
  const hdrSignal = isZhLocale ? '信号' : 'Signal';
  const hdrQuantity = isZhLocale ? '数量' : 'Quantity';
  const hdrEntryPrice = isZhLocale ? '入场价' : 'Entry Price';
  const hdrPosition = isZhLocale ? '当前持仓' : 'Current Position';
  const hdrProfit = isZhLocale ? '当日盈亏' : 'Profit';
  const hdrTA = isZhLocale ? '技术分析' : 'T-A';
  const [tradePlans, setTradePlans] = useState<TradePlan[]>([]);
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [chartData, setChartData] = useState<SinceInceptionValue[]>([]);
  const [klineData, setKlineData] = useState<KlineData | null>(null);
  const [cashflows, setCashflows] = useState<Cashflow[]>([]);
  const [dailyNav, setDailyNav] = useState<DailyNav[]>([]);
  const xRangeRef = useRef<[string, string] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [showHold, setShowHold] = useState(false);
  const [modalTitle, setModalTitle] = useState<string>("");
  const [modalContent, setModalContent] = useState<string>("");
  const [modalThinking, setModalThinking] = useState<string>("");
  const [showEquity, setShowEquity] = useState(true);
  const [showReturn, setShowReturn] = useState(true);
  const [yRange, setYRange] = useState<[number, number] | null>(null);
  const [axisTicks, setAxisTicks] = useState<{ vals: number[], text: string[] } | null>(null);
  const [loadingPlanDate, setLoadingPlanDate] = useState<string | null>(null);

  const themeColors = useMemo(() => {
    const isDark = resolvedTheme === 'dark';
    return {
      up: '#089981', // TradingView Green
      down: '#F23645', // TradingView Red
      bg: 'transparent',
      grid: isDark ? '#2A2E39' : '#E1E3EB',
      text: isDark ? '#D1D4DC' : '#131722',
      markerBuy: '#089981',
      markerSell: '#F23645',
      markerClose: '#2962FF',
    };
  }, [resolvedTheme]);

  const formatDecimal = (value: number) => new Intl.NumberFormat('zh-CN', { style: 'decimal', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);

  const calculateSharpe = (data: SinceInceptionValue[]) => {
    if (data.length < 2) return 0;
    const returns = [];
    for (let i = 1; i < data.length; i++) {
      const prev = data[i - 1].equity;
      const curr = data[i].equity;
      if (prev > 0) {
        returns.push((curr - prev) / prev);
      }
    }
    if (returns.length === 0) return 0;
    
    const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
    const variance = returns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (returns.length - 1 || 1);
    const stdDev = Math.sqrt(variance);
    
    if (stdDev === 0) return 0;
    return (mean / stdDev) * Math.sqrt(252);
  };

  const calculateWinRate = (plans: TradePlan[]) => {
    const completed = plans.filter(p => p.profit !== null && p.profit !== undefined);
    if (completed.length === 0) return 0;
    const wins = completed.filter(p => (p.profit || 0) > 0);
    return wins.length / completed.length;
  };

  const generateAxisTicks = (startIdx: number, endIdx: number, data: KlineData['ohlc']) => {
    const start = Math.max(0, Math.floor(startIdx));
    const end = Math.min(data.length - 1, Math.ceil(endIdx));
    
    if (start >= end) return null;

    const vals: number[] = [];
    const text: string[] = [];
    
    // Collect all change points
    const yearChanges: number[] = [];
    const monthChanges: number[] = [];
    
    for (let i = start; i <= end; i++) {
      const curr = new Date(data[i].trade_date);
      const prev = i > start ? new Date(data[i-1].trade_date) : null;
      
      if (!prev || curr.getFullYear() !== prev.getFullYear()) {
        yearChanges.push(i);
        monthChanges.push(i); // Year change is also a month change
      } else if (curr.getMonth() !== prev.getMonth()) {
        monthChanges.push(i);
      }
    }

    const span = end - start;
    
    // Strategy Selection
    // 1. Long term (> 500 candles, approx 2 years): Show Years
    if (span > 500) {
      yearChanges.forEach(i => {
        vals.push(i);
        text.push(String(new Date(data[i].trade_date).getFullYear()));
      });
    } 
    // 2. Medium term (> 60 candles, approx 3 months): Show Months
    else if (span > 60) {
      monthChanges.forEach(i => {
        vals.push(i);
        const d = new Date(data[i].trade_date);
        const isJan = d.getMonth() === 0;
        // If Jan (or first visible tick is a year change), show Year, else Month
        if (isJan || yearChanges.includes(i)) {
           text.push(String(d.getFullYear()));
        } else {
           text.push(d.toLocaleDateString(isZhLocale ? 'zh-CN' : 'en-US', { month: 'short' }));
        }
      });
    } 
    // 3. Short term: Show Days (Interval based)
    else {
      // Target roughly 6-8 ticks
      const interval = Math.max(1, Math.ceil(span / 8));
      for (let i = start; i <= end; i += interval) {
        vals.push(i);
        const d = new Date(data[i].trade_date);
        // If it happens to be a month start, show Month name, else MM-DD
        const prev = i > 0 ? new Date(data[i-1].trade_date) : null;
        if (prev && d.getMonth() !== prev.getMonth()) {
             text.push(d.toLocaleDateString(isZhLocale ? 'zh-CN' : 'en-US', { month: 'short' }));
        } else {
             text.push(d.toLocaleDateString(isZhLocale ? 'zh-CN' : 'en-US', { month: '2-digit', day: '2-digit' }));
        }
      }
    }

    return { vals, text };
  };

  const calculateYRange = (startIndex: number, endIndex: number, data: KlineData): [number, number] | null => {
    const len = data.ohlc.length;
    // Clamp indices
    const start = Math.max(0, Math.floor(startIndex));
    const end = Math.min(len - 1, Math.ceil(endIndex));

    if (start >= end) return null;

    let min = Infinity;
    let max = -Infinity;

    for (let i = start; i <= end; i++) {
      const k = data.ohlc[i];
      if (k.low < min) min = k.low;
      if (k.high > max) max = k.high;
    }

    if (min !== Infinity && max !== -Infinity) {
      const padding = (max - min) * 0.05;
      const safePadding = padding === 0 ? max * 0.01 : padding;
      return [min - safePadding, max + safePadding];
    }
    return null;
  };

  const maLines = useMemo(() => {
    if (!klineData) return { ma5: [], ma10: [], ma20: [] };
    const closes = klineData.ohlc.map(d => d.close);
    
    const calcMA = (n: number) => closes.map((_, i, arr) => {
      if (i < n - 1) return null;
      const sum = arr.slice(i - n + 1, i + 1).reduce((a, b) => a + b, 0);
      return sum / n;
    });

    return {
      ma5: calcMA(5),
      ma10: calcMA(10),
      ma20: calcMA(20),
    };
  }, [klineData]);

  // Set initial X and Y range when data loads
  useEffect(() => {
    if (klineData && klineData.ohlc.length > 0) {
      const len = klineData.ohlc.length;
      const zoomCount = 60; // Default to last 60 candles
      const startIdx = Math.max(0, len - zoomCount);
      const endIdx = len - 1;

      if (!xRangeRef.current) {
        xRangeRef.current = [String(startIdx), String(endIdx)];
      }
      
      const [startStr, endStr] = xRangeRef.current;
      const sIdx = parseFloat(startStr);
      const eIdx = parseFloat(endStr);

      const initialY = calculateYRange(sIdx, eIdx, klineData);
      if (initialY) setYRange(initialY);

      const initialTicks = generateAxisTicks(sIdx, eIdx, klineData.ohlc);
      if (initialTicks) setAxisTicks(initialTicks);
    }
  }, [klineData, isZhLocale]);

  const isStale = useMemo(() => {
    if (!chartData || chartData.length === 0) return false;
    const latest = new Date(chartData[chartData.length - 1].timestamp).getTime();
    const now = Date.now();
    return now - latest > 24 * 60 * 60 * 1000; // 超过24小时未更新
  }, [chartData]);

  const itemsPerPage = 15;
  const filteredTradePlans = showHold ? tradePlans : tradePlans.filter(p => p.signal !== 'hold');
  const totalPages = Math.ceil(filteredTradePlans.length / itemsPerPage);
  const paginatedTradePlans = filteredTradePlans.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const initialLoadRef = useRef(true);
  const lastFetchTsRef = useRef(0);
  const lastCashflowFetchTsRef = useRef(0);

  const fetchAll = async (skipLoading?: boolean) => {
    try {
      if (!skipLoading) {
        setLoading(true);
      }
      const querySuffix = `?stock_code=${stock_code}` + (runId ? `&run_id=${runId}` : '');
      
      const [perfResponse, plansResponse, klineResponse] = await Promise.all([
        fetch(`/api/performance-summary${querySuffix}`, { cache: 'no-store' }),
        fetch(`/api/trading-data${querySuffix}`, { cache: 'no-store' }),
        fetch(`/api/kline-data${querySuffix}`, { cache: 'no-store' })
      ]);
      
      // Process Plans First
      let fetchedPlans: TradePlan[] = [];
      if (plansResponse.ok) {
        const plansResult = await plansResponse.json();
        fetchedPlans = (plansResult.data || []).sort((a: TradePlan, b: TradePlan) => new Date(b.date).getTime() - new Date(a.date).getTime());
        setTradePlans(fetchedPlans);
      }

      // Process Performance & Chart
      if (perfResponse.ok) {
        const perfResult = await perfResponse.json();
        const chartVals = perfResult.sinceInceptionValues || [];
        
        // Calculate Real Metrics
        const realSharpe = calculateSharpe(chartVals);
        const realWinRate = calculateWinRate(fetchedPlans);

        setSummary({
          ...perfResult.summary,
          sharpe: realSharpe,
          winRate: realWinRate
        });
        setChartData(chartVals);
      }

      if (klineResponse.ok) {
        const klineResult = await klineResponse.json();
        setKlineData(klineResult);
      }
      
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
    
    let query = supabase
      .from('cashflows')
      .select('date,amount')
      .eq('symbol', stock_code);

    if (runId) {
      query = query.eq('run_id', runId);
    }

    const { data, error } = await query
      .order('date', { ascending: false })
      .limit(50);

    if (!error && Array.isArray(data)) {
      const rows = data.map((r: any) => ({ date: String(r.date), amount: Number(r.amount) }));
      setCashflows(rows);
    }
  };

  const fetchDailyNav = async () => {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL as string;
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_KEY as string;
    if (!supabaseUrl || !supabaseKey) return;
    const supabase = createClient(supabaseUrl, supabaseKey);
    
    let query = supabase
      .from('daily_metrics')
      .select('date,nav,equity')
      .eq('symbol', stock_code);

    if (runId) {
      query = query.eq('run_id', runId);
    }

    const { data, error } = await query
      .order('date', { ascending: true })
      .limit(2000);

    if (!error && Array.isArray(data)) {
      const rows = data.map((r: any) => ({
        timestamp: String(r.date),
        nav: Number(r.nav ?? 0),
        equity: Number(r.equity ?? 0),
      }));
      setDailyNav(rows);
    }
  };

  useEffect(() => {
    fetchAll(false);
    fetchCashflows();
    fetchDailyNav();
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL as string;
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_KEY as string;
    if (supabaseUrl && supabaseKey) {
      const supabase = createClient(supabaseUrl, supabaseKey);
      
      const filterStr = runId ? `run_id=eq.${runId}` : `symbol=eq.${stock_code}`;
      
      const channel = supabase
        .channel('realtime:trading')
        .on('postgres_changes', { event: '*', schema: 'public', table: 'daily_metrics', filter: filterStr }, () => {
          const now = Date.now();
          if (now - lastFetchTsRef.current > 1500) {
            lastFetchTsRef.current = now;
            fetchAll(true);
            fetchDailyNav();
            fetchCashflows();
          }
        })
        .on('postgres_changes', { event: '*', schema: 'public', table: 'trades', filter: filterStr }, () => {
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
          if (now - lastCashflowFetchTsRef.current > 1000) {
            lastCashflowFetchTsRef.current = now;
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

  const openModal = (title: string, content: string, thinking: string = "") => {
    setModalTitle(title);
    setModalContent(content);
    setModalThinking(thinking);
    const dlg = document.getElementById('trade_modal') as HTMLDialogElement | null;
    dlg?.showModal();
  };

  const handleOpenAnalysis = async (plan: TradePlan) => {
    if (plan.technical_analysis && plan.technical_analysis.length > 10) {
      openModal(t('technicalAnalysis'), plan.technical_analysis, plan.thinking);
      return;
    }

    setLoadingPlanDate(plan.date);
    try {
      const res = await fetch(`/api/trade-reasoning?stock_code=${stock_code}&date=${plan.date}`);
      if (!res.ok) throw new Error('Failed to load');
      const data = await res.json();
      
      const ta = data.technical_analysis || data.reasoning;
      const th = data.thinking || "";

      // Update local state to cache the result
      setTradePlans(prev => prev.map(p => 
        p.date === plan.date 
          ? { ...p, technical_analysis: ta, thinking: th } 
          : p
      ));

      openModal(t('technicalAnalysis'), ta || t('noContent'), th);
    } catch (e) {
      openModal(t('technicalAnalysis'), t('noContent'));
    } finally {
      setLoadingPlanDate(null);
    }
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
    if (dailyNav && dailyNav.length > 0) {
      return dailyNav.map(d => ({
        timestamp: d.timestamp,
        equity: d.equity,
        signal: '',
        return_pct: ((d.nav - 1) * 100),
      })) as (SinceInceptionValue & { return_pct: number })[];
    }
    if (!chartData || chartData.length === 0) return [] as (SinceInceptionValue & { return_pct: number })[];
    const initial = chartData[0].equity || 1;
    return chartData.map(d => ({
      ...d,
      return_pct: ((d.equity / initial) - 1) * 100,
    }));
  }, [dailyNav, chartData]);

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
        <div className="stats stats-vertical lg:stats-horizontal shadow w-full bg-base-100">
          
          <div className="stat">
            <div className="stat-figure text-primary">
              <JapaneseYen className="inline-block w-8 h-8 stroke-current" />
            </div>
            <div className="stat-title">{t('currentEquity')}</div>
            <div className="stat-value text-primary">{formatDecimal(summary.currentEquity)}</div>
            <div className="stat-desc">{t('initialCapital')}: {formatCurrency(chartData[0]?.equity ?? 100000)}</div>
          </div>
          
          <div className="stat">
            <div className="stat-figure text-secondary">
              <TrendingUp className="inline-block w-8 h-8 stroke-current" />
            </div>
            <div className="stat-title">{isZhLocale ? '24h 变动' : '24h Change'}</div>
            <div className={`stat-value ${summary.change24h >= 0 ? 'text-success' : 'text-error'}`}>
              {formatCurrency(summary.change24h)}
            </div>
            <div className="stat-desc">
              {chartData.length > 1 ? 
                (isZhLocale ? '上个交易日: ' : 'Prev: ') + formatCurrency(chartData[chartData.length - 2].equity) 
                : 'No data'}
            </div>
          </div>

          <div className="stat">
            <div className="stat-figure text-secondary">
              <Wallet className="inline-block w-8 h-8 stroke-current" />
            </div>
            <div className="stat-title">{isZhLocale ? '资金流向' : 'Cashflow'}</div>
            <div className={`stat-value ${cashflows.length > 0 && cashflows[0].amount >= 0 ? 'text-success' : 'text-error'}`}>
              {cashflows.length > 0 ? formatCurrency(cashflows[0].amount) : '0'}
            </div>
            <div className="stat-desc">
              {cashflows.length > 0 ? new Date(cashflows[0].date).toLocaleDateString() : 'No records'}
            </div>
          </div>

          <div className="stat">
            <div className="stat-figure text-secondary">
              <Activity className="inline-block w-8 h-8 stroke-current" />
            </div>
            <div className="stat-title">{isZhLocale ? '胜率' : 'Win Rate'}</div>
            <div className="stat-value">{summary.winRate ? (summary.winRate * 100).toFixed(1) + '%' : '0.0%'}</div>
            <div className="stat-desc">{isZhLocale ? '夏普比率' : 'Sharpe'}: {summary.sharpe ? summary.sharpe.toFixed(2) : '0.00'}</div>
          </div>

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
                // Main Candles
                {
                  x: klineData.ohlc.map(d => d.trade_date),
                  open: klineData.ohlc.map(d => d.open),
                  high: klineData.ohlc.map(d => d.high),
                  low: klineData.ohlc.map(d => d.low),
                  close: klineData.ohlc.map(d => d.close),
                  type: 'candlestick',
                  name: stock_code,
                  increasing: { line: { color: themeColors.up, width: 1 }, fillcolor: themeColors.up },
                  decreasing: { line: { color: themeColors.down, width: 1 }, fillcolor: themeColors.down },
                  yaxis: 'y',
                },
                // Moving Averages
                {
                  x: klineData.ohlc.map(d => d.trade_date),
                  y: maLines.ma5 as number[],
                  type: 'scatter',
                  mode: 'lines',
                  name: 'MA5',
                  line: { color: '#f59e0b', width: 1 }, // Amber
                  hoverinfo: 'y+name',
                },
                {
                  x: klineData.ohlc.map(d => d.trade_date),
                  y: maLines.ma10 as number[],
                  type: 'scatter',
                  mode: 'lines',
                  name: 'MA10',
                  line: { color: '#3b82f6', width: 1 }, // Blue
                  hoverinfo: 'y+name',
                },
                {
                  x: klineData.ohlc.map(d => d.trade_date),
                  y: maLines.ma20 as number[],
                  type: 'scatter',
                  mode: 'lines',
                  name: 'MA20',
                  line: { color: '#a855f7', width: 1 }, // Purple
                  hoverinfo: 'y+name',
                },
                // Signals
                {
                  x: klineData.signals.filter(s => s.signal === 'buy').map(s => s.trade_date),
                  y: klineData.signals.filter(s => s.signal === 'buy').map(s => s.price * 0.98),
                  mode: 'markers',
                  type: 'scatter',
                  name: 'Buy',
                  marker: { color: themeColors.markerBuy, size: 12, symbol: 'triangle-up' },
                  hoverinfo: 'text',
                  text: klineData.signals.filter(s => s.signal === 'buy').map(s => `Buy: ${s.price}`),
                },
                {
                  x: klineData.signals.filter(s => s.signal === 'sell').map(s => s.trade_date),
                  y: klineData.signals.filter(s => s.signal === 'sell').map(s => s.price * 1.02),
                  mode: 'markers',
                  type: 'scatter',
                  name: 'Sell',
                  marker: { color: themeColors.markerSell, size: 12, symbol: 'triangle-down' },
                  hoverinfo: 'text',
                  text: klineData.signals.filter(s => s.signal === 'sell').map(s => `Sell: ${s.price}`),
                },
                {
                  x: klineData.signals.filter(s => s.signal === 'close').map(s => s.trade_date),
                  y: klineData.signals.filter(s => s.signal === 'close').map(s => s.price),
                  mode: 'markers',
                  type: 'scatter',
                  name: 'Close',
                  marker: { color: themeColors.markerClose, size: 10, symbol: 'x' },
                },
              ] as any}
              layout={{
                height: 500,
                autosize: true,
                margin: { l: 50, r: 50, t: 30, b: 30 },
                paper_bgcolor: themeColors.bg,
                plot_bgcolor: themeColors.bg,
                font: { color: themeColors.text, family: 'Inter, sans-serif' },
                xaxis: {
                  type: 'category',
                  rangeslider: { visible: false },
                  range: (xRangeRef.current || [klineData.ohlc.length - 60, klineData.ohlc.length]),
                  gridcolor: themeColors.grid,
                  showgrid: false, // Clean look per user request
                  zeroline: false,
                  linecolor: themeColors.grid,
                  tickfont: { size: 11 },
                  tickmode: 'array',
                  tickvals: axisTicks?.vals,
                  ticktext: axisTicks?.text,
                  showspikes: true,
                  spikemode: 'across',
                  spikesnap: 'cursor',
                  spikecolor: themeColors.grid,
                  spikethickness: 1,
                  minallowed: -1,
                  maxallowed: klineData.ohlc.length,
                },
                yaxis: {
                  title: { text: '' },
                  gridcolor: themeColors.grid,
                  showgrid: false, // Clean look per user request
                  zeroline: false,
                  linecolor: themeColors.grid,
                  tickfont: { size: 11 },
                  autorange: false,
                  range: yRange || undefined,
                  fixedrange: true,
                  showspikes: true,
                  spikemode: 'across',
                  spikesnap: 'cursor',
                  spikecolor: themeColors.grid,
                  spikethickness: 1,
                },
                hovermode: 'x unified',
                hoverlabel: {
                  bgcolor: resolvedTheme === 'dark' ? '#1e1e1e' : '#ffffff',
                  font: { color: themeColors.text },
                  namelength: -1,
                },
                uirevision: `${stock_code}-${resolvedTheme}`,
                showlegend: true,
                legend: { orientation: 'h', y: 1, x: 0, bgcolor: 'rgba(0,0,0,0)' },
                dragmode: 'pan',
              }}
              config={{ 
                responsive: true, 
                scrollZoom: true, 
                displayModeBar: false 
              }}
              onRelayout={(e: any) => {
                let x0 = e['xaxis.range[0]'];
                let x1 = e['xaxis.range[1]'];
                
                if (!x0 && e['xaxis.range']) {
                  x0 = e['xaxis.range'][0];
                  x1 = e['xaxis.range'][1];
                }

                // Parse indices
                const idx0 = parseFloat(x0);
                const idx1 = parseFloat(x1);

                if (!isNaN(idx0) && !isNaN(idx1)) {
                  const MIN_ZOOM = 10;
                  
                  let finalX0 = idx0;
                  let finalX1 = idx1;

                  if (finalX1 - finalX0 < MIN_ZOOM) {
                    const mid = (finalX0 + finalX1) / 2;
                    finalX0 = mid - MIN_ZOOM / 2;
                    finalX1 = mid + MIN_ZOOM / 2;
                  }

                  const maxIdx = klineData.ohlc.length;
                  if (finalX0 < -1) finalX0 = -1;
                  if (finalX1 > maxIdx) finalX1 = maxIdx;

                  xRangeRef.current = [String(finalX0), String(finalX1)];

                  if (klineData) {
                    const newY = calculateYRange(finalX0, finalX1, klineData);
                    if (newY) setYRange(newY);

                    const newTicks = generateAxisTicks(finalX0, finalX1, klineData.ohlc);
                    if (newTicks) setAxisTicks(newTicks);
                  }
                }
              }}
              useResizeHandler={true}
              style={{ width: '100%', height: '100%' }}            />
          </CardContent>
        </Card>
      )}

      {!loading && !error && (
        <Card className="bg-background">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>{t('plansTitle')}</CardTitle>
            <Button variant="outline" size="sm" onClick={() => { setShowHold(v => !v); setCurrentPage(1); }}>
              {showHold ? '隐藏 hold' : '显示 hold'}
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            {filteredTradePlans.length === 0 ? (
              <div className="py-16 text-center text-base-content/50 whitespace-pre-line">
                {showHold ? t('noPlans') : t('noPlansHint')}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="table table-zebra table-pin-rows">
                  <thead>
                    <tr>
                      <th>{hdrDate}</th>
                      <th>{hdrSignal}</th>
                      <th className="text-right">{hdrQuantity}</th>
                      <th className="text-right">{hdrEntryPrice}</th>
                      <th className="text-right">{hdrPosition}</th>
                      <th className="text-right">{hdrProfit}</th>
                      {/* <th>{hdrTA}</th> Removed */}
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedTradePlans.map((plan, index) => (
                      <tr key={index}>
                        <td className="font-mono text-xs opacity-70">{plan.date}</td>
                        <td>
                          <div
                            className={`badge ${
                              plan.signal === 'buy'
                                ? 'badge-success text-success-content'
                                : plan.signal === 'sell'
                                ? 'badge-error text-error-content'
                                : 'badge-neutral'
                            } badge-sm font-bold uppercase px-2`}
                          >
                            {plan.signal}
                          </div>
                        </td>
                        <td className="text-right font-mono">{plan.quantity}</td>
                        <td className="text-right font-mono">
                          {(() => {
                            const val = parseFloat(plan.entry_price);
                            return isNaN(val) ? plan.entry_price : val.toFixed(4);
                          })()}
                        </td>
                        <td className="text-right font-mono">{plan.position_total != null ? plan.position_total : '-'}</td>
                        <td className="text-right font-mono">
                          {plan.profit != null ? (
                            <span className={plan.profit >= 0 ? 'text-success' : 'text-error'}>
                              {formatCurrency(plan.profit)}
                            </span>
                          ) : '-'}
                        </td>
                        {/* <td>Removed TA Button</td> */}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
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
          <CardContent className="p-0">
            {cashflows.length === 0 ? (
              <div className="py-10 text-center text-base-content/50">{isZhLocale ? '暂无资金事件' : 'No cashflows'}</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="table table-zebra table-sm">
                  <thead>
                    <tr>
                      <th className="w-1/2 pl-6">{isZhLocale ? '日期' : 'Date'}</th>
                      <th className="w-1/2 text-right pr-6">{isZhLocale ? '金额' : 'Amount'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cashflows.slice(0, 10).map((cf, idx) => (
                      <tr key={idx}>
                        <td className="pl-6 font-mono opacity-80">{new Date(cf.date).toLocaleDateString(isZhLocale ? 'zh-CN' : 'en-CA')}</td>
                        <td className={`text-right pr-6 font-mono font-medium ${cf.amount >= 0 ? 'text-success' : 'text-error'}`}>
                          {formatCurrency(cf.amount)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
      <dialog id="trade_modal" className="modal">
        <div className="modal-box w-11/12 max-w-5xl h-[70vh] overflow-y-auto">
          <form method="dialog">
            <button className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button>
          </form>
          <h3 className="text-lg font-bold mb-4">{modalTitle}</h3>
          {modalThinking && (
            <div className="collapse collapse-arrow bg-base-200 mb-4 text-sm">
              <input type="checkbox" /> 
              <div className="collapse-title font-medium opacity-70">
                AI Thinking Process
              </div>
              <div className="collapse-content"> 
                <p className="whitespace-pre-wrap leading-relaxed opacity-80">{modalThinking}</p>
              </div>
            </div>
          )}
          <p className="whitespace-pre-wrap leading-relaxed">{modalContent}</p>
        </div>
        <form method="dialog" className="modal-backdrop">
          <button className="sr-only">close</button>
        </form>
      </dialog>
    </div>
  );
}
