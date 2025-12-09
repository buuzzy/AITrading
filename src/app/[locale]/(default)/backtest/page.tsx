'use client';

import React, { useState, useEffect, useCallback } from 'react';
import AIStrategyWizard from '@/components/backtest/AIStrategyWizard';
import { useTranslations } from 'next-intl';
import { RotateCcw, History, AlertCircle, Info, CheckCircle } from 'lucide-react';
import { ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// --- Types ---
interface StrategySnapshot {
  id: string;
  timestamp: number;
  config: any;
  result: any;
  symbol: string;
}

interface ToastMessage {
  id: string;
  type: 'info' | 'success' | 'error';
  text: string;
}

// --- Main Page Component ---
export default function BacktestPage() {
  const t = useTranslations('Backtest');
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  
  // Core State
  const [strategyConfig, setStrategyConfig] = useState<any>(null);
  const [symbol, setSymbol] = useState('000001');
  
  // History State
  const [history, setHistory] = useState<StrategySnapshot[]>([]);
  
  // Intent Persistence
  const [userIntent, setUserIntent] = useState('');
  
  // Date constraints
  const today = new Date().toISOString().split('T')[0];
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-06-01');
  
  // Validation State
  const [stockName, setStockName] = useState('');
  const [isValidStock, setIsValidStock] = useState(true);
  const [isValidating, setIsValidating] = useState(false);
  
  // Execution State
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [logs, setLogs] = useState('');
  
  // Diagnosis State
  const [diagnosisContext, setDiagnosisContext] = useState<any>(null); // New structured context
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [chatMode, setChatMode] = useState<'creation' | 'edit' | 'diagnosis' | null>(null);

  // UI State
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [snapshotToRestore, setSnapshotToRestore] = useState<StrategySnapshot | null>(null);

  // --- Helper Functions ---
  const showToast = (text: string, type: 'info' | 'success' | 'error' = 'info') => {
    const id = crypto.randomUUID();
    setToasts(prev => [...prev, { id, type, text }]);
    setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, 3000);
  };

  const checkStock = useCallback(async (code: string) => {
    if (code.length !== 6) return;
    
    setIsValidating(true);
    try {
      const res = await fetch(`/api/validate/stock?code=${code}`);
      const data = await res.json();
      if (data.valid) {
        setIsValidStock(true);
        setStockName(data.name);
      } else {
        setIsValidStock(false);
        setStockName('');
      }
    } catch (e) {
      setIsValidStock(false);
    } finally {
      setIsValidating(false);
    }
  }, []);

  // Handle Symbol Input Change
  const handleSymbolChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '');
    setSymbol(val);
    
    if (val.length < 6) {
        setIsValidStock(true);
        setStockName('');
    } else if (val.length === 6) {
        checkStock(val);
    }
  };

  const handleStrategyApply = (config: any) => {
    setStrategyConfig(config);
    setDiagnosisContext(null); // Clear diagnosis context after apply
    showToast('Strategy applied successfully', 'success');
  };

  const handleCreateNew = () => {
    setChatHistory([]); 
    setChatMode('creation');
    setDiagnosisContext(null); // Not in diagnosis mode
    setUserIntent(''); // Reset intent for new session
    setIsWizardOpen(true);
  };

  const handleEdit = () => {
    setChatHistory([]);
    setChatMode('edit'); 
    setDiagnosisContext(null); // Edit mode is not diagnosis
    setIsWizardOpen(true);
  };

  const confirmRestore = () => {
    if (snapshotToRestore) {
        setStrategyConfig(snapshotToRestore.config);
        setResult(snapshotToRestore.result);
        setChatHistory([]); 
        setDiagnosisContext(null);
        setUserIntent(''); 
        showToast('Version restored', 'success');
        setSnapshotToRestore(null);
    }
  };

  const handleDiagnose = () => {
    if (!result?.report) return;
    
    // 1. Auto-Save Snapshot logic (kept same)
    const isConfigExist = history.some(snap => JSON.stringify(snap.config) === JSON.stringify(strategyConfig));
    if (!isConfigExist) {
        const newSnapshot: StrategySnapshot = {
            id: crypto.randomUUID(),
            timestamp: Date.now(),
            config: strategyConfig,
            result: result,
            symbol: symbol
        };
        setHistory(prev => [...prev, newSnapshot].slice(-20));
    }
    
    // 2. Prepare RICH Diagnosis Context
    const finalEquity = result.final_equity || 100000;
    const totalReturnPct = ((finalEquity - 100000) / 100000 * 100).toFixed(2);
    const winRatePct = (result.report.win_rate * 100).toFixed(1);
    const totalTrades = result.report.total_trades;
    
    let reportText = `[BACKTEST SUMMARY]\n`;
    reportText += `- Total Return: ${totalReturnPct}%
`;
    reportText += `- Win Rate: ${winRatePct}%
`;
    reportText += `- Total Trades: ${totalTrades}
`;
    reportText += `- Final Equity: ${finalEquity.toFixed(2)}

`;
    
    if (result.report.bad_trades && result.report.bad_trades.length > 0) {
        reportText += `[TOP LOSSES]
`;
        result.report.bad_trades.forEach((t: any, i: number) => {
            reportText += `Loss #${i+1}: ${t.date}, PnL=${t.pnl.toFixed(2)} (${(t.pnl_pct*100).toFixed(2)}%), Reason=${t.reason}
`;
            reportText += `  Context: Price=${t.context.price.toFixed(2)}, RSI=${t.context.rsi_14?.toFixed(1) || 'N/A'}
`;
        });
    }

    // 3. Set Context State (Don't send yet!)
    setDiagnosisContext({
        report: reportText,
        strategy_config: JSON.stringify(strategyConfig, null, 2), // Inject Strategy Config
        summary: `当前策略收益率 ${totalReturnPct}%，胜率 ${winRatePct}%。`
    });
    
    // 4. Reset Chat ONLY if it's a fresh diagnosis (or you can add logic to track session IDs)
    // For now, we allow appending to existing history if the user re-opens diagnosis for the same result.
    // However, if the result *changed*, we might want to clear. 
    // Since handleDiagnose is usually called on a specific result state, let's just Open the wizard.
    // Note: If you want to force clear on every NEW diagnosis click, keep setChatHistory([]).
    // But to fix "losing context on close/reopen", we should NOT clear here blindly if we are just re-opening.
    
    // Simple heuristic: If chatHistory is empty, it's fresh. If not, we keep it.
    // If user wants a FRESH diagnosis, they can use "Create New" or we can add a "Clear" button in Wizard.
    // setChatHistory([]); // REMOVED to preserve history
    
    // Logic: If previous mode was NOT diagnosis (e.g. creation/edit), we MUST clear history to avoid context pollution.
    if (chatMode !== 'diagnosis') {
        setChatHistory([]);
    }
    setChatMode('diagnosis');
    setIsWizardOpen(true);
  };

  const runBacktest = async () => {
    if (!strategyConfig) return;
    if (symbol.length !== 6) {
        setIsValidStock(false);
        return;
    }
    if (startDate > endDate) {
      showToast('Start date must be before end date', 'error');
      return;
    }

    setIsRunning(true);
    setResult(null);
    setLogs('');

    try {
      const fmtStart = startDate.replace(/-/g, '');
      const fmtEnd = endDate.replace(/-/g, '');

      const res = await fetch('/api/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy_config: strategyConfig,
          symbol,
          start_date: fmtStart,
          end_date: fmtEnd
        }),
      });

      if (!res.body) throw new Error('No response body');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullLogs = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        fullLogs += chunk;
        setLogs((prev) => prev + chunk);
      }

      const lines = fullLogs.trim().split('\n');
      let finalResult = null;
      for (let i = lines.length - 1; i >= 0; i--) {
        try {
          const parsed = JSON.parse(lines[i]);
          if (parsed.status || parsed.final_equity) {
            finalResult = parsed;
            break;
          }
        } catch (e) {}
      }

      if (finalResult) {
        setResult(finalResult);
        
        setHistory(prev => {
            const isConfigExist = prev.some(snap => JSON.stringify(snap.config) === JSON.stringify(strategyConfig));
            
            if (isConfigExist) {
                return prev; 
            }
            
            const newSnapshot: StrategySnapshot = {
                id: crypto.randomUUID(),
                timestamp: Date.now(),
                config: strategyConfig,
                result: finalResult,
                symbol: symbol 
            };
            return [...prev, newSnapshot].slice(-20);
        });
      }

    } catch (e: any) {
      setLogs((prev) => prev + `\n[Error] ${e.message}`);
      showToast(e.message || 'Backtest failed', 'error');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-base-200 p-8 font-sans text-base-content relative">
      
      {/* Toast Container (DaisyUI) */}
      {toasts.length > 0 && (
          <div className="toast toast-top toast-center z-50">
              {toasts.map(toast => (
                  <div key={toast.id} className={`alert ${ 
                      toast.type === 'error' ? 'alert-error' : 
                      (toast.type === 'success' ? 'alert-success' : 'alert-info')
                  } text-white shadow-lg`}>
                      {toast.type === 'error' && <AlertCircle className="size-5" />}
                      {toast.type === 'success' && <CheckCircle className="size-5" />}
                      {toast.type === 'info' && <Info className="size-5" />}
                      <span>{toast.text}</span>
                  </div>
              ))}
          </div>
      )}

      {/* Restore Confirmation Modal (DaisyUI) */}
      {snapshotToRestore && (
        <dialog className="modal modal-open">
          <div className="modal-box bg-base-100 border border-base-300">
            <h3 className="font-bold text-lg">Confirm Restore</h3>
            <p className="py-4 text-base-content/70">
                Are you sure you want to restore this version?
                <br />
                <span className="text-sm text-error mt-2 block">
                    Warning: Current configuration and unsaved chat history will be lost.
                </span>
            </p>
            <div className="modal-action">
              <button className="btn btn-ghost" onClick={() => setSnapshotToRestore(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={confirmRestore}>Restore</button>
            </div>
          </div>
          <form method="dialog" className="modal-backdrop">
             <button onClick={() => setSnapshotToRestore(null)}>close</button>
          </form>
        </dialog>
      )}

      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex justify-between items-end border-b border-base-300 pb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
            <p className="text-base-content/60 mt-2">
              {t('subtitle')}
            </p>
          </div>
          <button 
            onClick={handleCreateNew}
            className="btn btn-primary shadow-sm"
          >
            <span className="mr-2">✨</span> {t('createStrategy')}
          </button>
        </div>

        {/* Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Configuration & History */}
          <div className="lg:col-span-1 space-y-6">
            
             {/* History Dropdown / List */}
             {history.length > 0 && (
                <div className="bg-base-100 rounded-xl border border-base-300 p-5 shadow-sm">
                    <div className="flex items-center gap-2 text-sm font-semibold text-base-content/60 mb-3">
                        <History className="size-4" />
                        <span>回测历史</span>
                    </div>
                    <div className="space-y-2 max-h-40 overflow-y-auto pr-1 custom-scrollbar">
                        {[...history].reverse().map((snap, idx) => {
                            const versionNum = history.length - idx;
                            const returnPct = ((snap.result.final_equity - 100000) / 1000);
                            const isPositive = returnPct >= 0;
                            
                            return (
                                <div key={snap.id} className="flex items-center justify-between p-3 rounded-lg bg-base-200/50 border border-base-200 text-xs group hover:bg-base-200 transition-colors">
                                    <div className="flex flex-col gap-1">
                                        <div className="flex items-center gap-3">
                                            <span className="font-bold text-base-content/80">V{versionNum}</span>
                                            <span className="text-base-content/40 text-[10px]">{new Date(snap.timestamp).toLocaleTimeString()}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] text-base-content/60 bg-base-100 border border-base-300 px-1.5 py-0.5 rounded">{snap.symbol}</span>
                                            <span className={`font-mono font-bold ${isPositive ? 'text-success' : 'text-error'}`}>
                                                {returnPct > 0 ? '+' : ''}{returnPct.toFixed(2)}%
                                            </span>
                                        </div>
                                    </div>
                                    <button 
                                        onClick={() => setSnapshotToRestore(snap)}
                                        className="opacity-0 group-hover:opacity-100 btn btn-ghost btn-xs btn-square text-primary"
                                        title="Restore this version"
                                    >
                                        <RotateCcw className="size-3.5" />
                                    </button>
                                </div>
                            );
                        })}
                    </div>
                </div>
             )}

            {/* 1. Strategy Card */}
            <div className="bg-base-100 rounded-xl border border-base-300 p-5 shadow-sm h-[400px] flex flex-col">
              <div className="flex justify-between items-center mb-4 shrink-0">
                <h3 className="font-semibold text-lg">{t('strategyConfig')}</h3>
                {strategyConfig ? (
                  <span className="badge badge-success badge-md font-bold uppercase px-3 border-transparent text-white">{t('loaded')}</span>
                ) : (
                  <span className="badge badge-ghost badge-md font-bold uppercase px-3">{t('empty')}</span>
                )}
              </div>
              
              {strategyConfig ? (
                <div className="relative group flex-1 overflow-hidden rounded-lg border border-base-300 bg-base-200">
                  <pre className="h-full w-full overflow-auto p-5 text-xs font-mono text-base-content/80 custom-scrollbar">
                    {JSON.stringify(strategyConfig, null, 2)}
                  </pre>
                  <button 
                    onClick={handleEdit}
                    className="absolute top-3 right-3 btn btn-xs btn-neutral opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
                  >
                    {t('edit')}
                  </button>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center bg-base-200/50 rounded-lg border border-dashed border-base-300">
                  <p className="text-sm text-base-content/60">{t('noStrategy')}</p>
                  <button onClick={handleCreateNew} className="mt-3 btn btn-sm btn-primary">
                    {t('openWizard')}
                  </button>
                </div>
              )}
            </div>

            {/* 2. Parameters Card */}
            <div className="bg-base-100 rounded-xl border border-base-300 p-5 shadow-sm space-y-4">
              <h3 className="font-semibold text-lg mb-2">{t('backtestSettings')}</h3>
              
              <div>
                <label className="block text-sm font-medium text-base-content/60 mb-1">{t('stockSymbol')}</label>
                <div className="relative">
                  <input 
                    type="text" 
                    value={symbol}
                    onChange={handleSymbolChange}
                    onBlur={() => checkStock(symbol)} // Keep onBlur as a safety net
                    maxLength={6}
                    className={`input input-bordered w-full font-mono ${!isValidStock ? 'input-error' : ''}`}
                    placeholder="e.g. 600519"
                  />
                  {isValidating && <span className="absolute right-3 top-3 loading loading-spinner loading-xs text-base-content/40"></span>}
                </div>
                
                {/* Validation Feedback */}
                <div className="h-5 mt-1">
                  {!isValidStock && (
                    <p className="text-xs text-error">Invalid Stock Code</p>
                  )}
                  {isValidStock && stockName && (
                    <p className="text-xs text-success flex items-center">
                      ✓ {stockName}
                    </p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-base-content/60 mb-1">{t('startDate')}</label>
                  <input 
                    type="date" 
                    value={startDate}
                    min="1990-01-01"
                    max={today}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="input input-bordered w-full font-mono text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-base-content/60 mb-1">{t('endDate')}</label>
                  <input 
                    type="date" 
                    value={endDate}
                    min="1990-01-01"
                    max={today}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="input input-bordered w-full font-mono text-sm"
                  />
                </div>
              </div>

              <button
                onClick={runBacktest}
                disabled={!strategyConfig || isRunning || !isValidStock || isValidating || symbol.length !== 6}
                className="btn btn-neutral w-full mt-4"
              >
                {isRunning ? t('running') : t('runBacktest')}
              </button>
            </div>
          </div>

          {/* Right Column: Results */}
          <div className="lg:col-span-2 flex flex-col space-y-6">
            
            {/* 1. Result Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <ResultCard 
                label={t('finalEquity')} 
                value={result ? result.final_equity?.toFixed(2) : '-'}
                subValue={result ? `Initial: 100,000` : ''}
                trend={result && result.final_equity > 100000 ? 'up' : (result && result.final_equity < 100000 ? 'down' : 'neutral')}
              />
              <ResultCard 
                label={t('returnPct')} 
                value={result ? `${((result.final_equity - 100000)/1000).toFixed(2)}%` : '-'}
                trend={result && result.final_equity > 100000 ? 'up' : (result && result.final_equity < 100000 ? 'down' : 'neutral')}
              />
              {/* Win Rate Card (New) */}
              <div className="bg-base-100 rounded-xl border border-base-300 p-5 shadow-sm flex flex-col justify-between">
                 <div>
                    <p className="text-xs font-medium text-base-content/60 uppercase tracking-wider mb-1">Win Rate</p>
                    <p className="text-2xl font-bold text-base-content">
                        {result?.report ? `${(result.report.win_rate * 100).toFixed(0)}%` : '-'}
                    </p>
                 </div>
                 {result?.report && (
                    <button 
                        onClick={handleDiagnose}
                        className="mt-2 btn btn-accent btn-sm w-full font-bold uppercase tracking-wide gap-1"
                    >
                        <span className="text-lg">🩺</span> AI Diagnose
                    </button>
                 )}
              </div>
            </div>

            {/* 2. Logs Console */}
            <div className="h-[400px] bg-neutral text-neutral-content rounded-xl border border-neutral p-4 flex flex-col">
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-neutral-content/60 uppercase tracking-wider">{t('logs')}</span>
                    <span className="badge badge-xs badge-ghost text-[10px] text-neutral-content/40">Trade Only</span>
                </div>
                <span className="text-xs text-neutral-content/60">stdout</span>
              </div>
              <div className="flex-1 overflow-y-auto font-mono text-xs custom-scrollbar">
                {logs ? (
                    logs.split('\n')
                    .filter(line => {
                        // Filter logic: Show only EXEC, BUY, SELL, PnL, ERROR, Completed, or lines starting with [date] that contain trade info
                        const l = line.toUpperCase();
                        const isTradeInfo = l.includes('EXEC') || l.includes('BUY') || l.includes('SELL') || 
                                          l.includes('PNL') || l.includes('ERROR') || l.includes('COMPLETED') ||
                                          l.includes('✅') || l.includes('❌');
                        
                        // Explicitly hide the raw JSON result line
                        const isJsonResult = line.includes('"status": "success"') || line.includes('equity_curve');
                        
                        return isTradeInfo && !isJsonResult;
                    })
                    .map((line, i) => (
                        <div key={i} className={`whitespace-pre-wrap mb-0.5 ${
                            line.includes('✅') ? 'text-success' : 
                            (line.includes('❌') || line.includes('ERROR')) ? 'text-error' : 
                            'text-neutral-content/80'
                        }`}>
                            {line}
                        </div>
                    ))
                ) : (
                    <span className="text-neutral-content/40">// {t('waitingLogs')}</span>
                )}
              </div>
            </div>

            {/* 3. Equity Curve Chart */}
            {result?.equity_curve && (
              <div className="bg-base-100 rounded-xl border border-base-300 p-5 shadow-sm h-[380px]">
                <h3 className="font-semibold text-lg mb-4 text-base-content/80">资金曲线</h3>
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={result.equity_curve.map((item: any) => ({
                      ...item,
                      yield: parseFloat(((item.equity - 100000) / 1000).toFixed(2)) // Ensure number for auto-scaling
                    }))}>
                      <defs>
                        <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#8884d8" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} strokeOpacity={0.2} />
                      <XAxis 
                        dataKey="date" 
                        tick={{fontSize: 10, fill: '#666'}} 
                        tickFormatter={(val) => val.slice(5)} // Show MM-DD
                        minTickGap={30}
                      />
                      <YAxis 
                        yAxisId="left"
                        domain={['auto', 'auto']}
                        tick={{fontSize: 10, fill: '#666'}}
                        tickFormatter={(val) => `${(val/10000).toFixed(1)}万`}
                        width={45}
                      />
                      <YAxis 
                        yAxisId="right"
                        orientation="right"
                        domain={['auto', 'auto']}
                        tick={{fontSize: 10, fill: '#666'}}
                        tickFormatter={(val) => `${val}%`}
                        width={35}
                      />
                      <Tooltip 
                        contentStyle={{ 
                            backgroundColor: 'var(--color-base-100)', 
                            borderColor: 'var(--color-base-300)',
                            borderRadius: '0.5rem'
                        }}
                        itemStyle={{ color: 'var(--color-base-content)' }}
                        formatter={(value: any, name: string) => {
                          if (name === 'yield') return [`${value}%`, '收益率'];
                          return [`¥${Number(value).toFixed(2)}`, '资金'];
                        }}
                        labelFormatter={(label) => `日期: ${label}`}
                      />
                      <Area 
                        yAxisId="left"
                        type="monotone" 
                        dataKey="equity" 
                        stroke="#8884d8" 
                        fillOpacity={1} 
                        fill="url(#colorEquity)" 
                        strokeWidth={2}
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="yield"
                        stroke="#f59e0b" // Warning/Amber color for contrast
                        strokeWidth={2}
                        dot={false}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Modal Wizard */}
      <AIStrategyWizard 
        isOpen={isWizardOpen} 
        onClose={() => setIsWizardOpen(false)} 
        onApply={handleStrategyApply}
        diagnosisContext={diagnosisContext}
        userIntent={userIntent}
        history={chatHistory}
        onHistoryChange={setChatHistory}
        onUserQuery={setUserIntent}
      />
    </div>
  );
}

// Simple Stat Component
function ResultCard({ label, value, subValue, trend }: { label: string, value: string | number, subValue?: string, trend: 'up' | 'down' | 'neutral' }) {
  const color = trend === 'up' ? 'text-success' : (trend === 'down' ? 'text-error' : 'text-base-content');
  return (
    <div className="bg-base-100 rounded-xl border border-base-300 p-5 shadow-sm">
      <p className="text-xs font-medium text-base-content/60 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      {subValue && <p className="text-xs text-base-content/40 mt-1">{subValue}</p>}
    </div>
  );
}