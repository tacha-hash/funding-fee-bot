#!/usr/bin/env python3
"""
Trading Pair Scanner for AsterDex Auto Smart Trader
Scans and analyzes trading pairs for optimal funding arbitrage opportunities
"""
import os
import sys
import json
import time
import requests
import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode
from typing import Dict, List, Optional, Tuple
import concurrent.futures
from threading import Lock

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class PairScanner:
    def __init__(self):
        self.api_key = os.environ.get("ASTERDEX_API_KEY")
        self.api_secret = os.environ.get("ASTERDEX_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials not found")
        
        self.spot_base_url = "https://sapi.asterdex.com"
        self.futures_base_url = "https://fapi.asterdex.com"
        
        # Scanning criteria
        self.criteria = {
            # Funding rate criteria
            "min_positive_funding": 0.0005,    # 0.05% minimum positive funding
            "excellent_funding": 0.005,        # 0.5% excellent funding
            "max_negative_funding": -0.002,    # -0.2% maximum negative funding
            
            # Volume criteria (24h)
            "min_spot_volume_usdt": 100000,    # 100k USDT minimum spot volume
            "min_futures_volume_usdt": 500000, # 500k USDT minimum futures volume
            
            # Price criteria
            "min_price": 0.001,                # Minimum price 0.001 USDT
            "max_price": 1000,                 # Maximum price 1000 USDT
            "max_spread_percent": 0.5,         # Max 0.5% spread between spot/futures
            
            # Volatility criteria
            "min_24h_change": 0.02,            # Minimum 2% 24h change (volatility)
            "max_24h_change": 0.20,            # Maximum 20% 24h change (too volatile)
            
            # Position size criteria
            "min_notional": 1000,              # Minimum 1000 USDT notional
            "max_notional": 100000,            # Maximum 100k USDT notional
        }
        
        self.print_lock = Lock()
        
    def sign_params(self, params):
        """Sign API request parameters"""
        api_secret = self.api_secret.encode('utf-8')
        params.setdefault("recvWindow", 5000)
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params, doseq=True)
        signature = hmac.new(api_secret, query.encode("utf-8"), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params
    
    def make_request(self, base_url, path, params=None, signed=False):
        """Make API request with error handling"""
        url = f"{base_url}{path}"
        params = params or {}
        
        headers = {
            "X-MBX-APIKEY": self.api_key,
            "User-Agent": "PairScanner/1.0",
        }
        
        if signed:
            params = self.sign_params(params)
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                with self.print_lock:
                    print(f"⚠️ API Error {response.status_code} for {path}: {response.text[:100]}")
                return None
        except Exception as e:
            with self.print_lock:
                print(f"⚠️ Request failed for {path}: {e}")
            return None
    
    def get_spot_symbols(self):
        """Get all available spot trading symbols"""
        exchange_info = self.make_request(self.spot_base_url, "/api/v1/exchangeInfo")
        if not exchange_info:
            return []
        
        usdt_pairs = []
        for symbol in exchange_info.get("symbols", []):
            if (symbol.get("status") == "TRADING" and 
                symbol.get("quoteAsset") == "USDT" and
                symbol.get("symbol").endswith("USDT")):
                usdt_pairs.append(symbol["symbol"])
        
        return usdt_pairs
    
    def get_futures_symbols(self):
        """Get all available futures trading symbols"""
        exchange_info = self.make_request(self.futures_base_url, "/fapi/v1/exchangeInfo")
        if not exchange_info:
            return []
        
        usdt_pairs = []
        for symbol in exchange_info.get("symbols", []):
            if (symbol.get("status") == "TRADING" and 
                symbol.get("quoteAsset") == "USDT" and
                symbol.get("symbol").endswith("USDT")):
                usdt_pairs.append(symbol["symbol"])
        
        return usdt_pairs
    
    def get_spot_ticker(self, symbol):
        """Get spot ticker data"""
        ticker = self.make_request(self.spot_base_url, "/api/v1/ticker/24hr", {"symbol": symbol})
        if not ticker:
            return None
        
        return {
            "symbol": ticker["symbol"],
            "price": float(ticker["lastPrice"]),
            "volume": float(ticker["quoteVolume"]),
            "change_24h": float(ticker["priceChangePercent"]) / 100,
            "high": float(ticker["highPrice"]),
            "low": float(ticker["lowPrice"])
        }
    
    def get_futures_ticker(self, symbol):
        """Get futures ticker data"""
        ticker = self.make_request(self.futures_base_url, "/fapi/v1/ticker/24hr", {"symbol": symbol})
        if not ticker:
            return None
        
        return {
            "symbol": ticker["symbol"],
            "price": float(ticker["lastPrice"]),
            "volume": float(ticker["quoteVolume"]),
            "change_24h": float(ticker["priceChangePercent"]) / 100,
            "high": float(ticker["highPrice"]),
            "low": float(ticker["lowPrice"])
        }
    
    def get_funding_rate(self, symbol):
        """Get funding rate for futures symbol"""
        funding = self.make_request(self.futures_base_url, "/fapi/v1/premiumIndex", {"symbol": symbol})
        if not funding:
            return None
        
        return {
            "symbol": funding["symbol"],
            "funding_rate": float(funding["lastFundingRate"]),
            "mark_price": float(funding["markPrice"]),
            "index_price": float(funding["indexPrice"]),
            "next_funding_time": datetime.fromtimestamp(funding["nextFundingTime"] / 1000, timezone.utc)
        }
    
    def analyze_pair(self, symbol):
        """Analyze a single trading pair"""
        try:
            # Get data for both spot and futures
            spot_data = self.get_spot_ticker(symbol)
            futures_data = self.get_futures_ticker(symbol)
            funding_data = self.get_funding_rate(symbol)
            
            if not all([spot_data, futures_data, funding_data]):
                return None
            
            # Calculate metrics
            price_spread = abs(spot_data["price"] - futures_data["price"]) / spot_data["price"]
            funding_rate = funding_data["funding_rate"]
            daily_funding = funding_rate * 3 * 365  # Annualized
            
            # Apply filters
            if not self.meets_criteria(spot_data, futures_data, funding_data, price_spread):
                return None
            
            # Calculate score
            score = self.calculate_score(spot_data, futures_data, funding_data, price_spread)
            
            return {
                "symbol": symbol,
                "spot_price": spot_data["price"],
                "futures_price": futures_data["price"],
                "price_spread_pct": price_spread * 100,
                "funding_rate_8h": funding_rate * 100,
                "funding_rate_daily": funding_rate * 3 * 100,
                "funding_rate_annual": daily_funding * 100,
                "spot_volume_24h": spot_data["volume"],
                "futures_volume_24h": futures_data["volume"],
                "price_change_24h": spot_data["change_24h"] * 100,
                "volatility_24h": (spot_data["high"] - spot_data["low"]) / spot_data["low"] * 100,
                "next_funding": funding_data["next_funding_time"],
                "score": score,
                "recommendation": self.get_recommendation(funding_rate, score)
            }
            
        except Exception as e:
            with self.print_lock:
                print(f"⚠️ Error analyzing {symbol}: {e}")
            return None
    
    def meets_criteria(self, spot_data, futures_data, funding_data, price_spread):
        """Check if pair meets scanning criteria"""
        funding_rate = funding_data["funding_rate"]
        
        # Price criteria
        if not (self.criteria["min_price"] <= spot_data["price"] <= self.criteria["max_price"]):
            return False
        
        # Volume criteria
        if spot_data["volume"] < self.criteria["min_spot_volume_usdt"]:
            return False
        if futures_data["volume"] < self.criteria["min_futures_volume_usdt"]:
            return False
        
        # Spread criteria
        if price_spread > self.criteria["max_spread_percent"] / 100:
            return False
        
        # Volatility criteria
        change_24h = abs(spot_data["change_24h"])
        if not (self.criteria["min_24h_change"] <= change_24h <= self.criteria["max_24h_change"]):
            return False
        
        # Funding rate criteria (allow both positive and negative for different strategies)
        if funding_rate < self.criteria["max_negative_funding"]:
            return False
        
        return True
    
    def calculate_score(self, spot_data, futures_data, funding_data, price_spread):
        """Calculate opportunity score for the pair"""
        score = 0
        funding_rate = funding_data["funding_rate"]
        
        # Funding rate score (higher is better for shorts)
        if funding_rate >= self.criteria["excellent_funding"]:
            score += 50
        elif funding_rate >= self.criteria["min_positive_funding"]:
            score += 30
        elif funding_rate >= 0:
            score += 10
        else:
            score -= 20  # Negative funding is bad for shorts
        
        # Volume score (higher volume = better liquidity)
        volume_score = min(30, (spot_data["volume"] + futures_data["volume"]) / 1000000 * 10)
        score += volume_score
        
        # Spread score (lower spread = better)
        spread_score = max(0, 20 - (price_spread * 100 * 40))  # Penalize high spreads
        score += spread_score
        
        # Volatility score (moderate volatility is good)
        volatility = (spot_data["high"] - spot_data["low"]) / spot_data["low"]
        if 0.02 <= volatility <= 0.10:  # 2-10% daily range is good
            score += 20
        elif volatility > 0.20:  # Too volatile
            score -= 10
        
        return max(0, min(100, score))
    
    def get_recommendation(self, funding_rate, score):
        """Get trading recommendation based on analysis"""
        if score >= 80 and funding_rate >= self.criteria["excellent_funding"]:
            return "🎯 EXCELLENT - High priority for shorts"
        elif score >= 60 and funding_rate >= self.criteria["min_positive_funding"]:
            return "✅ GOOD - Suitable for shorts"
        elif score >= 40 and funding_rate >= 0:
            return "💛 FAIR - Consider for shorts"
        elif funding_rate < 0:
            return "⚠️ NEGATIVE FUNDING - Good for longs"
        else:
            return "❌ POOR - Not recommended"
    
    def scan_all_pairs(self, max_workers=10):
        """Scan all available pairs"""
        print("🔍 Scanning Trading Pairs...")
        print("=" * 60)
        
        # Get available symbols
        spot_symbols = self.get_spot_symbols()
        futures_symbols = self.get_futures_symbols()
        
        # Find common symbols
        common_symbols = list(set(spot_symbols) & set(futures_symbols))
        
        print(f"📊 Found {len(common_symbols)} common USDT pairs")
        print("🔄 Analyzing pairs (this may take a few minutes)...")
        
        results = []
        
        # Use ThreadPoolExecutor for concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(self.analyze_pair, symbol): symbol 
                for symbol in common_symbols
            }
            
            # Process completed tasks
            completed = 0
            for future in concurrent.futures.as_completed(future_to_symbol):
                completed += 1
                symbol = future_to_symbol[future]
                
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                    
                    # Progress indicator
                    if completed % 10 == 0:
                        with self.print_lock:
                            print(f"⏳ Progress: {completed}/{len(common_symbols)} pairs analyzed")
                            
                except Exception as e:
                    with self.print_lock:
                        print(f"⚠️ Error processing {symbol}: {e}")
        
        return results
    
    def display_results(self, results, top_n=20):
        """Display scan results"""
        if not results:
            print("❌ No pairs found matching criteria")
            return
        
        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"\n🎯 TOP {min(top_n, len(results))} TRADING OPPORTUNITIES")
        print("=" * 100)
        
        # Header
        print(f"{'Rank':<4} {'Symbol':<12} {'Score':<5} {'Funding(8h)':<11} {'Funding(Day)':<12} {'Volume(24h)':<12} {'Spread':<8} {'Recommendation'}")
        print("-" * 100)
        
        # Display top results
        for i, result in enumerate(results[:top_n], 1):
            volume_m = result["spot_volume_24h"] / 1000000
            
            print(f"{i:<4} {result['symbol']:<12} {result['score']:<5.0f} "
                  f"{result['funding_rate_8h']:<11.3f}% {result['funding_rate_daily']:<12.2f}% "
                  f"{volume_m:<12.1f}M {result['price_spread_pct']:<8.2f}% "
                  f"{result['recommendation']}")
        
        # Summary statistics
        print("\n📊 SUMMARY STATISTICS")
        print("-" * 50)
        
        positive_funding = [r for r in results if r["funding_rate_8h"] > 0]
        negative_funding = [r for r in results if r["funding_rate_8h"] < 0]
        excellent_pairs = [r for r in results if r["score"] >= 80]
        good_pairs = [r for r in results if r["score"] >= 60]
        
        print(f"📈 Total pairs analyzed: {len(results)}")
        print(f"💰 Positive funding pairs: {len(positive_funding)}")
        print(f"📉 Negative funding pairs: {len(negative_funding)}")
        print(f"🎯 Excellent opportunities (80+ score): {len(excellent_pairs)}")
        print(f"✅ Good opportunities (60+ score): {len(good_pairs)}")
        
        if positive_funding:
            avg_funding = sum(r["funding_rate_daily"] for r in positive_funding) / len(positive_funding)
            print(f"📊 Average daily funding (positive): {avg_funding:.2f}%")
        
        # Top recommendations
        print(f"\n🏆 TOP 3 RECOMMENDATIONS FOR AUTO TRADING:")
        print("-" * 50)
        
        for i, result in enumerate(results[:3], 1):
            symbol = result["symbol"]
            funding_daily = result["funding_rate_daily"]
            volume_m = result["spot_volume_24h"] / 1000000
            
            print(f"{i}. {symbol}")
            print(f"   💎 Daily funding: {funding_daily:.2f}%")
            print(f"   📊 24h volume: {volume_m:.1f}M USDT")
            print(f"   🎯 Score: {result['score']}/100")
            print(f"   💡 {result['recommendation']}")
            print()
    
    def save_results(self, results, filename="pair_scan_results.json"):
        """Save results to JSON file"""
        try:
            # Prepare data for JSON serialization
            json_data = []
            for result in results:
                json_result = result.copy()
                # Convert datetime to string
                json_result["next_funding"] = result["next_funding"].isoformat()
                json_data.append(json_result)
            
            with open(filename, 'w') as f:
                json.dump({
                    "scan_time": datetime.now().isoformat(),
                    "total_pairs": len(results),
                    "results": json_data
                }, f, indent=2)
            
            print(f"💾 Results saved to {filename}")
            
        except Exception as e:
            print(f"⚠️ Failed to save results: {e}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AsterDex Trading Pair Scanner")
    parser.add_argument("--top", "-t", type=int, default=20, help="Number of top pairs to display (default: 20)")
    parser.add_argument("--save", "-s", type=str, help="Save results to JSON file")
    parser.add_argument("--workers", "-w", type=int, default=10, help="Number of concurrent workers (default: 10)")
    parser.add_argument("--min-funding", type=float, help="Minimum funding rate (8h %)")
    parser.add_argument("--min-volume", type=float, help="Minimum spot volume (USDT)")
    
    args = parser.parse_args()
    
    try:
        scanner = PairScanner()
        
        # Override criteria if provided
        if args.min_funding:
            scanner.criteria["min_positive_funding"] = args.min_funding / 100
        if args.min_volume:
            scanner.criteria["min_spot_volume_usdt"] = args.min_volume
        
        # Run scan
        results = scanner.scan_all_pairs(max_workers=args.workers)
        
        # Display results
        scanner.display_results(results, top_n=args.top)
        
        # Save results if requested
        if args.save:
            scanner.save_results(results, args.save)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
