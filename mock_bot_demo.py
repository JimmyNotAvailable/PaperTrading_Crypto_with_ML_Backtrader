"""
Mock Demo of Discord Bot
Shows how the bot would respond to commands without actually connecting to Discord
Perfect for testing and demonstration purposes
"""

import time
from datetime import datetime

class MockBot:
    def __init__(self):
        self.name = "Crypto ML Trading Bot"
        self.version = "1.0.0"
        self.commands = {
            "!ping": "Check bot health and latency",
            "!help": "Show all available commands",
            "!dudoan": "Get ML-based crypto price predictions",
            "!price [SYMBOL]": "Get current price and prediction for a symbol",
            "!gia [SYMBOL]": "Vietnamese version of !price",
            "!movers": "Show top gainers and losers (24h)",
            "!chart [SYMBOL]": "Display price chart for a symbol"
        }

    def simulate_ping(self):
        latency = 45  # Mock latency in ms
        return f"""
🏓 **Pong!**
Latency: `{latency}ms`
Bot is healthy and responsive! ✅
Uptime: 2h 34m
"""

    def simulate_help(self):
        help_text = f"""
📚 **{self.name} - Commands Help**

🔧 **Basic Commands:**
• `!ping` - Health check
• `!help` - Show this help message

💰 **Price & Prediction:**
• `!price [SYMBOL]` - Get current price and ML prediction
• `!gia [SYMBOL]` - Vietnamese: Xem giá và dự đoán
• `!dudoan` - Detailed ML prediction demo

📈 **Market Analysis:**
• `!movers` - Top gainers/losers in 24h
• `!chart [SYMBOL]` - Display price chart

🤖 **About:**
Version: {self.version}
ML Models: Ridge Regression, Random Forest
Data Source: Real-time Binance API

💡 **Example Usage:**
`!price BTC` - Get Bitcoin price and prediction
`!movers` - See market movers
"""
        return help_text

    def simulate_price(self, symbol="BTC"):
        predictions = {
            "BTC": {
                "name": "Bitcoin",
                "price": 67234.56,
                "change_24h": 2.34,
                "prediction": {
                    "trend": "BULLISH ⬆️",
                    "confidence": 78,
                    "next_1h": 67450,
                    "next_1h_change": 0.32
                }
            },
            "ETH": {
                "name": "Ethereum",
                "price": 3845.23,
                "change_24h": 1.87,
                "prediction": {
                    "trend": "BULLISH ⬆️",
                    "confidence": 72,
                    "next_1h": 3880,
                    "next_1h_change": 0.90
                }
            },
            "BNB": {
                "name": "Binance Coin",
                "price": 625.45,
                "change_24h": -0.56,
                "prediction": {
                    "trend": "NEUTRAL →",
                    "confidence": 65,
                    "next_1h": 624.80,
                    "next_1h_change": -0.10
                }
            }
        }

        data = predictions.get(symbol.upper(), predictions["BTC"])
        change_emoji = "📈" if data["change_24h"] > 0 else "📉"

        return f"""
💰 **{data['name']} ({symbol.upper()})**
━━━━━━━━━━━━━━━━━━━━━━━━

**Current Price:** ${data['price']:,.2f}
**24h Change:** {data['change_24h']:+.2f}% {change_emoji}

🔮 **ML Prediction:**
• Trend: {data['prediction']['trend']}
• Confidence: {data['prediction']['confidence']}%
• Next 1h: ${data['prediction']['next_1h']:,.2f} ({data['prediction']['next_1h_change']:+.2f}%)

⏰ Updated: {datetime.now().strftime('%H:%M:%S')}
"""

    def simulate_dudoan(self):
        return """
🔮 **Machine Learning Prediction Demo**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Current Market Analysis:**

**BTC (Bitcoin)**
• Current: $67,234.56
• Predicted (1h): $67,450 (+0.32%)
• Trend: BULLISH ⬆️
• Confidence: 78%

**ETH (Ethereum)**
• Current: $3,845.23
• Predicted (1h): $3,880 (+0.90%)
• Trend: BULLISH ⬆️
• Confidence: 72%

**BNB (Binance Coin)**
• Current: $625.45
• Predicted (1h): $624.80 (-0.10%)
• Trend: NEUTRAL →
• Confidence: 65%

🤖 **Model Info:**
• Algorithm: Ridge Regression + Random Forest
• Training Data: 30 days historical
• Features: Price, Volume, MA, RSI, MACD
• Accuracy: 76.5%

⚡ Real-time predictions powered by ML!
"""

    def simulate_movers(self):
        return """
📊 **Top Movers (24h)**
━━━━━━━━━━━━━━━━━━━━━

🚀 **Top Gainers:**
1. **SOL** (Solana) +8.45% 📈
   $145.67 → $157.98
   
2. **AVAX** (Avalanche) +6.23% 📈
   $38.50 → $40.90
   
3. **MATIC** (Polygon) +5.12% 📈
   $0.85 → $0.89

📉 **Top Losers:**
1. **DOGE** (Dogecoin) -4.56% 📉
   $0.082 → $0.078
   
2. **ADA** (Cardano) -3.21% 📉
   $0.62 → $0.60
   
3. **XRP** (Ripple) -2.45% 📉
   $0.53 → $0.52

⏰ Updated: {datetime.now().strftime('%H:%M:%S')}
"""

    def simulate_chart(self, symbol="BTC"):
        return f"""
📈 **{symbol.upper()} Price Chart**
━━━━━━━━━━━━━━━━━━━━━

ASCII 24h Chart:
```
68K ┤     ╭─╮
67K ┤   ╭─╯ ╰╮
66K ┤ ╭─╯    ╰─╮
65K ┤─╯        ╰─
    └──────────────
    0h    12h   24h
```

📊 **Technical Indicators:**
• MA(7): $66,890
• RSI(14): 62.5 (Neutral)
• MACD: Bullish crossover ⬆️

🔗 **Detailed Chart:**
https://www.tradingview.com/chart/?symbol=BINANCE:{symbol.upper()}USDT

⏰ {datetime.now().strftime('%H:%M:%S')}
"""

def run_mock_demo():
    """Run a mock interactive demo of the bot"""
    bot = MockBot()

    print("="*70)
    print("🤖 CRYPTO ML TRADING BOT - MOCK DEMO")
    print("="*70)
    print()
    print("This is a simulation of how the Discord bot responds to commands.")
    print("No actual Discord connection is made.")
    print()
    print("Available commands: !ping, !help, !price, !dudoan, !movers, !chart")
    print("Type 'exit' to quit")
    print()
    print("-"*70)
    print()

    # Simulate startup
    print("🔍 Bot starting...")
    time.sleep(1)
    print("✅ Bot logged in as: Crypto ML Bot#1234")
    print("✅ Connected to 1 server")
    print("✅ Bot is ready!")
    print()
    print("="*70)
    print()

    # Demo some commands
    demos = [
        ("!ping", bot.simulate_ping()),
        ("!price BTC", bot.simulate_price("BTC")),
        ("!dudoan", bot.simulate_dudoan()),
        ("!movers", bot.simulate_movers()),
        ("!help", bot.simulate_help()),
    ]

    for command, response in demos:
        print(f"👤 User: {command}")
        print()
        time.sleep(0.5)
        print(f"🤖 Bot:{response}")
        print()
        print("-"*70)
        print()
        time.sleep(1)

    print("✅ Demo completed!")
    print()
    print("💡 To run with real Discord connection:")
    print("   1. Update token.txt with valid Discord bot token")
    print("   2. Run: python -m app.bot")
    print("   3. Or use Docker: docker compose up -d demo")
    print()

if __name__ == "__main__":
    try:
        run_mock_demo()
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo stopped by user")

