# apikeys
## 
    Name,Type,Default Value,Primary,Extra_options
    id,int4,NULL,yes,Is_Identity
    api_key,varchar,NULL,,Is_Unique
    title,varchar,NULL,,Is_Nullable
    user_uuid,varchar,NULL,,
    created_at,timestamp,now(),Is_Nullable
    status,varchar,NULL,,Is_Nullable

# backtest_runs
## 记录用户回测的数据
    Name,Type,Default Value,Constraints
    id,uuid,gen_random_uuid(),Is_Primary_Key
    session_id,uuid,NULL,
    user_id,varchar,NULL,
    strategy_config,jsonb,NULL,
    start_date,date,NULL,Allow_Null
    end_date,date,NULL,Allow_Null
    initial_cash,numeric,NULL,Allow_Nullable
    final_equity,numeric,NULL,Allow_Nullable
    return_pct,numeric,NULL,Allow_Nullable
    win_rate,numeric,NULL,Allow_Nullable
    total_trades,int4,NULL,Allow_Nullable
    max_drawdown,numeric,NULL,Allow_Nullable
    result_summary,jsonb,NULL,Allow_Nullable
    created_at,timestamptz,now(),

# backtest_sessions
## 记录用户的输入问题
    Name,Type,Default Value,Constraints
    id,uuid,gen_random_uuid(),Is_Primary_Key
    user_id,varchar,NULL,
    name,text,NULL,Allow_Nullable
    symbol,text,NULL,Allow_Nullable
    description,text,NULL,Allow_Nullable
    is_favorite,bool,false,Allow_Nullable
    created_at,timestamptz,now(),Is_Nullable
    updated_at,timestamptz,now(),Is_Nullable

# cashflows
## 实盘逐日记录，记录人工存入或取出的金额
    Name,Type,Default Value,Primary,Extra_options
    id,uuid,gen_random_uuid(),yes,
    run_id,text,NULL,,
    symbol,text,NULL,,
    date,date,NULL,,
    amount,numeric,NULL,,
    note,text,NULL,,Is_Nullable
    created_at,timestamp,now(),,Is_Nullable

# checkpoints
## 记录每一只股票不同日期进行LLM决策的进度
    Name,Type,Default Value,Primary,Extra_options
    run_id,uuid,NULL,yes,
    symbol,text,NULL,yes,
    date,date,NULL,yes,
    reason,text,NULL,,Is_Nullable
    created_at,timestamp,now(),,Is_Nullable

# credits
## 记录用户的积分获取、使用、赠送、清除（删除）记录
    Name,Type,Default Value,Primary,Extra_options
    id,int4,Null,yes,Is_Identity
    trans_no,varchar,Null,Is_Unique
    created_at,timestamp,now(),,
    user_uuid,varchar,NULL,,
    trans_type,varchar,NULL,,
    credits,int4,NULL,,
    order_no,varchar,NULL,,Is_Nullable
    expired_at,timestamp,NULL,,Is_Nullable

# daily_metrics
## 记录每一只股票进行回测的数据表现
    Name,Type,Default Value,Primary,Extra_options
    run_id,uuid,NULL,yes,
    symbol,text,NULL,yes,
    date,date,NULL,yes,
    nav,numeric,NULL,,Is_Nullable
    cash,numeric,NULL,,Is_Nullable
    position,numeric,NULL,,Is_Nullable
    daily_return,numeric,NULL,,Is_Nullable
    equity,numeric,NULL,,Is_Nullable
    created_at,timestamptz,now(),,

# errors
## 记录执行失败、错误信息
    Name,Type,Default Value,Primary,Extra_options
    id,uuid,gen_random_uuid(),yes,
    run_id,uuid,NULL,,
    symbol,text,NULL,,Is_Nullable
    date,date,NULL,,Is_Nullable
    source,text,NULL,,Is_Nullable
    code,text,NULL,,Is_Nullable
    message,text,NULL,,Is_Nullable
    raw,jsonb,NULL,,Is_Nullable
    created_at,timestampt,now(),,

# manual_exec
## 记录实盘手动成交的价格、方向等数据
    Name,Type,Default Value,Primary,Extra_options
    id,uuid,gen_random_uuid(),yes,
    run_id,uuid,NULL,,
    symbol,text,NULL,,
    decision_date,date,NULL,,
    execution_date,date,NULL,,
    side,text,NULL,,
    quantity_shares,int4,NULL,,
    price,numeric,NULL,,
    commission_rate,numeric,NULL,,Is_Nullable
    success,bool,True,,
    note,text,NULL,,Is_Nullable
    created_at,timestampt,now(),,Is_Nullable

# ohlc
## 记录股票每天的开盘价、收盘价、最高价、最低价、成交量
    Name,Type,Default Value,Primary,Extra_options
    symbol,text,NULL,yes,
    date,date,NULL,yes,
    run_id,uuid,NULL,,Is_Nullable
    open,numeric,NULL,,Is_Nullable
    high,numeric,NULL,,Is_Nullable
    low,numeric,NULL,,Is_Nullable
    close,numeric,NULL,,Is_Nullable
    source,text,NULL,,Is_Nullable
    created_at,timestampt,now(),,Is_Nullable

# order
##
    Name,Type,Default Value,Primary,Extra_options
    id,int4,NULL,yes,Is_Identity
    order_no,varchar,NULL,,Is_Unique
    created_at,timestampt,now(),Is_Nullable
    user_uuid,varchar,''::character_varying,,
    user_email,varchar,''::character_varying,,
    amount,int4,NULL,,
    interval,varchar,NULL,,Is_Nullable
    expired_at,timestamp,NULL,,Is_Nullable
    status,varchar,NULL,,
    stripe_session_id,varchar,NULL,,Is_Nullable
    credits,int4,NULL,,
    currency,varchar,NULL,,Is_Nullable
    sub_id,varchar,NULL,,Is_Nullable
    sub_interval_count,int4,NULL,,Is_Nullable
    sub_cycle_anchor,int4,NULL,,Is_Nullable
    sub_period_end,int4,NULL,,Is_Nullable
    sub_period_start,int4,NULL,,Is_Nullable
    sub_times,int4,NULL,,Is_Nullable
    product_id,varchar,NULL,,Is_Nullable
    product_name,varchar,NULL,,Is_Nullable
    valid_months,int4,NULL,,Is_Nullable
    order_detail,text,NULL,,Is_Nullable
    paid_at,timestamp,NULL,,Is_Nullable
    paid_email,varchar,NULL,,Is_Nullable
    paid_detail,text,NULL,,Is_Nullable

# runs
## 记录每一次回测的运行信息
    Name,Type,Default Value,Primary,Extra_options
    run_id,uuid,gen_random_uuid(),yes,
    label,text,NULL,,Is_Nullable
    status,text,NULL,,
    start_date,date,NULL,,Is_Nullable
    end_date,date,NULL,,Is_Nullable
    last_processed_date,date,NULL,,Is_Nullable
    created_at,timestamptz,now(),,
    finished_at,timestamptz,NULL,,Is_Nullable
    notes,text,NULL,,Is_Nullable
    user_id,varchar,NULL,,Is_Nullable
    stock_code,varchar,NULL,,Is_Nullable
    strategy_config,jsonb,NULL,,Is_Nullable
    cost,numeric,0,,Is_Nullable

# trades
## 记录回测成交的价格、方向等数据
    Name,Type,Default Value,Primary,Extra_options
    run_id,uuid,NULL,yes,
    symbol,text,NULL,yes,
    date,date,NULL,yes,
    side,text,NULL,,
    qty,numeric,NULL,,
    price,numeric,NULL,,
    effective_price,numeric,NULL,,Is_Nullable
    cash_before,numeric,NULL,,Is_Nullable
    cash_after,numeric,NULL,,Is_Nullable
    position_before,numeric,NULL,,Is_Nullable
    position_after,numeric,NULL,,Is_Nullable
    pnl,numeric,NULL,,Is_Nullable
    note,text,NULL,,Is_Nullable
    created_at,timestamp,now(),,

# users
## 记录用户信息
    Name,Type,Default Value,Primary,Extra_options
    id,int4,NULL,yes,Is_Identity
    uuid,varchar,NULL,,Is_Unique
    email,varchar,NULL,,
    nickname,varchar,NULL,,Is_Nullable
    avatar_url,varchar,NULL,,Is_Nullable
    signin_type,varchar,NULL,,Is_Nullable
    signin_provider,varchar,NULL,,Is_Nullable
    signin_openid,varchar,NULL,,Is_Nullable
    created_at,timestamp,now(),,Is_Nullable
    updated_at,timestamp,now(),,Is_Nullable
    signin_ip,varchar,NULL,,Is_Nullable
    locale,varchar,NULL,,Is_Nullable
    invite_code,varchar,''::character_varying,,Is_Nullable
    invited_by,varchar,''::character_varying,,
    is_affiliate,bool,false,,