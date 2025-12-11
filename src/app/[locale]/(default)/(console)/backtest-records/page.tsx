'use client';

import React, { useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';
import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { ChevronRight, Calendar, TrendingUp, History, BarChart2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

export default function BacktestRecordsPage() {
  const t = useTranslations('Backtest');
  const { data: session } = useSession();
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchRecords() {
      if (!session?.user?.uuid) return;

      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_KEY!
      );

      const { data: sessionsData, error } = await supabase
        .from('backtest_sessions')
        .select('*')
        .eq('user_id', session.user.uuid)
        .order('updated_at', { ascending: false });

      if (error) {
        console.error('Error fetching sessions:', error);
        setLoading(false);
        return;
      }

      if (!sessionsData || sessionsData.length === 0) {
        setSessions([]);
        setLoading(false);
        return;
      }

      const sessionIds = sessionsData.map(s => s.id);
      
            const { data: runsData } = await supabase
              .from('backtest_runs')
              .select('session_id, return_pct, win_rate, total_trades, created_at, stock_code')
              .in('session_id', sessionIds)
              .order('created_at', { ascending: false }); // Latest first
      
            // Map runs to sessions
            const enrichedSessions = sessionsData.map(sess => {
              // Find the FIRST run that matches this session_id (since runs are ordered desc)
              const latestRun = runsData?.find(r => r.session_id === sess.id);
              const runCount = runsData?.filter(r => r.session_id === sess.id).length || 0;
              
              return {
                ...sess,
                latestRun,
                runCount
              };
            });
      
            setSessions(enrichedSessions);
            setLoading(false);
          }
      
          fetchRecords();
        }, [session]);
      
        if (loading) {
          return <div className="p-8 flex justify-center"><span className="loading loading-spinner loading-lg"></span></div>;
        }
      
        return (
          <div className="p-6 max-w-5xl mx-auto space-y-6">
            <div className="flex justify-between items-center">
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <History className="size-6 text-primary" />
                {t('recordsTitle')}
              </h1>
              <Link href="/backtest" className="btn btn-primary btn-sm">
                + {t('createStrategy')}
              </Link>
            </div>
      
            <div className="bg-base-100 rounded-xl border border-base-300 shadow-sm overflow-hidden">
              {sessions.length === 0 ? (
                <div className="p-12 text-center flex flex-col items-center">
                  <div className="bg-base-200 p-4 rounded-full mb-4">
                     <BarChart2 className="size-8 text-base-content/30" />
                  </div>
                  <h3 className="text-lg font-semibold text-base-content/80">{t('emptyRecords')}</h3>
                  <p className="text-base-content/50 text-sm mt-1 mb-4">
                     {t('noContent')}
                  </p>
                  <Link href="/backtest" className="btn btn-neutral btn-sm">{t('createStrategy')}</Link>
                </div>
              ) : (
                <div className="flex flex-col">
                  {sessions.map((item, index) => {
                    const hasRun = !!item.latestRun;
                    const returnVal = hasRun ? parseFloat(item.latestRun.return_pct) : 0;
                    const isPositive = returnVal >= 0;
                    const winRate = hasRun ? (item.latestRun.win_rate * 100).toFixed(0) : 0;
                    const displaySymbol = (hasRun && item.latestRun.stock_code) ? item.latestRun.stock_code : item.symbol;
      
                                  return (
      
                                    <Link 
      
                                      key={item.id} 
      
                                      href={`/backtest-records/${item.id}`}
      
                                      className={`group flex flex-col md:flex-row md:items-center justify-between p-5 hover:bg-base-200/50 transition-colors ${
      
                                        index !== sessions.length - 1 ? 'border-b border-base-200' : ''
      
                                      }`}
      
                                    >
      
                                      {/* Left: Identity */}
      
                                      <div className="flex items-start gap-4 mb-4 md:mb-0 flex-1 min-w-0 pr-4">
      
                                        <div className="flex flex-col items-center gap-1 min-w-[60px] flex-shrink-0">
      
                                            <span className="badge badge-lg badge-neutral font-mono font-bold px-3 py-1">{displaySymbol}</span>
      
                                            <span className="text-[10px] text-base-content/40 font-mono">
      
                                                {new Date(item.created_at).toLocaleDateString()}
      
                                            </span>
      
                                        </div>
      
                                        <div className="min-w-0">
      
                                            <h3 className="font-semibold text-base-content group-hover:text-primary transition-colors truncate">
      
                                                {item.name || 'Untitled Strategy'}
      
                                            </h3>
      
                                            <div className="flex items-center gap-2 mt-1.5">
      
                                                 <span className="text-xs text-base-content/50 flex items-center gap-1">
      
                                                    <History className="size-3" />
      
                                                    {item.runCount} Runs
      
                                                 </span>
      
                                                 {hasRun && (
      
                                                    <span className="text-xs text-base-content/40">
      
                                                       • Last: {new Date(item.latestRun.created_at).toLocaleTimeString()}
      
                                                    </span>
      
                                                 )}
      
                                            </div>
      
                                        </div>
      
                                      </div>
      
                    
      
                                      {/* Right: Metrics */}
      
                                      <div className="flex items-center gap-6 md:gap-12 flex-shrink-0">
      
                                        {hasRun ? (
      
                                            <>
      
                                               <div className="flex flex-col items-end min-w-[80px]">
      
                                                    <span className="text-xs text-base-content/40 uppercase tracking-wider mb-0.5">{t('returnPct')}</span>
      
                                                    <span className={`text-lg font-bold font-mono ${isPositive ? 'text-success' : 'text-error'}`}>
      
                                                        {returnVal > 0 ? '+' : ''}{returnVal}%
      
                                                    </span>
      
                                               </div>
      
                                                                          <div className="flex flex-col items-end min-w-[80px]">
      
                                                                               <span className="text-xs text-base-content/40 uppercase tracking-wider mb-0.5">{t('winRate')}</span>
      
                                                                               <div className="flex items-center gap-2">
      
                                                                                   <span className="font-bold text-base-content/80 text-lg font-mono">{winRate}%</span>
      
                                                                               </div>
      
                                                                          </div>
      
                                            </>
      
                                        ) : (
      
                                            <span className="text-sm text-base-content/40 italic pr-8">Pending Run</span>
      
                                        )}
      
                                      </div>
      
                                      
      
                                      <ChevronRight className="size-5 text-base-content/20 group-hover:text-base-content/60 transition-colors flex-shrink-0 ml-4 hidden md:block" />
      
                                    </Link>
      
                                  );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
