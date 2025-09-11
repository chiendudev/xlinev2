#!/bin/bash

# Xline Quick Start Script
# Hướng dẫn sử dụng nhanh hệ thống Xline

echo "🚀 Xline - Advanced Crypto Auto Trading System"
echo "==============================================="

# Kiểm tra Python environment
if [ ! -d ".venv" ]; then
    echo "❌ Python virtual environment not found!"
    echo "Please run: python -m venv .venv && source .venv/bin/activate"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

echo "✅ Python environment activated"

# Kiểm tra cài đặt
echo "📋 Checking Xline installation..."
python xline.py --version

echo ""
echo "🔧 Available commands:"
echo "----------------------"
echo "1. Create config:       cp user_data/config.json.example user_data/config.json"
echo "2. Download data:       python xline.py download-data --exchange binance --pairs BTC/USDT --timeframes 1h"
echo "3. Backtest strategy:   python xline.py backtesting --strategy XlineSimpleStrategy"
echo "4. Dry run trading:     python xline.py trade --strategy XlineSimpleStrategy --config user_data/config.json"
echo "5. Web interface:       python xline.py webserver --config user_data/config.json"
echo ""

# Check if config exists
if [ ! -f "user_data/config.json" ]; then
    echo "⚠️  Configuration file not found!"
    echo "   Creating from template..."
    cp user_data/config.json.example user_data/config.json
    echo "✅ Config created at user_data/config.json"
    echo "   Please edit this file with your exchange API keys"
    echo ""
fi

echo "📚 Quick start:"
echo "   1. Edit user_data/config.json with your API keys"
echo "   2. Run: python xline.py download-data --exchange binance --pairs BTC/USDT --timeframes 1h --days 30"
echo "   3. Run: python xline.py backtesting --strategy XlineSimpleStrategy"
echo ""
echo "⚠️  Remember: Always test with dry-run before live trading!"
echo "💡 For detailed documentation, see README_XLINE.md"
