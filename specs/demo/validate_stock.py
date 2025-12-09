import sys
import json
import os
import tinyshare as ts
from dotenv import load_dotenv

load_dotenv()

def validate(code):
    token = os.getenv("TINYSHARE_TOKEN")
    if not token:
        return {"valid": False, "reason": "Missing Tushare Token"}
        
    ts.set_token(token)
    pro = ts.pro_api()
    
    # 尝试智能补全后缀
    # 规则：60/68/5 => SH, 00/30/15 => SZ, 4/8 => BJ
    suffix = 'SZ'
    if code.startswith(('60', '68', '5', '90')): suffix = 'SH'
    elif code.startswith(('4', '8')): suffix = 'BJ'
    
    ts_code = f"{code}.{suffix}"
    
    try:
        # 查询 stock_basic，只查这一只
        # fields: ts_code, symbol, name, market
        df = pro.stock_basic(ts_code=ts_code, fields='ts_code,name,market')
        
        if df is not None and not df.empty:
            return {
                "valid": True, 
                "name": df.iloc[0]['name'],
                "ts_code": df.iloc[0]['ts_code']
            }
        
        # 如果股票没查到，试试基金（ETF）
        df_fund = pro.fund_basic(ts_code=ts_code, fields='ts_code,name')
        if df_fund is not None and not df_fund.empty:
             return {
                "valid": True, 
                "name": df_fund.iloc[0]['name'],
                "ts_code": df_fund.iloc[0]['ts_code'],
                "is_fund": True
            }
            
        return {"valid": False, "reason": "Not found in A-share or ETF list"}
        
    except Exception as e:
        return {"valid": False, "reason": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"valid": False, "reason": "No code provided"}))
        sys.exit(1)
        
    code = sys.argv[1]
    # 简单清洗
    code = code.strip()
    if not code.isdigit() or len(code) != 6:
         print(json.dumps({"valid": False, "reason": "Format error (must be 6 digits)"}))
         sys.exit(0)

    res = validate(code)
    print(json.dumps(res, ensure_ascii=False))
