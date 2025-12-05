'use client';

import { useState } from 'react';
import { createClient } from '@supabase/supabase-js';
import { useRouter } from 'next/navigation';
import { Rocket } from 'lucide-react';

export default function BacktestPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [symbol, setSymbol] = useState('600519'); // Default to Moutai
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState(new Date().toISOString().slice(0, 10));
  const [initialCash, setInitialCash] = useState(100000);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_KEY!
      );

      // 1. Get current user
      const { data: { user } } = await supabase.auth.getUser();
      
      // Note: In a real app, you should probably validate the user is logged in.
      // For this demo, we'll proceed. If user is null, user_id might be null or we use a placeholder.
      
      // 2. Create a new run entry
      const { data, error } = await supabase
        .from('runs')
        .insert([
          {
            user_id: user?.id || 'anonymous', // Or handle auth check strictly
            stock_code: symbol,
            start_date: startDate,
            end_date: endDate,
            status: 'pending',
            strategy_config: {
              initial_cash: initialCash,
              model_name: 'deepseek-chat' // Default for now
            }
          }
        ])
        .select()
        .single();

      if (error) throw error;

      // 3. Redirect to a status/result page (or just stay here and show list)
      // For now, let's go to the trading view of that stock which we optimized earlier,
      // though ideally we'd have a "Run Detail" page. 
      // But since our TradingPage reads from trades table by symbol, it might mix data if we don't filter by run_id.
      // **Crucial Note**: Our current TradingPage (/trading/[stock_code]) reads ALL trades for a symbol.
      // It doesn't yet filter by `run_id`. To see THIS specific backtest, we'd need to update that page too.
      // For MVP, let's just alert success and maybe clear form.
      
      alert(`Job created! Run ID: ${data.run_id}`);
      
    } catch (err: any) {
      alert('Error creating job: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto py-10 max-w-2xl">
      <div className="card bg-base-100 shadow-xl border border-base-200">
        <div className="card-body">
          <h2 className="card-title text-2xl mb-6 flex items-center gap-2">
            <Rocket className="size-6 text-primary" />
            Create Backtest Job
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="form-control">
              <label className="label">
                <span className="label-text">Stock Symbol</span>
              </label>
              <input 
                type="text" 
                placeholder="e.g. 600519" 
                className="input input-bordered" 
                value={symbol}
                onChange={e => setSymbol(e.target.value)}
                required
              />
              <div className="label">
                <span className="label-text-alt text-base-content/60">A-Share code without suffix</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="form-control">
                <label className="label">
                  <span className="label-text">Start Date</span>
                </label>
                <input 
                  type="date" 
                  className="input input-bordered"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  required
                />
              </div>
              
              <div className="form-control">
                <label className="label">
                  <span className="label-text">End Date</span>
                </label>
                <input 
                  type="date" 
                  className="input input-bordered"
                  value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text">Initial Capital (CNY)</span>
              </label>
              <input 
                type="number" 
                className="input input-bordered"
                value={initialCash}
                onChange={e => setInitialCash(Number(e.target.value))}
                min={10000}
                step={10000}
              />
            </div>

            <div className="card-actions justify-end mt-6">
              <button 
                type="submit" 
                className={`btn btn-primary w-full ${loading ? 'btn-disabled' : ''}`}
              >
                {loading ? <span className="loading loading-spinner"></span> : 'Start Backtest'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
