'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { createClient } from '@supabase/supabase-js';
import { useRouter } from 'next/navigation';
import { 
  Rocket, List, Play, CircleStop, Trash2, Clock, Calendar, 
  Sparkles, Brain, Activity, Search, ArrowRight, Plus, X, CheckCircle2, AlertCircle, Banknote, Bot, ChevronRight
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';
import { useSession } from "next-auth/react";

export default function BacktestDashboard() {
  const t = useTranslations('Backtest');
  const router = useRouter();
  const { data: session, status } = useSession();
  const [loading, setLoading] = useState(false);
  
  // Form State
  const [symbol, setSymbol] = useState('600519');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [model, setModel] = useState('deepseek-chat');
  
  const getYesterday = () => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().slice(0, 10);
  };
  const [endDate, setEndDate] = useState(getYesterday());
  const [initialCash, setInitialCash] = useState(100000);
  const [estimatedDays, setEstimatedDays] = useState<number | null>(null);
  
  // Strategy State
  const [strategyPrompt, setStrategyPrompt] = useState('');
  const [wizardInput, setWizardInput] = useState('');
  const [wizardModel, setWizardModel] = useState('deepseek-chat');
  const [wizardLoading, setWizardLoading] = useState(false);
  const [wizardResult, setWizardResult] = useState('');
  const [wizardReasoning, setWizardReasoning] = useState('');
  const abortControllerRef = useRef<AbortController | null>(null);

  // Estimate trading days
  useEffect(() => {
    if (startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      if (start > end) {
        setEstimatedDays(0);
        return;
      }
      let count = 0;
      const cur = new Date(start);
      if (isNaN(cur.getTime()) || isNaN(end.getTime())) return;
      while (cur <= end) {
        const day = cur.getDay();
        if (day !== 0 && day !== 6) count++;
        cur.setDate(cur.getDate() + 1);
      }
      if (count > 10) setEstimatedDays(Math.floor(count * 0.95));
      else setEstimatedDays(count);
    }
  }, [startDate, endDate]);

  const handleQuickSelect = (months: number) => {
    const end = new Date();
    end.setDate(end.getDate() - 1);
    const start = new Date();
    start.setDate(start.getDate() - 1);
    start.setMonth(start.getMonth() - months);
    setEndDate(end.toISOString().slice(0, 10));
    setStartDate(start.toISOString().slice(0, 10));
  };

  const handleGenerateStrategy = async () => {
    if (!wizardInput.trim()) return;
    if (abortControllerRef.current) abortControllerRef.current.abort();
    
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setWizardLoading(true);
    setWizardReasoning('');
    try {
      const res = await fetch('/api/generate-strategy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: wizardInput, model: wizardModel }),
        signal: controller.signal
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setWizardResult(data.result);
      setWizardReasoning(data.reasoning || '');
    } catch (e: any) {
      if (e.name !== 'AbortError') toast.error(e.message);
    } finally {
      if (abortControllerRef.current === controller) {
         setWizardLoading(false);
         abortControllerRef.current = null;
      }
    }
  };

  const handleCancelGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setWizardLoading(false);
      toast.info('Cancelled');
    }
  };

  const applyStrategy = () => {
    setStrategyPrompt(wizardResult);
    setModel(wizardModel);
    (document.getElementById('strategy_modal') as HTMLDialogElement)?.close();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^\d{6}$/.test(symbol)) {
      toast.error(t('validation_error'));
      return;
    }
    const start = new Date(startDate);
    const end = new Date(endDate);
    if (start >= end) {
      toast.error("Start date must be before end date.");
      return;
    }
    
    if (initialCash < 5000 || initialCash > 1000000) {
      toast.error("Invalid Capital");
      return;
    }

    if (status !== 'authenticated' || !session?.user) {
      toast.info(t('loginRequired') || "Please login first");
      router.push('/auth/signin?callbackUrl=/backtest');
      return;
    }

    setLoading(true);

    try {
      const valRes = await fetch(`/api/validate/stock?code=${symbol}`);
      const valData = await valRes.json();
      if (!valData.valid) {
        toast.error(`Invalid Stock: ${valData.reason || 'Code not found'}`);
        setLoading(false);
        return;
      }
      if (valData.name) toast.success(`Selected: ${valData.name} (${symbol})`);
    } catch (e) {
      setLoading(false);
      return;
    }

    try {
      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_KEY!
      );

      const { error } = await supabase
        .from('runs')
        .insert([{
            user_id: (session.user as any).uuid || session.user.email,
            stock_code: symbol,
            start_date: startDate,
            end_date: endDate,
            status: 'pending',
            strategy_config: {
              initial_cash: initialCash,
              model_name: model,
              system_prompt: strategyPrompt
            }
          }]);

      if (error) throw error;
      toast.success(`Job created!`);
    } catch (err: any) {
      toast.error('Error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-base-100/50">
      <div className="container mx-auto py-12 px-6 max-w-7xl">
        
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-base-content flex items-center gap-3">
              <Activity className="size-8 text-primary" strokeWidth={1.5} />
              {t('title')}
            </h1>
            <p className="text-base-content/60 mt-2 font-light">Configure and launch your AI trading simulation.</p>
          </div>
          
          <div className="flex gap-3">
             <button 
              className="btn btn-outline gap-2 border-base-300 hover:bg-base-200 hover:border-base-400 transition-all"
              onClick={() => (document.getElementById('strategy_modal') as HTMLDialogElement)?.showModal()}
            >
              <Sparkles className="size-4 text-primary" />
              AI Strategy Wizard
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-12 gap-10">
          
          {/* Left Column: Configuration Form */}
          <div className="xl:col-span-4 space-y-8">
            <div className="card bg-base-100 border border-base-200 shadow-sm hover:shadow-md transition-shadow duration-300 rounded-2xl overflow-hidden">
              <div className="card-body p-8 gap-8">
                
                <form onSubmit={handleSubmit} className="flex flex-col gap-8">
                  
                  {/* Strategy Active Indicator */}
                  {strategyPrompt && (
                    <div className="flex items-center justify-between bg-primary/5 border border-primary/10 px-4 py-3 rounded-lg">
                      <div className="flex items-center gap-2 text-sm text-primary font-medium">
                        <Brain className="size-4" />
                        <span>{t('strategyActive')}</span>
                      </div>
                      <button 
                        type="button" 
                        className="btn btn-xs btn-circle btn-ghost opacity-60 hover:opacity-100" 
                        onClick={() => setStrategyPrompt('')}
                      >
                        <X className="size-3" />
                      </button>
                    </div>
                  )}

                  {/* Stock Symbol */}
                  <div className="form-control w-full">
                    <label className="label px-0 pt-0 mb-2">
                      <span className="label-text font-semibold text-base text-base-content">{t('stockSymbol')}</span>
                    </label>
                    <div className="relative">
                      <input 
                        type="text" 
                        placeholder="e.g. 600519" 
                        className="input input-bordered w-full px-4 font-mono text-base tracking-wide bg-base-50 focus:bg-base-100 transition-all h-11 rounded-lg border-base-300 focus:border-primary shadow-sm placeholder:text-base-content/20" 
                        value={symbol}
                        onChange={e => setSymbol(e.target.value)}
                        required
                        maxLength={6}
                      />
                    </div>
                    <div className="label px-0 pb-0 mt-2">
                      <span className="label-text-alt text-base-content/50 flex items-center gap-1">
                        <AlertCircle className="size-3" /> {t('stockSymbolHint')}
                      </span>
                    </div>
                  </div>

                  {/* Date Range */}
                  <div className="space-y-3">
                    <label className="label px-0 pt-0 justify-between mb-2">
                      <span className="label-text font-semibold text-base text-base-content">{t('dateRange')}</span>
                      {estimatedDays !== null && (
                        <span className="text-xs font-mono text-base-content/50 flex items-center gap-1 bg-base-200/50 px-2 py-1 rounded-md">
                          <Clock className="size-3" />
                          {estimatedDays} days
                        </span>
                      )}
                    </label>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div className="form-control relative">
                        <input 
                          type="date" 
                          className="input input-bordered w-full px-4 text-sm font-mono bg-base-50 focus:bg-base-100 h-10 rounded-lg border-base-300 focus:border-primary shadow-sm transition-all"
                          value={startDate}
                          onChange={e => setStartDate(e.target.value)}
                          required
                        />
                      </div>
                      <div className="form-control relative">
                        <input 
                          type="date" 
                          className="input input-bordered w-full px-4 text-sm font-mono bg-base-50 focus:bg-base-100 h-10 rounded-lg border-base-300 focus:border-primary shadow-sm transition-all"
                          value={endDate}
                          onChange={e => setEndDate(e.target.value)}
                          required
                        />
                      </div>
                    </div>

                    <div className="flex gap-2 pt-1">
                      {[3, 6, 12, 36].map(m => (
                        <button 
                          key={m}
                          type="button" 
                          className="btn btn-xs btn-ghost border border-base-200 font-normal hover:border-primary hover:text-primary transition-all flex-1" 
                          onClick={() => handleQuickSelect(m)}
                        >
                          {m}M
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Model Selection */}
                  <div className="form-control w-full">
                    <label className="label px-0 pt-0 mb-2">
                      <span className="label-text font-semibold text-base text-base-content">{t('wizardModelLabel')}</span>
                    </label>
                    <div className="relative">
                      <select 
                        className="select select-bordered w-full px-4 bg-base-50 focus:bg-base-100 h-11 rounded-lg font-normal text-base border-base-300 focus:border-primary shadow-sm transition-all"
                        value={model}
                        onChange={e => setModel(e.target.value)}
                      >
                        <option value="deepseek-chat">⚡️ {t('modelChat')}</option>
                        <option value="deepseek-reasoner">🧠 {t('modelReasoner')}</option>
                      </select>
                    </div>
                  </div>

                  {/* Capital */}
                  <div className="form-control w-full">
                    <label className="label px-0 pt-0 mb-2">
                      <span className="label-text font-semibold text-base text-base-content">{t('capital')}</span>
                    </label>
                    <div className="relative">
                      <input 
                        type="number" 
                        className="input input-bordered w-full px-4 font-mono text-base tracking-wide bg-base-50 focus:bg-base-100 h-11 rounded-lg border-base-300 focus:border-primary shadow-sm transition-all [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                        value={initialCash}
                        onChange={e => setInitialCash(Number(e.target.value))}
                        min={5000}
                        max={1000000}
                        step={1000}
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-base-content/40 font-mono text-sm pointer-events-none">CNY</span>
                    </div>
                    <div className="label px-0 pb-0 mt-2">
                      <span className="label-text-alt text-base-content/50">{t('capitalHint')}</span>
                    </div>
                  </div>

                  <div className="pt-6">
                    <button 
                      type="submit" 
                      className={`btn btn-primary w-full h-12 rounded-lg text-base font-bold tracking-wide shadow-lg shadow-primary/20 hover:shadow-primary/40 hover:-translate-y-0.5 transition-all duration-300 ${loading ? 'btn-disabled' : ''}`}
                    >
                      {loading ? <span className="loading loading-dots loading-md"></span> : (
                        <span className="flex items-center gap-2">
                          {t('submit')} <ArrowRight className="size-5" />
                        </span>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>

          {/* Right Column: Run List */}
          <div className="xl:col-span-8">
             <RunList />
          </div>

        </div>

        {/* Strategy Generator Modal */}
        <dialog id="strategy_modal" className="modal modal-bottom sm:modal-middle backdrop-blur-sm">
          <div className="modal-box w-full max-w-4xl p-0 bg-base-100 rounded-3xl border border-base-200 shadow-2xl overflow-hidden">
            
            {/* Modal Header */}
            <div className="flex justify-between items-center p-6 border-b border-base-100 bg-base-50/50">
              <h3 className="font-bold text-xl flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Sparkles className="text-primary size-5" />
                </div>
                {t('wizardTitle')}
              </h3>
              <form method="dialog">
                <button className="btn btn-sm btn-circle btn-ghost text-base-content/50 hover:bg-base-200">✕</button>
              </form>
            </div>

            <div className="p-8 max-h-[80vh] overflow-y-auto">
              {/* Loading State */}
              {wizardLoading ? (
                <div className="flex flex-col items-center justify-center py-20 space-y-6">
                  <div className="relative">
                    <div className="loading loading-ring loading-lg text-primary scale-150"></div>
                  </div>
                  <p className="text-base-content/60 font-medium animate-pulse">Crafting your strategy...</p>
                  <button className="btn btn-ghost btn-sm text-error/80 hover:bg-error/10" onClick={handleCancelGeneration}>
                    Cancel
                  </button>
                </div>
              ) : !wizardResult ? (
                /* Input State */
                <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  
                  <div className="alert bg-base-50 border-none text-sm py-3 px-4 text-base-content/70 flex items-start gap-3 rounded-xl">
                    <AlertCircle className="size-5 shrink-0 mt-0.5 text-info" />
                    <div>
                      <div className="font-semibold text-base-content mb-1">{t('wizardNoticeTitle')}</div>
                      <div className="leading-relaxed opacity-80">{t('wizardNoticeContent')}</div>
                    </div>
                  </div>

                  <div className="form-control">
                    <label className="label px-0 mb-2">
                      <span className="label-text font-medium text-lg">{t('wizardDescLabel')}</span>
                    </label>
                    <textarea 
                      className="textarea textarea-bordered w-full h-40 text-base leading-relaxed p-4 rounded-2xl focus:border-primary resize-none shadow-sm" 
                      placeholder={t('wizardDescPlaceholder')}
                      value={wizardInput}
                      onChange={e => setWizardInput(e.target.value)}
                    ></textarea>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-4 pt-2">
                    <div className="form-control flex-1">
                      <select 
                        className="select select-bordered w-full h-12 rounded-xl bg-base-50"
                        value={wizardModel}
                        onChange={e => setWizardModel(e.target.value)}
                      >
                        <option value="deepseek-chat">⚡️ {t('modelChat')}</option>
                        <option value="deepseek-reasoner">🧠 {t('modelReasoner')}</option>
                      </select>
                    </div>
                    <button 
                      className="btn btn-primary h-12 px-8 rounded-xl font-semibold shadow-lg shadow-primary/20 sm:w-auto w-full" 
                      onClick={handleGenerateStrategy}
                      disabled={!wizardInput.trim()}
                    >
                      <Sparkles className="size-5" /> {t('wizardGenerate')}
                    </button>
                  </div>
                </div>
              ) : (
                /* Result State */
                <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-right-8 duration-500">
                  {wizardReasoning && (
                    <div className="collapse collapse-arrow border border-base-200 bg-base-50 rounded-xl">
                      <input type="checkbox" /> 
                      <div className="collapse-title text-sm font-medium flex items-center gap-2">
                        <Brain className="size-4 text-secondary" /> Analysis Process
                      </div>
                      <div className="collapse-content text-xs font-mono opacity-80 leading-relaxed"> 
                        {wizardReasoning}
                      </div>
                    </div>
                  )}

                  <div className="form-control">
                    <div className="label px-0 mb-2 flex justify-between">
                      <span className="label-text font-medium text-lg">{t('wizardOutputLabel')}</span>
                      <div className="badge badge-neutral badge-outline badge-sm font-mono opacity-50">System Prompt</div>
                    </div>
                    <textarea 
                      className="textarea textarea-bordered w-full h-[400px] font-mono text-sm leading-relaxed p-4 rounded-2xl bg-base-50 focus:bg-base-100 transition-colors shadow-inner resize-none" 
                      value={wizardResult}
                      onChange={e => setWizardResult(e.target.value)}
                      placeholder={t('wizardOutputPlaceholder')}
                    ></textarea>
                  </div>
                  
                  <div className="flex gap-4 pt-2">
                    <button 
                      className="btn btn-ghost flex-1 h-12 rounded-xl border border-base-200 hover:border-base-300 hover:bg-base-100" 
                      onClick={() => setWizardResult('')}
                    >
                      Retry
                    </button>
                    <button 
                      className="btn btn-primary flex-[2] h-12 rounded-xl shadow-lg shadow-primary/20 font-semibold" 
                      onClick={applyStrategy}
                    >
                      {t('wizardApply')}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
          <form method="dialog" className="modal-backdrop">
            <button>close</button>
          </form>
        </dialog>

      </div>
    </div>
  );
}

function RunList() {
  const t = useTranslations('Backtest');
  const { data: session } = useSession();
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [viewStrategy, setViewStrategy] = useState<string>('');

  const supabase = useMemo(() => createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_KEY!
  ), []);

  const fetchRuns = async () => {
    if (!session?.user) {
      setLoading(false);
      return;
    }

    const userId = (session.user as any).uuid || session.user.email;
    const { data, error } = await supabase
      .from('runs')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(20);

    if (!error && data) {
      setRuns(data);
    }
    setLoading(false);
  };

  const handleAction = async (runId: string, action: 'stop' | 'delete' | 'resume') => {
    if (action === 'delete') {
      setDeleteId(runId);
      const modal = document.getElementById('delete_modal') as HTMLDialogElement;
      modal?.showModal();
    } else if (action === 'stop') {
      await supabase.from('runs').update({ status: 'stopped' }).eq('run_id', runId);
      fetchRuns();
    } else if (action === 'resume') {
      await supabase.from('runs').update({ status: 'pending' }).eq('run_id', runId);
      fetchRuns();
    }
  };

  const confirmDelete = async () => {
    if (!deleteId) return;
    await supabase.from('runs').update({ status: 'stopped' }).eq('run_id', deleteId);
    const { error } = await supabase.from('runs').delete().eq('run_id', deleteId);
    if (error) toast.error("Failed to delete: " + error.message);
    else toast.success("Record deleted");
    setDeleteId(null);
    (document.getElementById('delete_modal') as HTMLDialogElement)?.close();
    fetchRuns();
  };

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 3000);
    return () => clearInterval(interval);
  }, [session]);

  return (
    <div className="card bg-base-100 border border-base-200 shadow-sm rounded-2xl h-full flex flex-col">
      <div className="p-6 border-b border-base-100 flex justify-between items-center">
        <h2 className="text-xl font-bold text-base-content flex items-center gap-2">
          <List className="size-5 text-base-content/60" />
          {t('myRuns')}
        </h2>
        <button className="btn btn-ghost btn-sm btn-circle text-base-content/40 hover:text-primary" onClick={fetchRuns}>
          <Activity className="size-4" />
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        {loading && runs.length === 0 ? (
          <div className="flex justify-center py-20">
            <span className="loading loading-spinner loading-md text-base-content/20"></span>
          </div>
        ) : runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-base-content/40 gap-4">
            <div className="p-4 bg-base-200 rounded-full">
              <List className="size-8 opacity-50" />
            </div>
            <p className="font-medium">{t('noContent')}</p>
          </div>
        ) : (
          <table className="table table-lg w-full">
            <thead>
              <tr className="border-b border-base-100 text-base-content/40 text-xs uppercase tracking-wider">
                <th className="pl-8 bg-transparent font-medium">Status</th>
                <th className="bg-transparent font-medium">Asset</th>
                <th className="bg-transparent font-medium">AI Model</th>
                <th className="bg-transparent font-medium">Range</th>
                <th className="pr-8 text-right bg-transparent font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {runs.map((run) => (
                <tr key={run.run_id} className="group hover:bg-base-50 transition-colors border-b border-base-100 last:border-none">
                  <td className="pl-8 py-4">
                    <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium border ${
                      run.status === 'completed' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' :
                      run.status === 'running' ? 'bg-blue-50 text-blue-600 border-blue-100' :
                      run.status === 'failed' ? 'bg-red-50 text-red-600 border-red-100' :
                      'bg-gray-50 text-gray-600 border-gray-100'
                    }`}>
                      {run.status === 'running' && <span className="loading loading-spinner loading-xs opacity-70"></span>}
                      {run.status === 'completed' && <CheckCircle2 className="size-3" />}
                      <span className="capitalize">{run.status}</span>
                    </div>
                  </td>
                  <td className="py-4">
                    <div className="font-mono font-bold text-base-content/90">{run.stock_code || run.label?.split('_')[0]}</div>
                  </td>
                  <td className="py-4">
                    <div className="flex items-center gap-2">
                      {run.strategy_config?.system_prompt && (
                        <button 
                          className="btn btn-ghost btn-xs btn-square text-primary/70 hover:bg-primary/10"
                          onClick={() => {
                            setViewStrategy(run.strategy_config.system_prompt);
                            (document.getElementById('strategy_view_modal') as HTMLDialogElement)?.showModal();
                          }}
                          title="View Custom Strategy"
                        >
                          <Brain className="size-4" />
                        </button>
                      )}
                      <span className="text-xs font-medium text-base-content/60 bg-base-200 px-2 py-0.5 rounded">
                        {run.strategy_config?.model_name?.includes('reasoner') ? 'R1' : 'V3'}
                      </span>
                    </div>
                  </td>
                  <td className="py-4">
                    <div className="flex flex-col text-xs text-base-content/50 font-mono">
                      <span>{run.start_date}</span>
                      <span className="opacity-50">↓</span>
                      <span>{run.end_date}</span>
                    </div>
                  </td>
                  <td className="pr-8 py-4 text-right">
                    <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {run.status === 'completed' && (
                        <a 
                          href={`/trading/${run.stock_code || run.label?.split('_')[0]}?run_id=${run.run_id}`} 
                          className="btn btn-sm btn-ghost text-primary hover:bg-primary/10 gap-1 font-normal"
                          target="_blank"
                        >
                          View <ArrowRight className="size-3" />
                        </a>
                      )}
                      
                      {run.status === 'running' && (
                        <button 
                          className="btn btn-sm btn-square btn-ghost text-warning hover:bg-warning/10"
                          onClick={() => handleAction(run.run_id, 'stop')}
                        >
                          <CircleStop className="size-4" />
                        </button>
                      )}

                      {(run.status === 'stopped' || run.status === 'failed') && (
                        <button 
                          className="btn btn-sm btn-square btn-ghost text-success hover:bg-success/10"
                          onClick={() => handleAction(run.run_id, 'resume')}
                        >
                          <Play className="size-4" />
                        </button>
                      )}

                      <button 
                        className="btn btn-sm btn-square btn-ghost text-base-content/30 hover:text-error hover:bg-error/10"
                        onClick={() => handleAction(run.run_id, 'delete')}
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Strategy View Modal */}
      <dialog id="strategy_view_modal" className="modal backdrop-blur-sm">
        <div className="modal-box w-11/12 max-w-2xl bg-base-100 rounded-2xl border border-base-200 shadow-2xl">
          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
            <Brain className="text-primary size-5" /> Strategy Prompt
          </h3>
          <div className="bg-base-50 p-6 rounded-xl font-mono text-xs leading-relaxed whitespace-pre-wrap max-h-[60vh] overflow-y-auto border border-base-200 shadow-inner text-base-content/80">
            {viewStrategy}
          </div>
          <div className="modal-action mt-6">
            <form method="dialog">
              <button className="btn btn-ghost">Close</button>
            </form>
          </div>
        </div>
        <form method="dialog" className="modal-backdrop">
          <button>close</button>
        </form>
      </dialog>

      {/* Delete Confirmation Modal */}
      <dialog id="delete_modal" className="modal backdrop-blur-sm">
        <div className="modal-box bg-base-100 rounded-2xl border border-base-200 shadow-xl max-w-sm">
          <div className="flex flex-col items-center text-center gap-4 pt-4">
            <div className="p-3 bg-error/10 rounded-full text-error">
              <Trash2 className="size-8" />
            </div>
            <h3 className="font-bold text-lg">Delete Run?</h3>
            <p className="text-sm text-base-content/60 px-4">
              This action cannot be undone. All data associated with this run will be permanently removed.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 mt-8">
            <form method="dialog">
              <button className="btn btn-ghost w-full border border-base-200">Cancel</button>
            </form>
            <button className="btn btn-error text-white shadow-lg shadow-error/20" onClick={confirmDelete}>Delete</button>
          </div>
        </div>
        <form method="dialog" className="modal-backdrop">
          <button>close</button>
        </form>
      </dialog>
    </div>
  );
}
