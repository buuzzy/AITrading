"""
Simple Portfolio Tracker - One position per symbol
"""
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime


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
        buy_date: Optional[str] = None,
        can_sell_date: Optional[str] = None
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
        self.buy_date = buy_date  # T+1: 买入日期
        self.can_sell_date = can_sell_date  # T+1: 可卖出日期
        
    def calculate_liquidation_price(self) -> Optional[float]:
        """Calculate liquidation price - Not applicable for A-share"""
        return None
    
    def calculate_unrealized_pnl(self) -> float:
        """Calculate unrealized PnL with leverage"""
        direction = 1 if self.quantity >= 0 else -1
        return (self.current_price - self.entry_price) * abs(self.quantity) * self.leverage * direction

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'liquidation_price': self.liquidation_price,
            'leverage': self.leverage,
            'unrealized_pnl': self.calculate_unrealized_pnl(),
            'entry_time': self.entry_time
        }
    
    def calculate_risk_usd(self) -> float:
        """Calculate risk in USD (distance to stop loss)"""
        if self.stop_loss is None:
            return 0.0
        direction = 1 if self.quantity >= 0 else -1
        return abs(self.entry_price - self.stop_loss) * abs(self.quantity) * self.leverage
    
    def calculate_notional_usd(self) -> float:
        """Calculate notional value in USD"""
        return abs(self.quantity) * self.current_price
    
    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON format as requested"""
        # Calculate exit plan
        exit_plan = {}
        if self.profit_target is not None:
            exit_plan['profit_target'] = self.profit_target
        if self.stop_loss is not None:
            exit_plan['stop_loss'] = self.stop_loss
        
        # Calculate invalidation condition if stop_loss exists
        if self.stop_loss is not None:
            invalidation_level = self.stop_loss
            exit_plan['invalidation_condition'] = f"If the price closes below {invalidation_level:.2f} on a 3-minute candle"
        
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'liquidation_price': self.liquidation_price,
            'unrealized_pnl': self.calculate_unrealized_pnl(),
            'leverage': self.leverage,
            'exit_plan': exit_plan,
            'confidence': self.confidence,
            'risk_usd': self.calculate_risk_usd(),
            'notional_usd': self.calculate_notional_usd()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Position':
        """Create from dictionary"""
        return cls(
            symbol=data['symbol'],
            quantity=data['quantity'],
            entry_price=data['entry_price'],
            current_price=data.get('current_price', data['entry_price']),
            liquidation_price=data.get('liquidation_price'),
            leverage=data.get('leverage', 1.0),
            profit_target=data.get('profit_target'),
            stop_loss=data.get('stop_loss'),
            confidence=data.get('confidence', 0.5)
        )


class SimplePortfolio:
    """Super simple portfolio - one position per symbol"""
    
    def __init__(self, initial_cash: float = 10000.0):
        self.positions: Dict[str, Position] = {}
        self.initial_cash = initial_cash
        self.available_cash = initial_cash
        self.total_asset = initial_cash
    
    def add_position(self, position: Position) -> None:
        """Add or replace position for a symbol"""
        # Calculate collateral needed for this position
        collateral_needed = abs(position.quantity) * position.entry_price / position.leverage
        
        # Check if we already have this position to handle collateral
        old_collateral = 0
        if position.symbol in self.positions:
            old_position = self.positions[position.symbol]
            old_collateral = abs(old_position.quantity) * old_position.entry_price / old_position.leverage
        
        # Update available cash
        self.available_cash = self.available_cash + old_collateral - collateral_needed
        
        # Add position
        self.positions[position.symbol] = position
        
        # Update total asset
        self._update_total_asset()
    def decisions_display(self, all_decisions: Dict[str, Any]) -> None:
        print("\n" + "="*80)
        for symbol, decision_data in all_decisions.items():
            args = decision_data.get("trade_signal_args", {})
            print(f"\n{symbol} Trading Decision:")
            print(f"  Signal: {args.get('signal')}")
            print(f"  Quantity: {args.get('quantity')}")
            print(f"  Entry Price: ${args.get('entry_price', 0):.2f}")
            print(f"  Profit Target: ${args.get('profit_target')}")
            print(f"  Stop Loss: ${args.get('stop_loss')}")
            print(f"  Leverage: {args.get('leverage')}x")
            print(f"  Confidence: {args.get('confidence')}")
            print(f"  Risk: ${args.get('risk_usd', 0)}")
            print(f"  Invalidation: {args.get('invalidation_condition', 'N/A')}")
        
        
    def _validate_order_params(self, symbol: str, entry_price: float, leverage: float, quantity: float) -> Tuple[bool, str]:
        """Validate order parameters before execution"""
        if entry_price <= 0:
            return False, f"Invalid entry price: {entry_price} (must be > 0)"
        
        if leverage <= 0:
            return False, f"Invalid leverage: {leverage} (must be > 0)"
        
        if quantity == 0.0:
            return False, "Quantity is zero"
        
        return True, ""

    def execute_decision(self, symbol: Optional[str] = None, quantity: Optional[float] = None, 
                         price: Optional[float] = None, leverage: float = 1.0,
                         profit_target: Optional[float] = None, stop_loss: Optional[float] = None,
                         confidence: float = 0.5, signal: Optional[str] = None,
                         decision_data: Optional[Dict[str, Any]] = None, **kwargs) -> bool:
        """Execute a trading decision with validation and error handling.
        
        Can be called in two ways:
        1. Old add_order style: execute_decision(symbol="BTC", quantity=1.0, price=50000, ...)
        2. New dict style: execute_decision(decision_data={"trade_signal_args": {...}})
        
        Args:
            symbol: Symbol for the trade (or from decision_data)
            quantity: Quantity for the trade (or from decision_data)
            price: Entry price (or from decision_data)
            leverage: Leverage multiplier (default: 1.0)
            profit_target: Profit target price (optional)
            stop_loss: Stop loss price (optional)
            confidence: Confidence level 0-1 (default: 0.5)
            signal: Trading signal - 'buy', 'sell', 'hold', 'close' (or from decision_data)
            decision_data: Dictionary containing 'trade_signal_args' with order parameters
        
        Returns:
            True if order was executed successfully, False otherwise
        """
        try:
            # If decision_data is provided, extract parameters from it
            if decision_data is not None:
                # Extract args from decision_data
                if 'trade_signal_args' in decision_data:
                    args = decision_data.get("trade_signal_args", {})
                else:
                    # If decision_data is already the args dict
                    args = decision_data
                
                signal = args.get('signal', signal or 'hold')
                quantity = quantity if quantity is not None else args.get('quantity', 0.0)
                price = price if price is not None else args.get('entry_price', 0)
                leverage = args.get('leverage', leverage)
                profit_target = args.get('profit_target', profit_target)
                stop_loss = args.get('stop_loss', stop_loss)
                confidence = args.get('confidence', confidence)
                
                # Get symbol from args if not provided
                if symbol is None:
                    symbol = args.get('coin') or args.get('symbol')
            else:
                # Using positional/keyword arguments
                signal = signal or 'hold'
                if quantity is None or price is None:
                    print("❌ Quantity and price must be provided")
                    return False
            
            if symbol is None:
                print("❌ No symbol provided")
                return False
            
            # Convert to float for safety
            quantity = float(quantity) if quantity is not None else 0.0
            entry_price = float(price) if price is not None else 0.0
            leverage = float(leverage) if leverage is not None else 1.0

            
            # Normalize signal
            normalized_signal = signal.lower() if signal else 'hold'
            
            # Handle explicit close signal
            if normalized_signal == 'close':
                if symbol in self.positions:
                    self.remove_position(symbol)
                    print(f"🛑 {symbol}: Position closed by signal.")
                    return True
                else:
                    print(f"⚠️  {symbol}: No position to close.")
                    return False

            # If signal is hold, skip execution
            if normalized_signal == 'hold' or quantity == 0.0:
                print(f"⏸️  {symbol}: No new position (signal=hold or quantity=0).")
                return False

            # Validate order parameters
            is_valid, error_msg = self._validate_order_params(symbol, entry_price, leverage, quantity)
            if not is_valid:
                print(f"❌ {symbol}: {error_msg}")
                return False

            # Execute order with signal-based logic
            has_position = symbol in self.positions and self.positions[symbol].quantity != 0
            
            # Create position object
            liquidation_price = entry_price * (1 - 1/leverage) if leverage > 1 else None
            position = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                current_price=entry_price,
                liquidation_price=liquidation_price,
                leverage=leverage,
                profit_target=profit_target,
                stop_loss=stop_loss,
                confidence=confidence
            )
            
            # Rule: hold -> do nothing (already handled above)
            
            # Rule: existing position + close -> close and update totals (already handled above)
            
            # Rule: existing position + buy/sell -> handle based on direction
            if normalized_signal in ('buy', 'sell'):
                if has_position:
                    existing = self.positions[symbol]
                    existing_qty = float(existing.quantity)
                    if normalized_signal == 'buy':
                        # 加仓：数量需为正
                        if quantity <= 0:
                            print(f"❌ {symbol}: Invalid add quantity")
                            return False
                        # 现金校验（使用新增部分的资金占用）
                        try:
                            add_collateral = abs(quantity) * entry_price / leverage
                        except ZeroDivisionError:
                            print(f"❌ {symbol}: Invalid leverage (divide by zero)")
                            return False
                        if add_collateral > self.available_cash:
                            print(f"❌ {symbol}: Insufficient cash to add (need ${add_collateral:,.2f}, have ${self.available_cash:,.2f})")
                            return False
                        # 加权平均开仓价
                        new_qty = existing_qty + quantity
                        if new_qty <= 0:
                            print(f"❌ {symbol}: Resulting quantity invalid")
                            return False
                        new_entry = ((existing_qty * existing.entry_price) + (quantity * entry_price)) / new_qty
                        new_pos = Position(
                            symbol=symbol,
                            quantity=new_qty,
                            entry_price=new_entry,
                            current_price=entry_price,
                            liquidation_price=position.liquidation_price,
                            leverage=leverage,
                            profit_target=profit_target,
                            stop_loss=stop_loss,
                            confidence=confidence
                        )
                        self.add_position(new_pos)
                        print(f"✅ {symbol}: Position increased (Old Qty: {existing_qty}, +{quantity} -> New Qty: {new_qty}, Avg Entry: ${new_entry:.2f})")
                        return True
                    else:
                        # 部分减仓：数量需为正，且不超过当前持仓
                        if quantity <= 0:
                            print(f"❌ {symbol}: Invalid reduce quantity")
                            return False
                        reduce_qty = quantity
                        if reduce_qty > existing_qty:
                            reduce_qty = existing_qty
                        # 释放保证金并计入已实现盈亏
                        freed_collateral = reduce_qty * existing.entry_price / existing.leverage
                        realized_pnl = (entry_price - existing.entry_price) * reduce_qty * existing.leverage
                        self.available_cash += (freed_collateral + realized_pnl)
                        remaining_qty = existing_qty - reduce_qty
                        if remaining_qty <= 0:
                            # 全部减至零视为平仓
                            self.remove_position(symbol)
                            print(f"✅ {symbol}: Position reduced to zero (Sold {reduce_qty}, Exit price: ${entry_price:.2f})")
                            return True
                        else:
                            # 保持原入场均价，更新数量与当前价
                            existing.quantity = remaining_qty
                            existing.current_price = entry_price
                            self._update_total_asset()
                            print(f"✅ {symbol}: Position reduced (Old Qty: {existing_qty}, -{reduce_qty} -> New Qty: {remaining_qty})")
                            return True

                # No position - open new
                if not has_position:
                    # 现金校验仅在开新仓或做空开仓时触发
                    try:
                        collateral_needed = abs(quantity) * entry_price / leverage
                    except ZeroDivisionError:
                        print(f"❌ {symbol}: Invalid leverage (divide by zero)")
                        return False
                    if collateral_needed > self.available_cash:
                        print(f"❌ {symbol}: Insufficient cash (need ${collateral_needed:,.2f}, have ${self.available_cash:,.2f})")
                        return False
                    self.add_position(position)
                    print(f"✅ {symbol}: Order added successfully (Qty: {quantity}, Price: ${entry_price:.2f}, Signal: {signal})")
                    return True
            
            # Invalid signal
            print(f"❌ {symbol}: Invalid signal: {normalized_signal}")
            return False
                
        except Exception as e:
            print(f"❌ {symbol}: Error executing decision: {e}")
            return False

    def add_order(self, symbol: str, quantity: float, price: float, leverage: float, signal: str) -> bool:
        """兼容旧接口的下单方法，用于测试与历史代码。

        Args:
            symbol: 交易标的
            quantity: 数量（正为多，负为空）
            price: 入场价格
            leverage: 杠杆倍数
            signal: 'buy' | 'sell' | 'hold' | 'close'

        Returns:
            执行是否成功
        """
        return self.execute_decision(
            symbol=symbol,
            quantity=quantity,
            price=price,
            leverage=leverage,
            signal=signal
        )
    
    def remove_position(self, symbol: str) -> None:
        """Remove a position"""
        if symbol in self.positions:
            position = self.positions[symbol]
            # Return collateral to available cash
            collateral = abs(position.quantity) * position.entry_price / position.leverage
            unrealized_pnl = position.calculate_unrealized_pnl()
            # When closing position, we get back collateral + unrealized PnL
            self.available_cash += collateral + unrealized_pnl
        self.positions.pop(symbol, None)
        # Update total asset
        self._update_total_asset()
    
    def update_price(self, symbol: str, new_price: float) -> None:
        """Update current price for a position"""
        if symbol in self.positions:
            self.positions[symbol].current_price = new_price
            self._update_total_asset()
    
    def update_unrealized_pnl(self, symbol: str) -> None:
        """Update PnL for a position"""
        if symbol in self.positions:
            self.positions[symbol].unrealized_pnl = self.positions[symbol].calculate_unrealized_pnl()
    
    def update_all_prices(self, price_updates: Dict[str, float]) -> None:
        """Update prices for multiple positions at once"""
        for symbol, price in price_updates.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price
        self._update_total_asset()
    
    def _recalculate_assets(self) -> None:
        """Recalculate available cash and total asset based on current positions"""
        # Calculate total collateral used
        total_collateral = 0
        for position in self.positions.values():
            collateral = abs(position.quantity) * position.entry_price / position.leverage
            total_collateral += collateral
        
        # Available cash = initial cash - collateral used
        self.available_cash = self.initial_cash - total_collateral
        
        # Update total asset
        self._update_total_asset()
    
    def _update_total_asset(self) -> None:
        """Calculate and update total asset value"""
        # Total asset = available cash + (collateral + unrealized PnL for each position)
        position_values = 0
        for position in self.positions.values():
            collateral = abs(position.quantity) * position.entry_price / position.leverage
            unrealized_pnl = position.calculate_unrealized_pnl()
            position_values += collateral + unrealized_pnl
        
        self.total_asset = self.available_cash + position_values
    
    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        return list(self.positions.values())
    
    def total_pnl(self) -> float:
        """Calculate total PnL across all positions"""
        return sum(pos.calculate_unrealized_pnl() for pos in self.positions.values())
    
    def save_to_file(self, filename: str) -> None:
        data = {
            'positions': [pos.to_dict() for pos in self.positions.values()],
            'timestamp': datetime.now().isoformat(),
            'initial_cash': self.initial_cash,
            'available_cash': self.available_cash,
            'total_asset': self.total_asset
        }
        tmp = f"{filename}.tmp"
        try:
            import os, shutil
            if os.path.isfile(filename):
                try:
                    shutil.copyfile(filename, f"{filename}.bak")
                except Exception:
                    pass
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
            os.replace(tmp, filename)
        except Exception:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except Exception:
                pass
    
    def load_from_file(self, filename: str) -> None:
        import os
        path = filename
        data = None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            try:
                bak = f"{filename}.bak"
                with open(bak, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                path = bak
            except Exception:
                data = None
        if not isinstance(data, dict):
            data = {}
        self.initial_cash = data.get('initial_cash', self.initial_cash)
        self.available_cash = data.get('available_cash', self.available_cash)
        self.positions = {}
        for pos_data in data.get('positions', []):
            try:
                position = Position.from_dict(pos_data)
                self.positions[position.symbol] = position
            except Exception:
                pass
        self._update_total_asset()
    
    def display(self) -> None:
        """Simple display of all positions"""
        if not self.positions:
            print("No positions")
            return
        
        print(f"\n{'Symbol':<10} {'Qty':<10} {'Entry':<10} {'Current':<10} {'PnL':<10} {'Leverage':<10}")
        print("-" * 70)
        
        for pos in self.positions.values():
            pnl = pos.calculate_unrealized_pnl()
            pnl_str = f"${pnl:.4f}"
            print(f"{pos.symbol:<10} {pos.quantity:<10.4f} ${pos.entry_price:<9.2f} ${pos.current_price:<9.2f} {pnl_str:<10} {pos.leverage}x")
        
        print("-" * 70)
        print(f"Total PnL: ${self.total_pnl():.4f}")
        print(f"Available Cash: ${self.available_cash:.4f}")
        print(f"Total Asset: ${self.total_asset:.4f}\n")
    def return_json(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Return portfolio data in JSON format
        
        Args:
            symbol: Optional symbol to return data for. If None, returns all positions.
        
        Returns:
            If symbol is provided: single position JSON
            If symbol is None: dict with all positions as list
        """
        if symbol:
            if symbol not in self.positions:
                return {}
            return self.positions[symbol].to_json()
        
        # Return all positions as a list
        return {
            'positions': [pos.to_json() for pos in self.positions.values()],
            'timestamp': datetime.now().isoformat(),
            'total_pnl': self.total_pnl(),
            'available_cash': self.available_cash,
            'total_asset': self.total_asset,
            'initial_cash': self.initial_cash
        }
    def to_string(self, json_result: Dict[str, Any]) -> str:
        """Convert portfolio JSON to formatted string"""
        result_string = "HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE\n"
        
        # Calculate total return
        initial_cash = json_result.get('initial_cash', 10000.0)
        total_asset = json_result.get('total_asset', 0)
        total_return = ((total_asset - initial_cash) / initial_cash) * 100 if initial_cash > 0 else 0
        
        result_string += f"Current Total Return (percent): {total_return:.2f}%\n"
        result_string += f"Available Cash: {json_result.get('available_cash', 0):.2f}\n"
        result_string += f"Current Account Value: {total_asset:.2f}\n"
        result_string += "Current live positions & performance:\n\n"
        
        # Display each position
        positions = json_result.get('positions', [])
        for pos in positions:
            result_string += f"{pos}\n"
        
        return result_string

# Example usage
if __name__ == "__main__":
    # Create portfolio
    portfolio = SimplePortfolio()
    
    # Add positions using execute_decision
    portfolio.execute_decision(symbol="BTC", quantity=0.5, price=45000.0, leverage=10.0, signal="buy")
    portfolio.execute_decision(symbol="ETH", quantity=-10.0, price=3000.0, leverage=5.0, signal="sell")
    
    # Update current prices
    portfolio.update_all_prices({
        "BTC": 45500.0,
        "ETH": 2950.0
    })
    
    # Display
    portfolio.display()
    
    # Update prices
    portfolio.update_all_prices({
        "BTC": 46000.0,
        "ETH": 2920.0
    })
    
    portfolio.display()
    
    # Save
    portfolio.save_to_file("portfolio.json")

