'use client';

import React, { useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';
import { useSession } from 'next-auth/react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Copy, Check, Clock, TrendingUp, BarChart2, History } from 'lucide-react';
import Link from 'next/link';

export default function SessionDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { data: session } = useSession();
  
  const [sessionData, setSessionData] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      if (!id || !session?.user?.uuid) return;

      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_KEY!
      );

      // 1. Fetch Session Info
      const { data: sData, error: sError } = await supabase
        .from('backtest_sessions')
        .select('*')
        .eq('id', id)
        .single();

      if (sError || !sData) {
        console.error('Session not found');
        return;
      }
      setSessionData(sData);

      // 2. Fetch Runs History
      const { data: rData, error: rError } = await supabase
        .from('backtest_runs')
        .select('*')
        .eq('session_id', id)
        .order('created_at', { ascending: false });

      if (rData) {
        setRuns(rData);
      }
      setLoading(false);
    }

    fetchData();
  }, [id, session]);

  const copyConfig = (config: any, runId: string) => {
    navigator.clipboard.writeText(JSON.stringify(config, null, 2));
    setCopiedId(runId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading) {
    return <div className="p-8 flex justify-center"><span className="loading loading-spinner loading-lg"></span></div>;
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <Link href="/backtest-records" className="text-sm text-base-content/50 hover:text-primary flex items-center gap-1">
          <ArrowLeft className="size-4" /> Back to Records
        </Link>
        
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold">{sessionData.name}</h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-base-content/60">
              <span className="flex items-center gap-1">
                <Clock className="size-3" />
                Created {new Date(sessionData.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
          {/* Button removed */}
        </div>
      </div>

      {/* Timeline / List */}
      <div className="space-y-6 relative border-l-2 border-base-300 ml-4 pl-8 pb-10">
        {runs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 bg-base-100 rounded-xl border border-dashed border-base-300 ml-[-20px]">
            <div className="bg-base-200 p-4 rounded-full mb-4">
               <History className="size-8 text-base-content/30" />
            </div>
            <h3 className="text-lg font-semibold text-base-content/80">暂无回测记录</h3>
            <p className="text-base-content/50 text-sm mt-1 max-w-xs text-center">
              该策略尚未进行过回测。请返回策略工场加载配置并运行回测。
            </p>
            {sessionData.strategy_config && (
              <button 
                 onClick={() => copyConfig(sessionData.strategy_config, 'session-config')}
                 className="mt-4 btn btn-sm btn-neutral gap-2"
              >
                 {copiedId === 'session-config' ? <Check className="size-3" /> : <Copy className="size-3" />}
                 复制策略配置
              </button>
            )}
          </div>
        ) : (
          runs.map((run, index) => {
          const isLatest = index === 0;
          const returnVal = parseFloat(run.return_pct);
          const isPositive = returnVal >= 0;
          const winRate = (run.win_rate * 100).toFixed(0);

          return (
            <div key={run.id} className="relative">
              {/* Timeline Dot */}
              <div className={`absolute -left-[41px] top-6 size-5 rounded-full border-4 border-base-100 ${
                isLatest ? 'bg-primary ring-4 ring-primary/20' : 'bg-base-300'
              }`} />

              <div className={`card bg-base-100 border transition-all duration-200 ${
                isLatest ? 'border-primary shadow-md' : 'border-base-300 hover:border-base-content/30'
              }`}>
                <div className="card-body p-5">
                  
                  {/* Top Row: Meta & Actions */}
                  <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center gap-3">
                      <span className={`badge ${isLatest ? 'badge-primary font-bold' : 'badge-neutral badge-outline font-mono'} mr-2 px-3 py-1`}>
                        {isLatest ? 'LATEST' : `V${runs.length - index}`}
                      </span>
                      {isLatest && <span className="text-xs font-mono font-bold text-primary">V{runs.length - index}</span>}
                      
                      {run.stock_code && (
                        <span className="badge badge-neutral badge-sm font-mono font-bold px-2">
                            {run.stock_code}
                        </span>
                      )}
                      <span className="text-xs text-base-content/40 font-mono">
                        {new Date(run.created_at).toLocaleString()}
                      </span>
                    </div>
                    <button 
                      onClick={() => copyConfig(run.strategy_config, run.id)}
                      className="btn btn-ghost btn-xs gap-2"
                    >
                      {copiedId === run.id ? <Check className="size-3 text-success" /> : <Copy className="size-3" />}
                      {copiedId === run.id ? 'Copied' : 'Copy JSON'}
                    </button>
                  </div>

                  <div className="flex flex-col md:flex-row gap-6">
                    {/* Left: KPIs */}
                    <div className="flex-1 grid grid-cols-2 gap-4">
                      <div className="bg-base-200/50 rounded-lg p-3">
                        <div className="text-xs text-base-content/50 uppercase tracking-wider mb-1">Return</div>
                        <div className={`text-xl font-bold ${isPositive ? 'text-success' : 'text-error'}`}>
                          {returnVal > 0 ? '+' : ''}{returnVal}%
                        </div>
                      </div>
                      <div className="bg-base-200/50 rounded-lg p-3">
                        <div className="text-xs text-base-content/50 uppercase tracking-wider mb-1">Win Rate</div>
                        <div className="text-xl font-bold">{winRate}%</div>
                        <progress className={`progress w-full h-1 mt-2 ${isPositive ? 'progress-success' : 'progress-warning'}`} value={winRate} max="100"></progress>
                      </div>
                      <div className="bg-base-200/50 rounded-lg p-3">
                        <div className="text-xs text-base-content/50 uppercase tracking-wider mb-1">Trades</div>
                        <div className="text-xl font-bold">{run.total_trades}</div>
                      </div>
                      <div className="bg-base-200/50 rounded-lg p-3">
                        <div className="text-xs text-base-content/50 uppercase tracking-wider mb-1">Final Equity</div>
                        <div className="text-xl font-bold">¥{(run.final_equity / 10000).toFixed(1)}w</div>
                      </div>
                    </div>

                    {/* Right: Config Preview */}
                    <div className="flex-1 bg-neutral text-neutral-content rounded-lg p-4 font-mono text-xs overflow-hidden h-64 relative group">
                      <div className="absolute top-2 right-2 text-neutral-content/30 text-[10px] uppercase">Config Preview</div>
                      <pre className="opacity-80 h-full overflow-auto custom-scrollbar">
                        {JSON.stringify(run.strategy_config, null, 2)}
                      </pre>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          );
        }))}
      </div>
    </div>
  );
}
