"""
Simple Portfolio Tracker - Optimized for A-Share Backtesting
"""
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import math

class Position:
    """Simple position tracking - one per symbol"""
    
    def __init__(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        current_price: float = None,
        liquidation_price: Optional[float] = None,
        leverage: float = 1.0,
        profit_target: Optional[float] = None,
        stop_loss: Optional[float] = None,
        confidence: float = 0.5,
        buy_date: Optional[str] = None, # Store YYYYMMDD string or YYYY-MM-DD
        highest_price: float = None, # For trailing stop
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.current_price = current_price or entry_price
        self.liquidation_price = liquidation_price
        self.leverage = leverage
        self.entry_time = datetime.now().isoformat()
        self.profit_target = profit_target
        self.stop_loss = stop_loss
        self.confidence = confidence
        self.buy_date = buy_date
        self.highest_price = highest_price or entry_price
        
    def calculate_unrealized_pnl(self) -> float:
        """Calculate unrealized PnL with leverage"""
        direction = 1 if self.quantity >= 0 else -1
        return (self.current_price - self.entry_price) * abs(self.quantity) * self.leverage * direction

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'liquidation_price': self.liquidation_price,
            'leverage': self.leverage,
            'unrealized_pnl': self.calculate_unrealized_pnl(),
            'entry_time': self.entry_time,
            'buy_date': self.buy_date,
            'highest_price': self.highest_price
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Position':
        return cls(
            symbol=data['symbol'],
            quantity=data['quantity'],
            entry_price=data['entry_price'],
            current_price=data.get('current_price', data['entry_price']),
            liquidation_price=data.get('liquidation_price'),
            leverage=data.get('leverage', 1.0),
            profit_target=data.get('profit_target'),
            stop_loss=data.get('stop_loss'),
            confidence=data.get('confidence', 0.5),
            buy_date=data.get('buy_date'),
            highest_price=data.get('highest_price')
        )

    def to_json(self) -> Dict[str, Any]:
        # For AI context
        exit_plan = {}
        if self.profit_target: exit_plan['profit_target'] = self.profit_target
        if self.stop_loss: exit_plan['stop_loss'] = self.stop_loss
        
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'unrealized_pnl': self.calculate_unrealized_pnl(),
            'buy_date': self.buy_date,
            'highest_price': self.highest_price,
            'exit_plan': exit_plan
        }


class SimplePortfolio:
    """Portfolio Tracker with A-Share Rules (T+1, Commission, Stamp Duty)"""
    
    def __init__(self, initial_cash: float = 100000.0, commission_rate: float = 0.00025, stamp_duty_rate: float = 0.0005):
        self.positions: Dict[str, Position] = {}
        self.initial_cash = initial_cash
        self.available_cash = initial_cash
        self.total_asset = initial_cash
        self.commission_rate = commission_rate
        self.stamp_duty_rate = stamp_duty_rate
    
    def update_price(self, symbol: str, new_price: float) -> None:
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.current_price = new_price
            # Update High Water Mark
            if new_price > pos.highest_price:
                pos.highest_price = new_price
            self._update_total_asset()
            
    def _update_total_asset(self) -> None:
        position_values = sum(abs(pos.quantity) * pos.current_price for pos in self.positions.values())
        self.total_asset = self.available_cash + position_values

    def execute_decision(self, symbol: str, quantity: float, price: float, 
                         signal: str = 'hold', current_date: str = None) -> bool:
        """
        Execute trade with A-Share rules.
        Args:
            symbol: Stock code
            quantity: Number of shares (must be positive for buy/sell)
            price: Execution price
            signal: 'buy' or 'sell'/'close'
            current_date: YYYY-MM-DD string, required for T+1 check
        """
        try:
            if quantity <= 0 or price <= 0: return False
            signal = signal.lower()
            
            has_position = symbol in self.positions
            
            # === SELL LOGIC ===
            if signal in ('sell', 'close'):
                if not has_position: return False
                pos = self.positions[symbol]
                
                # T+1 Check
                if current_date and pos.buy_date:
                    # Assuming date format is comparable (YYYY-MM-DD or YYYYMMDD)
                    # Simple string comparison works if format is consistent
                    if current_date <= pos.buy_date:
                        # print(f"T+1 Lock: Bought {pos.buy_date}, Current {current_date}")
                        return False
                
                sell_qty = min(abs(quantity), abs(pos.quantity))
                
                revenue = sell_qty * price
                commission = revenue * self.commission_rate
                stamp_duty = revenue * self.stamp_duty_rate
                net_revenue = revenue - commission - stamp_duty
                
                self.available_cash += net_revenue
                
                remaining = abs(pos.quantity) - sell_qty
                if remaining < 1:
                    self.positions.pop(symbol, None)
                else:
                    pos.quantity = remaining
                
                self._update_total_asset()
                return True

            # === BUY LOGIC ===
            elif signal == 'buy':
                cost = quantity * price
                commission = cost * self.commission_rate
                total_cost = cost + commission
                
                if total_cost > self.available_cash:
                    return False
                
                self.available_cash -= total_cost
                
                if has_position:
                    pos = self.positions[symbol]
                    new_qty = pos.quantity + quantity
                    new_avg = ((pos.quantity * pos.entry_price) + (quantity * price)) / new_qty
                    pos.quantity = new_qty
                    pos.entry_price = new_avg
                    pos.current_price = price
                    if price > pos.highest_price: pos.highest_price = price # Update high on buy? Usually only mark to market matters.
                    # Simplified: Keep old buy_date
                else:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        quantity=quantity,
                        entry_price=price,
                        current_price=price,
                        highest_price=price, # Init high
                        buy_date=current_date
                    )
                
                self._update_total_asset()
                return True
                
            return False
        except Exception as e:
            print(f"Trade Error: {e}")
            return False

    def get_position_info(self, symbol: str) -> Optional[Dict]:
        if symbol in self.positions:
            p = self.positions[symbol]
            return {'quantity': p.quantity, 'entry_price': p.entry_price}
        return None