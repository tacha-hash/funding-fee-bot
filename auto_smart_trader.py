#!/usr/bin/env python3
"""
Auto Smart Trader for AsterDex Funding Bot
Automatically manages positions based on hybrid strategy rules
"""
import os
import sys
import json
import time
import requests
import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode
from typing import Dict, List, Optional, Tuple

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class AutoSmartTrader:
    def __init__(self):
        self.api_key = os.environ.get("ASTERDEX_API_KEY")
        self.api_secret = os.environ.get("ASTERDEX_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not found")
        
        self.spot_base_url = "https://sapi.asterdex.com"
        self.futures_base_url = "https://fapi.asterdex.com"
        
        # Trading rules - Hybrid Strategy
        self.rules = {
            # Profit taking rules
            "profit_targets": {
                "partial_take_1": {"threshold": 10.0, "percentage": 0.25, "executed": False},
                "partial_take_2": {"threshold": 25.0, "percentage": 0.30, "executed": False},
                "partial_take_3": {"threshold": 50.0, "percentage": 0.40, "executed": False},
                "full_exit": {"threshold": 100.0, "percentage": 1.0, "executed": False}
            },
            
            # Risk management rules
            "risk_management": {
                "stop_loss": -20.0,           # Stop loss at -20 USDT
                "trailing_stop": True,        # Enable trailing stop
                "trailing_distance": 10.0,    # Trail by 10 USDT from peak
                "max_drawdown": 15.0,         # Max drawdown from peak
                "margin_limit": 0.35          # Max 35% margin usage
            },
            
            # Funding rate rules
            "funding_rules": {
                "negative_threshold": -0.002,  # Exit if funding < -0.2%
                "very_negative": -0.005,       # Force exit if < -0.5%
                "rebalance_threshold": 0.01    # Rebalance if > 1%
            },
            
            # Position management
            "position_rules": {
                "min_position_size": 10.0,     # Minimum position in ASTER
                "max_position_size": 500.0,    # Maximum position in ASTER
                "rebalance_interval": 24,      # Hours between rebalancing
                "max_hold_days": 30           # Maximum days to hold position
            }
        }
        
        # State tracking
        self.state = {
            "peak_pnl": 0.0,
            "last_rebalance": None,
            "position_start_time": None,
            "executed_rules": [],
            "total_realized_profit": 0.0
        }
        
        self.dry_run = False  # Set to True for testing
        
    def sign_params(self, params):
        """Sign API request parameters"""
        api_secret = self.api_secret.encode('utf-8')
        params.setdefault("recvWindow", 5000)
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params, doseq=True)
        signature = hmac.new(api_secret, query.encode("utf-8"), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params
    
    def make_request(self, base_url, path, params=None, method="GET", signed=False):
        """Make API request"""
        url = f"{base_url}{path}"
        params = params or {}
        
        headers = {
            "X-MBX-APIKEY": self.api_key,
            "User-Agent": "AutoSmartTrader/1.0",
        }
        
        if signed:
            params = self.sign_params(params)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                response = requests.request(method.upper(), url, data=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def get_current_position(self):
        """Get current ASTERUSDT position"""
        positions = self.make_request(
            self.futures_base_url, "/fapi/v2/positionRisk", {}, signed=True
        )
        
        if not positions:
            return None
        
        for pos in positions:
            if pos["symbol"] == "ASTERUSDT" and abs(float(pos["positionAmt"])) > 0:
                return {
                    "symbol": pos["symbol"],
                    "size": float(pos["positionAmt"]),
                    "side": "LONG" if float(pos["positionAmt"]) > 0 else "SHORT",
                    "entry_price": float(pos["entryPrice"]),
                    "mark_price": float(pos["markPrice"]),
                    "pnl": float(pos["unRealizedProfit"]),
                    "notional": abs(float(pos["positionAmt"]) * float(pos["markPrice"]))
                }
        return None
    
    def get_account_info(self):
        """Get futures account information"""
        account = self.make_request(
            self.futures_base_url, "/fapi/v2/account", {}, signed=True
        )
        
        if not account:
            return None
        
        return {
            "total_balance": float(account["totalWalletBalance"]),
            "available_balance": float(account["availableBalance"]),
            "total_pnl": float(account["totalUnrealizedProfit"]),
            "margin_ratio": float(account["totalInitialMargin"]) / float(account["totalWalletBalance"]) if float(account["totalWalletBalance"]) > 0 else 0
        }
    
    def get_funding_rate(self):
        """Get current funding rate"""
        funding = self.make_request(
            self.futures_base_url, "/fapi/v1/premiumIndex", {"symbol": "ASTERUSDT"}
        )
        
        if not funding:
            return None
        
        return {
            "rate": float(funding["lastFundingRate"]),
            "next_time": datetime.fromtimestamp(funding["nextFundingTime"] / 1000, timezone.utc)
        }
    
    def close_position_partial(self, position, percentage):
        """Close partial position"""
        close_size = abs(position["size"]) * percentage
        close_size = self._floor_to_step(close_size, 0.01)  # Round to step size
        
        if close_size < 0.01:  # Minimum order size
            print(f"⚠️  Close size too small: {close_size}")
            return None
        
        # For SHORT position, we BUY to close
        side = "BUY" if position["side"] == "SHORT" else "SELL"
        
        payload = {
            "symbol": "ASTERUSDT",
            "side": side,
            "type": "MARKET",
            "quantity": f"{close_size:.2f}",
            "reduceOnly": "true"
        }
        
        if self.dry_run:
            print(f"🧪 DRY RUN: Would close {percentage*100:.1f}% ({close_size:.2f} ASTER) via {side}")
            return {"orderId": "DRY_RUN", "executedQty": close_size, "status": "FILLED"}
        
        print(f"📤 Closing {percentage*100:.1f}% position: {side} {close_size:.2f} ASTER")
        
        result = self.make_request(
            self.futures_base_url, "/fapi/v1/order", payload, method="POST", signed=True
        )
        
        return result
    
    def close_position_full(self, position):
        """Close entire position"""
        return self.close_position_partial(position, 1.0)
    
    def _floor_to_step(self, value, step):
        """Floor value to step size"""
        return float(Decimal(str(value)) - (Decimal(str(value)) % Decimal(str(step))))
    
    def evaluate_profit_targets(self, position, current_pnl):
        """Evaluate and execute profit taking rules"""
        actions = []
        
        for rule_name, rule in self.rules["profit_targets"].items():
            if rule["executed"]:
                continue
                
            if current_pnl >= rule["threshold"]:
                print(f"🎯 Profit target triggered: {rule_name} at {current_pnl:.2f} USDT")
                
                # Execute partial close
                result = self.close_position_partial(position, rule["percentage"])
                
                if result and result.get("status") == "FILLED":
                    executed_qty = float(result.get("executedQty", 0))
                    realized_profit = executed_qty * (position["mark_price"] - position["entry_price"])
                    if position["side"] == "SHORT":
                        realized_profit = -realized_profit  # Invert for short
                    
                    self.state["total_realized_profit"] += realized_profit
                    rule["executed"] = True
                    
                    actions.append({
                        "type": "profit_take",
                        "rule": rule_name,
                        "percentage": rule["percentage"] * 100,
                        "quantity": executed_qty,
                        "realized_profit": realized_profit,
                        "remaining_pnl": current_pnl
                    })
                    
                    print(f"✅ Executed {rule_name}: Closed {executed_qty:.2f} ASTER, Realized {realized_profit:.2f} USDT")
                break  # Only execute one rule per cycle
        
        return actions
    
    def evaluate_risk_management(self, position, account, current_pnl):
        """Evaluate and execute risk management rules"""
        actions = []
        
        # Update peak PnL for trailing stop
        if current_pnl > self.state["peak_pnl"]:
            self.state["peak_pnl"] = current_pnl
        
        # Stop loss check
        if current_pnl <= self.rules["risk_management"]["stop_loss"]:
            print(f"🚨 STOP LOSS TRIGGERED: {current_pnl:.2f} USDT")
            result = self.close_position_full(position)
            if result:
                actions.append({
                    "type": "stop_loss",
                    "reason": "Hard stop loss",
                    "pnl": current_pnl
                })
            return actions
        
        # Trailing stop check
        if self.rules["risk_management"]["trailing_stop"]:
            trailing_stop_level = self.state["peak_pnl"] - self.rules["risk_management"]["trailing_distance"]
            if current_pnl <= trailing_stop_level and self.state["peak_pnl"] > 0:
                print(f"🚨 TRAILING STOP TRIGGERED: {current_pnl:.2f} USDT (Peak: {self.state['peak_pnl']:.2f})")
                result = self.close_position_full(position)
                if result:
                    actions.append({
                        "type": "trailing_stop",
                        "reason": f"Trailing stop from peak {self.state['peak_pnl']:.2f}",
                        "pnl": current_pnl
                    })
                return actions
        
        # Max drawdown check
        drawdown = self.state["peak_pnl"] - current_pnl
        if drawdown >= self.rules["risk_management"]["max_drawdown"] and self.state["peak_pnl"] > 0:
            print(f"🚨 MAX DRAWDOWN TRIGGERED: {drawdown:.2f} USDT from peak")
            result = self.close_position_partial(position, 0.5)  # Close 50%
            if result:
                actions.append({
                    "type": "drawdown_protection",
                    "reason": f"Max drawdown {drawdown:.2f} USDT",
                    "percentage": 50
                })
        
        # Margin usage check
        if account and account["margin_ratio"] >= self.rules["risk_management"]["margin_limit"]:
            print(f"⚠️ HIGH MARGIN USAGE: {account['margin_ratio']*100:.1f}%")
            result = self.close_position_partial(position, 0.3)  # Close 30%
            if result:
                actions.append({
                    "type": "margin_management",
                    "reason": f"High margin usage {account['margin_ratio']*100:.1f}%",
                    "percentage": 30
                })
        
        return actions
    
    def evaluate_funding_rules(self, position, funding_rate):
        """Evaluate funding rate rules"""
        actions = []
        
        if not funding_rate:
            return actions
        
        rate = funding_rate["rate"]
        
        # Very negative funding - force exit
        if rate <= self.rules["funding_rules"]["very_negative"]:
            print(f"🚨 VERY NEGATIVE FUNDING: {rate*100:.3f}% - Force exit")
            result = self.close_position_full(position)
            if result:
                actions.append({
                    "type": "funding_exit",
                    "reason": f"Very negative funding {rate*100:.3f}%",
                    "rate": rate
                })
        
        # Negative funding warning
        elif rate <= self.rules["funding_rules"]["negative_threshold"]:
            print(f"⚠️ NEGATIVE FUNDING: {rate*100:.3f}% - Consider exit")
            # Don't auto-close, just warn
            actions.append({
                "type": "funding_warning",
                "reason": f"Negative funding {rate*100:.3f}%",
                "rate": rate
            })
        
        return actions
    
    def run_strategy_cycle(self):
        """Run one cycle of the smart trading strategy"""
        print(f"\n🤖 Auto Smart Trader Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Get current data
        position = self.get_current_position()
        if not position:
            print("ℹ️  No active position found")
            return []
        
        account = self.get_account_info()
        funding = self.get_funding_rate()
        current_pnl = position["pnl"]
        
        print(f"📊 Position: {position['side']} {abs(position['size']):.2f} ASTER @ {position['entry_price']:.4f}")
        print(f"💰 Current PnL: {current_pnl:+.2f} USDT")
        print(f"📈 Mark Price: {position['mark_price']:.4f} USDT")
        if funding:
            print(f"💎 Funding Rate: {funding['rate']*100:.3f}% (8h)")
        
        all_actions = []
        
        # 1. Evaluate profit targets
        profit_actions = self.evaluate_profit_targets(position, current_pnl)
        all_actions.extend(profit_actions)
        
        # 2. Evaluate risk management (only if position still exists)
        if not any(action["type"] in ["stop_loss", "funding_exit"] for action in all_actions):
            risk_actions = self.evaluate_risk_management(position, account, current_pnl)
            all_actions.extend(risk_actions)
        
        # 3. Evaluate funding rules (only if position still exists)
        if not any(action["type"] in ["stop_loss", "trailing_stop", "funding_exit"] for action in all_actions):
            funding_actions = self.evaluate_funding_rules(position, funding)
            all_actions.extend(funding_actions)
        
        # Log actions
        if all_actions:
            print(f"\n📋 Actions taken this cycle: {len(all_actions)}")
            for i, action in enumerate(all_actions, 1):
                print(f"   {i}. {action['type'].upper()}: {action.get('reason', 'N/A')}")
        else:
            print("\n✅ No actions needed - position stable")
        
        return all_actions
    
    def run_continuous(self, check_interval_minutes=5):
        """Run continuous auto trading"""
        print(f"🤖 Starting Auto Smart Trader")
        print(f"⚙️  Check interval: {check_interval_minutes} minutes")
        print(f"🧪 Dry run mode: {'ON' if self.dry_run else 'OFF'}")
        print("Press Ctrl+C to stop")
        print("=" * 80)
        
        try:
            while True:
                actions = self.run_strategy_cycle()
                
                # Check if position was fully closed
                position = self.get_current_position()
                if not position:
                    print(f"\n🎯 Position fully closed. Total realized profit: {self.state['total_realized_profit']:.2f} USDT")
                    print("Stopping auto trader...")
                    break
                
                print(f"\n⏰ Next check in {check_interval_minutes} minutes...")
                print("=" * 80)
                
                time.sleep(check_interval_minutes * 60)
                
        except KeyboardInterrupt:
            print("\n👋 Auto Smart Trader stopped by user")
            
            # Show final summary
            position = self.get_current_position()
            if position:
                print(f"📊 Final Position: {position['side']} {abs(position['size']):.2f} ASTER")
                print(f"💰 Unrealized PnL: {position['pnl']:+.2f} USDT")
            print(f"💎 Total Realized Profit: {self.state['total_realized_profit']:.2f} USDT")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AsterDex Auto Smart Trader")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry run mode (no actual trades)")
    parser.add_argument("--interval", "-i", type=int, default=5, help="Check interval in minutes (default: 5)")
    parser.add_argument("--show-rules", action="store_true", help="Show trading rules and exit")
    
    args = parser.parse_args()
    
    try:
        trader = AutoSmartTrader()
        trader.dry_run = args.dry_run
        
        if args.show_rules:
            print("🎯 Auto Smart Trading Rules:")
            print("=" * 50)
            print(json.dumps(trader.rules, indent=2))
            return
        
        trader.run_continuous(args.interval)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
