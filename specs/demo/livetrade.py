import os
import json
from typing import Optional, Dict, Any, List
import requests
import tinyshare as ts
import pandas as pd
from datetime import datetime, timedelta

def _supabase_headers(key: str) -> Dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

def _fmt_date8_to_iso(d: str) -> str:
    try:
        s = str(d or "").strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
        return s
    except Exception:
        return str(d)

def _format_daily_row(row: Dict[str, Any]) -> str:
    t = _fmt_date8_to_iso(row.get("trade_date"))
    o = row.get("open")
    h = row.get("high")
    l = row.get("low")
    c = row.get("close")
    return f"{t}, O:{o}, H:{h}, L:{l}, C:{c}"

def _format_weekly_row(row: Dict[str, Any]) -> str:
    t = _fmt_date8_to_iso(row.get("trade_date"))
    o = row.get("open")
    h = row.get("high")
    l = row.get("low")
    c = row.get("close")
    return f"{t}, O:{o}, H:{h}, L:{l}, C:{c}"


def request_technical_analysis(base: str, ts_code: str, T: str, T_1: str) -> Optional[str]:
    api_key = os.getenv("DIFY_API_KEY")
    if not api_key:
        print("[DIFY] 未配置 DIFY_API_KEY，跳过技术分析请求。")
        return None
    url = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1/workflows/run")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prefix = "sz"
    try:
        exch = str(ts_code).split(".")[-1].upper()
        if exch == "SH":
            prefix = "sh"
        elif exch == "SZ":
            prefix = "sz"
    except Exception:
        pass
    stock_code = f"{prefix}{str(base).zfill(6)}"
    daily_lines = ""
    weekly_lines = ""
    token = os.getenv("TINYSHARE_TOKEN")
    if token:
        try:
            ts.set_token(token)
            pro = ts.pro_api()
            end_d = str(T_1 or "").replace("-", "")
            if not (end_d and len(end_d) == 8 and end_d.isdigit()):
                end_d = str(datetime.now().strftime("%Y%m%d"))
            start_hint = (datetime.strptime(end_d, "%Y%m%d") - timedelta(days=365)).strftime("%Y%m%d")
            df_d = pro.daily(ts_code=ts_code, start_date=start_hint, end_date=end_d)
            if df_d is not None and not df_d.empty:
                end_i = int(end_d)
                df_d["trade_date"] = pd.to_numeric(df_d["trade_date"], errors="coerce")
                df_d = df_d.dropna(subset=["trade_date"])            
                df_d = df_d.sort_values("trade_date").reset_index(drop=True)
                df_d = df_d[df_d["trade_date"] < end_i]
                df_d = df_d.tail(80)
                daily_lines = "\n".join(_format_daily_row(r) for r in df_d.to_dict("records"))
            df_w = pro.weekly(ts_code=ts_code, start_date=start_hint, end_date=end_d)
            if df_w is not None and not df_w.empty:
                end_i = int(end_d)
                df_w["trade_date"] = pd.to_numeric(df_w["trade_date"], errors="coerce")
                df_w = df_w.dropna(subset=["trade_date"])            
                df_w = df_w.sort_values("trade_date").reset_index(drop=True)
                df_w = df_w[df_w["trade_date"] < end_i]
                df_w = df_w.tail(40)
                weekly_lines = "\n".join(_format_weekly_row(r) for r in df_w.to_dict("records"))
        except Exception as e:
            print(f"[DIFY] Tushare 取数失败：{e}")
    query_text = f"{base} 后市怎么走？"
    if len(query_text) > 250:
        query_text = query_text[:250]
    payload = {
        "inputs": {
            "stock_code": stock_code,
            "daily": daily_lines,
            "weekly": weekly_lines,
            "query": query_text,
        },
        "response_mode": "streaming",
        "user": f"livetrade-{base}"
    }
    print(f"[DIFY] 运行工作流: query='{query_text}' | symbol={base} | T={T} | T-1={T_1}")
    resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=100)
    if resp.status_code != 200:
        body = resp.text[:500]
        print(f"[DIFY] 工作流请求失败（HTTP {resp.status_code}）：{body}")
        raise RuntimeError(
            f"Dify 工作流请求失败：HTTP {resp.status_code} | stock_code={stock_code}"
        )
    final_outputs: Dict[str, Any] = {}
    text_chunks: List[str] = []
    workflow_run_id = None
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if isinstance(line, bytes):
            try:
                line = line.decode('utf-8', errors='ignore')
            except Exception:
                continue
        if not line.startswith('data: '):
            continue
        payload_str = line[6:].strip()
        try:
            evt = json.loads(payload_str)
        except Exception:
            continue
        event = evt.get('event')
        data_obj = evt.get('data') or {}
        workflow_run_id = evt.get('workflow_run_id') or workflow_run_id
        if event == 'text_chunk':
            txt = (data_obj or {}).get('text')
            if isinstance(txt, str) and txt:
                text_chunks.append(txt)
        if event == 'node_finished':
            title = data_obj.get('title')
            status = data_obj.get('status')
            if status == 'failed':
                print(f"[DIFY] {title} status=failed")
                raise RuntimeError(
                    f"Dify 工作流节点失败：{title} | stock_code={stock_code}"
                )
            else:
                print(f"[DIFY] {title} status=success")
            outputs = data_obj.get('outputs') or {}
            if outputs:
                final_outputs.update(outputs)
        elif event == 'workflow_finished':
            status = data_obj.get('status')
            outputs = data_obj.get('outputs') or {}
            if status == 'failed':
                print(f"[DIFY] workflow_finished status=failed")
                raise RuntimeError(
                    f"Dify 工作流失败 | stock_code={stock_code}"
                )
            else:
                print(f"[DIFY] workflow_finished status=success")
            if outputs:
                final_outputs.update(outputs)
            break
    text = (
        final_outputs.get('technical_analysis')
        or final_outputs.get('text')
        or (''.join(text_chunks) if text_chunks else None)
    )
    if not text:
        raise RuntimeError("Dify 工作流未返回 technical_analysis/text 输出")
    text = str(text)
    print(f"[DIFY] 技术分析已获取（长度={len(text)}）")
    return text