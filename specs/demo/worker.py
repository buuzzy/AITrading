import time
import os
import sys
import requests
import json
from dotenv import load_dotenv
from core_backtest import execute_backtest_job

load_dotenv()

def _supabase_creds():
    url = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY') or os.getenv('NEXT_PUBLIC_SUPABASE_KEY')
    return url, key

def fetch_pending_job():
    url, key = _supabase_creds()
    if not url or not key:
        print("Missing Supabase credentials")
        return None
        
    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation' # Return the updated row
    }
    
    # 1. Find one pending job
    # We use a simple GET first to avoid locking issues in simple REST mode, 
    # or use RPC if we had one. Standard pattern: GET limit 1 -> PATCH status='running'
    
    try:
        get_res = requests.get(
            f"{url}/rest/v1/runs?status=eq.pending&limit=1&order=created_at.asc",
            headers=headers,
            timeout=10
        )
        if get_res.status_code != 200:
            return None
        
        jobs = get_res.json()
        if not jobs:
            return None
            
        job = jobs[0]
        run_id = job['run_id']
        
        # 2. Optimistically lock it (Update status to running)
        patch_res = requests.patch(
            f"{url}/rest/v1/runs?run_id=eq.{run_id}&status=eq.pending", # Safety check
            headers=headers,
            json={'status': 'running'},
            timeout=10
        )
        
        if patch_res.status_code == 200 or patch_res.status_code == 204:
            # If update successful (and returned row if representation), we own it
            # Check if we actually updated it (in case of race condition)
            # REST API with Prefer: return=representation returns the row if matched
            if patch_res.status_code == 200 and not patch_res.json():
                return None # Race condition: someone else took it
            return job
            
        return None
        
    except Exception as e:
        print(f"Error fetching job: {e}")
        return None

def main():
    print("🚀 Starting Backtest Worker...")
    print(f"Listening for jobs on {os.getenv('NEXT_PUBLIC_SUPABASE_URL')}")
    
    while True:
        try:
            job = fetch_pending_job()
            if job:
                print(f"\n[JOB FOUND] ID: {job['run_id']} | Stock: {job.get('stock_code')} | User: {job.get('user_id')}")
                
                # Parse config
                config = job.get('strategy_config') or {}
                
                # Run Core Logic
                result = execute_backtest_job(
                    run_id=job['run_id'],
                    symbol=job.get('stock_code'),
                    start_date=job.get('start_date'),
                    end_date=job.get('end_date'),
                    strategy_config=config,
                    user_id=job.get('user_id')
                )
                
                print(f"[JOB FINISHED] Result: {result}")
            else:
                # No jobs, sleep
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\nStopping worker...")
            break
        except Exception as e:
            print(f"Worker Loop Error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
