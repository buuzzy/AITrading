import json
import operator
import re
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union, Set
from datetime import datetime

# === 1. Math & Logic Operators ===
OPERATORS = {
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    '==': operator.eq,
    '!=': operator.ne
}

# === 2. Indicator Library (The Factory) ===
class IndicatorLibrarian:
    def __init__(self):
        pass

    def _extract_indicators_from_rule(self, rule: Dict, indicators: Set[str]):
        if 'indicator' in rule:
            indicators.add(rule['indicator'])
        if 'value' in rule and isinstance(rule['value'], str):
            tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', rule['value'])
            for t in tokens:
                indicators.add(t)

    def parse_and_calculate(self, strategy_config: Dict, df: pd.DataFrame) -> pd.DataFrame:
        needed_indicators = set()
        
        def scan_rules(rules):
            for r in rules:
                if 'rules' in r: 
                    scan_rules(r['rules'])
                else: 
                    self._extract_indicators_from_rule(r, needed_indicators)

        scan_rules(strategy_config.get('entry_rules', []))
        scan_rules(strategy_config.get('exit_rules', {}).get('signals', []))

        for name in needed_indicators:
            self._calculate_indicator(name, df)
            
        return df

    def _calculate_indicator(self, name: str, df: pd.DataFrame):
        if name in df.columns: return

        # 1. Price SMA/EMA
        match_ma = re.match(r'(ema|sma)_(\d+)$', name)
        if match_ma:
            type_, period = match_ma.groups()
            period = int(period)
            if type_ == 'ema':
                df[name] = df['close'].ewm(span=period, adjust=False).mean()
            elif type_ == 'sma':
                df[name] = df['close'].rolling(window=period).mean()
            return

        # 2. Volume SMA/EMA (New!)
        match_vol_ma = re.match(r'(ema|sma)_vol_(\d+)$', name)
        if match_vol_ma:
            type_, period = match_vol_ma.groups()
            period = int(period)
            if 'vol' not in df.columns: return
            if type_ == 'ema':
                df[name] = df['vol'].ewm(span=period, adjust=False).mean()
            elif type_ == 'sma':
                df[name] = df['vol'].rolling(window=period).mean()
            return

        # 3. RSI
        match_rsi = re.match(r'rsi_(\d+)$', name)
        if match_rsi:
            period = int(match_rsi.group(1))
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            df[name] = 100.0 - (100.0 / (1.0 + rs))
            df[name] = df[name].fillna(50.0)
            return

        # 4. BOLL
        if name in ['boll_upper', 'boll_lower', 'boll_mid']:
            ma = df['close'].rolling(window=20).mean()
            std = df['close'].rolling(window=20).std()
            if 'boll_mid' not in df.columns: df['boll_mid'] = ma
            if name == 'boll_upper': df[name] = ma + 2 * std
            if name == 'boll_lower': df[name] = ma - 2 * std
            return

        # 5. MACD
        if name in ['macd', 'macd_dif', 'macd_dea']:
            ema12 = df['close'].ewm(span=12, adjust=False).mean()
            ema26 = df['close'].ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            hist = 2.0 * (dif - dea)
            if 'macd_dif' not in df.columns: df['macd_dif'] = dif
            if 'macd_dea' not in df.columns: df['macd_dea'] = dea
            if 'macd' not in df.columns: df['macd'] = hist
            return

        # 6. KDJ
        if name in ['kdj_k', 'kdj_d', 'kdj_j']:
            low_min = df['low'].rolling(window=9).min()
            high_max = df['high'].rolling(window=9).max()
            rsv = (df['close'] - low_min) / (high_max - low_min) * 100
            df['kdj_k'] = rsv.ewm(alpha=1/3, adjust=False).mean()
            df['kdj_d'] = df['kdj_k'].ewm(alpha=1/3, adjust=False).mean()
            df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
            return

        # 7. CCI
        match_cci = re.match(r'cci_(\d+)$', name)
        if match_cci:
            period = int(match_cci.group(1))
            tp = (df['high'] + df['low'] + df['close']) / 3
            sma_tp = tp.rolling(window=period).mean()
            mad = (tp - sma_tp).abs().rolling(window=period).mean()
            df[name] = (tp - sma_tp) / (0.015 * mad).replace(0, np.nan)
            return
        if name == 'cci':
            self._calculate_indicator('cci_20', df)
            df['cci'] = df['cci_20']
            return

        # 8. ATR
        match_atr = re.match(r'atr_(\d+)$', name)
        if match_atr:
            period = int(match_atr.group(1))
            prev_close = df['close'].shift(1)
            tr1 = df['high'] - df['low']
            tr2 = (df['high'] - prev_close).abs()
            tr3 = (df['low'] - prev_close).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df[name] = tr.rolling(window=period).mean()
            return

        # 9. Previous Data
        if name.startswith('prev_'):
            base_name = name[5:]
            self._calculate_indicator(base_name, df)
            if base_name in df.columns:
                df[name] = df[base_name].shift(1)
            return

        # 10. Rolling High/Low (New!)
        match_hl = re.match(r'(high|low)_(\d+)$', name)
        if match_hl:
            type_, period = match_hl.groups()
            period = int(period)
            if type_ == 'high':
                df[name] = df['high'].rolling(window=period).max()
            elif type_ == 'low':
                df[name] = df['low'].rolling(window=period).min()
            return
            
        # 11. Bollinger Bandwidth (New!)
        if name == 'boll_width':
            if 'boll_upper' not in df.columns: self._calculate_indicator('boll_upper', df)
            # Standard Bandwidth: (Upper - Lower) / Mid
            # But let's just make sure components exist, usually user does (Upper - Lower) manually
            # If user asks for 'boll_width', we give them (Upper - Lower) / Mid
            df[name] = (df['boll_upper'] - df['boll_lower']) / df['boll_mid']
            return

# === 3. The Brain (Evaluator) ===
class StrategyEvaluator:
    def __init__(self, strategy_json: Union[str, Dict[str, Any]]):
        if isinstance(strategy_json, str):
            self.config = json.loads(strategy_json)
        else:
            self.config = strategy_json
        self.librarian = IndicatorLibrarian()

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        # Ensure H/L/O exist
        if 'high' not in df.columns: df['high'] = df['close']
        if 'low' not in df.columns: df['low'] = df['close']
        if 'open' not in df.columns: df['open'] = df['close']
        if 'vol' not in df.columns: df['vol'] = 0 # Safety
        return self.librarian.parse_and_calculate(self.config, df)

    def validate(self) -> List[str]:
        """
        Scans the config for unsupported indicators.
        Returns a list of invalid indicator names found.
        """
        needed = set()
        self.librarian._extract_indicators_from_rule(self.config, needed) # This is a bit recursive, let's fix it below
        
        # Better scan logic for validation
        all_tokens = set()
        
        def scan_rules(rules):
            for r in rules:
                if 'rules' in r: 
                    scan_rules(r['rules'])
                else:
                    if 'indicator' in r: all_tokens.add(r['indicator'])
                    if 'value' in r and isinstance(r['value'], str):
                        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', r['value'])
                        for t in tokens: all_tokens.add(t)

        scan_rules(self.config.get('entry_rules', []))
        scan_rules(self.config.get('exit_rules', {}).get('signals', []))

        # Hardcoded Whitelist (should match Librarian's regex/logic)
        known_bases = {
            'close', 'open', 'high', 'low', 'vol', 'volume', 'date',
            'pnl_pct', 'position_highest', 'holding_days', 'current_price', 'boll_width'
        }
        
        invalid = []
        for token in all_tokens:
            if token in known_bases: continue
            if token.isdigit(): continue
            
            # Check Patterns
            is_valid_pattern = any([
                re.match(r'^(ema|sma)_(\d+)$', token),
                re.match(r'^(ema|sma)_vol_(\d+)$', token),
                re.match(r'^rsi_(\d+)$', token),
                re.match(r'^cci(_\d+)?$', token),
                re.match(r'^atr_(\d+)$', token),
                re.match(r'^(high|low)_(\d+)$', token),
                re.match(r'^prev_', token),
                token in ['boll_upper', 'boll_lower', 'boll_mid', 'macd', 'macd_dif', 'macd_dea', 'kdj_k', 'kdj_d', 'kdj_j']
            ])
            
            if not is_valid_pattern:
                invalid.append(token)
        
        return invalid

    def _resolve_math_expression(self, expression: Union[str, float, int], row: pd.Series) -> float:
        if isinstance(expression, (int, float)):
            return float(expression)
        if not isinstance(expression, str):
            return 0.0

        if expression in row:
            val = row[expression]
            return float(val) if pd.notna(val) else 0.0
        
        if not re.match(r'^[a-zA-Z0-9_\.\+\-\*\/\(\)\s]+$', expression):
            return 0.0

        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', expression)
        tokens.sort(key=len, reverse=True)
        
        eval_str = expression
        for token in tokens:
            if token in row:
                val = row[token]
                if pd.isna(val): val = 0.0
                eval_str = eval_str.replace(token, str(val))
            else:
                return 0.0
        try:
            return float(eval(eval_str))
        except:
            return 0.0

    def _evaluate_condition(self, rule: Dict[str, Any], row: pd.Series) -> bool:
        left_raw = rule.get('indicator')
        right_raw = rule.get('value')
        op_str = rule.get('comparator')

        left_val = self._resolve_math_expression(left_raw, row)
        right_val = self._resolve_math_expression(right_raw, row)

        op_func = OPERATORS.get(op_str)
        if not op_func: return False

        return op_func(left_val, right_val)

    def _evaluate_rules_list(self, rules: List[Dict], row: pd.Series) -> tuple[bool, str]:
        if not rules: return False, ""
        reasons = []
        for rule in rules:
            if not self._evaluate_condition(rule, row):
                return False, ""
            reasons.append(rule.get('description', 'match'))
        return True, " & ".join(reasons)

    def evaluate(self, row: pd.Series, current_position: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Context Injection
        pnl_pct = 0.0
        position_highest = 0.0
        holding_days = 0
        
        if current_position and current_position.get('quantity', 0) > 0:
            entry = float(current_position.get('entry_price', 0))
            position_highest = float(current_position.get('highest_price') or entry)
            
            curr = float(row.get('close', 0))
            if entry > 0:
                pnl_pct = (curr - entry) / entry
            
            # Calculate Holding Days
            buy_date_str = current_position.get('buy_date')
            current_date_str = row.get('date')
            if buy_date_str:
                try:
                    # Assuming simple YYYY-MM-DD or YYYYMMDD comparison works if consistent
                    # For accurate diff, parse to datetime
                    # row['date'] is usually Timestamp in engine, but passed as Series it might be object
                    d_curr = pd.to_datetime(current_date_str)
                    d_buy = pd.to_datetime(buy_date_str)
                    holding_days = (d_curr - d_buy).days
                except:
                    holding_days = 0
        
        # Create context view
        row_ctx = row.copy()
        row_ctx['pnl_pct'] = pnl_pct
        row_ctx['position_highest'] = position_highest
        row_ctx['holding_days'] = holding_days
        row_ctx['current_price'] = row['close']

        # --- 1. EXIT LOGIC ---
        if current_position and current_position.get('quantity', 0) > 0:
            sl_pct = self.config.get('exit_rules', {}).get('hard_stop_loss_pct')
            if sl_pct is not None and pnl_pct <= -abs(float(sl_pct)):
                return {"signal": "sell", "reason": f"Hard SL ({pnl_pct*100:.1f}%)"}

            tp_pct = self.config.get('exit_rules', {}).get('hard_take_profit_pct')
            if tp_pct is not None and pnl_pct >= abs(float(tp_pct)):
                return {"signal": "sell", "reason": f"Hard TP ({pnl_pct*100:.1f}%)"}

            exit_signals = self.config.get('exit_rules', {}).get('signals', [])
            for item in exit_signals:
                rules = item.get('rules', []) if 'rules' in item else [item]
                passed, desc = self._evaluate_rules_list(rules, row_ctx)
                if passed:
                    return {"signal": "sell", "reason": f"{item.get('name','Exit')}: {desc}"}

        # --- 2. ENTRY LOGIC ---
        has_pos = current_position and current_position.get('quantity', 0) > 0
        
        if not has_pos:
            entry_section = self.config.get('entry_rules', [])
            is_scenario_mode = len(entry_section) > 0 and 'rules' in entry_section[0]
            
            if is_scenario_mode:
                for scenario in entry_section:
                    passed, desc = self._evaluate_rules_list(scenario.get('rules', []), row_ctx)
                    if passed:
                        return {"signal": "buy", "reason": f"{scenario.get('name','Entry')}: {desc}"}
            else:
                passed, desc = self._evaluate_rules_list(entry_section, row_ctx)
                if passed:
                    return {"signal": "buy", "reason": desc}

        return {"signal": "hold", "reason": ""}