# Xline - Advanced Crypto Auto Trading System

Xline là một hệ thống tự động giao dịch tiền điện tử tiên tiến được xây dựng dựa trên Freqtrade. Hệ thống này cung cấp các tính năng nâng cao cho việc giao dịch tự động, backtesting và quản lý rủi ro.

## Tính năng chính

- **Giao dịch tự động**: Thực hiện giao dịch tự động dựa trên chiến lược được định nghĩa
- **Backtesting**: Kiểm tra hiệu quả chiến lược với dữ liệu lịch sử
- **Live Trading**: Giao dịch trực tiếp trên các sàn giao dịch
- **Quản lý rủi ro**: Các công cụ quản lý rủi ro tiên tiến
- **Telegram Bot**: Theo dõi và điều khiển bot qua Telegram
- **Web UI**: Giao diện web để giám sát và quản lý
- **Multiple Exchanges**: Hỗ trợ nhiều sàn giao dịch khác nhau

## Cài đặt

### Yêu cầu hệ thống
- Python 3.11+
- Git

### Cài đặt dependencies

```bash
# Cài đặt dependencies cơ bản
pip install -r requirements.txt

# Cài đặt dependencies cho plotting
pip install -r requirements-plot.txt

# Cài đặt dependencies cho hyperopt
pip install -r requirements-hyperopt.txt
```

### Cài đặt Xline

```bash
# Clone repository
git clone https://github.com/your-username/xline.git
cd xline

# Cài đặt package
pip install -e .
```

## Sử dụng nhanh

### 1. Cấu hình
Tạo file cấu hình từ template:
```bash
cp config_examples/config.json.example user_data/config.json
```

### 2. Download data
```bash
xline download-data --exchange binance --pairs BTC/USDT ETH/USDT --timeframes 1h 4h 1d
```

### 3. Backtesting
```bash
xline backtesting --strategy SampleStrategy --timerange 20230101-20240101
```

### 4. Live Trading
```bash
xline trade --strategy SampleStrategy --config user_data/config.json
```

## Cấu trúc dự án

```
xline/
├── freqtrade/           # Core trading engine
├── user_data/           # User configurations and strategies
│   ├── strategies/      # Trading strategies
│   ├── data/           # Market data
│   └── notebooks/      # Jupyter notebooks for analysis
├── scripts/            # Utility scripts
├── tests/              # Test files
└── docs/               # Documentation
```

## Phát triển chiến lược

Tạo chiến lược mới trong thư mục `user_data/strategies/`:

```python
from freqtrade.strategy import IStrategy
import talib.abstract as ta

class XlineStrategy(IStrategy):
    INTERFACE_VERSION = 3
    
    # Strategy parameters
    minimal_roi = {"0": 0.1}
    stoploss = -0.05
    timeframe = '1h'
    
    def populate_indicators(self, dataframe, metadata):
        # Add your indicators here
        dataframe['rsi'] = ta.RSI(dataframe)
        return dataframe
    
    def populate_entry_trend(self, dataframe, metadata):
        # Define entry conditions
        dataframe.loc[
            (dataframe['rsi'] < 30),
            'enter_long'] = 1
        return dataframe
    
    def populate_exit_trend(self, dataframe, metadata):
        # Define exit conditions
        dataframe.loc[
            (dataframe['rsi'] > 70),
            'exit_long'] = 1
        return dataframe
```

## Cấu hình nâng cao

### Telegram Bot
Để kích hoạt Telegram bot, thêm vào file config:
```json
{
    "telegram": {
        "enabled": true,
        "token": "your_bot_token",
        "chat_id": "your_chat_id"
    }
}
```

### Web UI
Khởi động FreqUI:
```bash
freqtrade webserver --config user_data/config.json
```

## Tài liệu

- [Documentation](docs/)
- [Strategy Development](docs/strategy-development.md)
- [Configuration](docs/configuration.md)
- [Backtesting](docs/backtesting.md)

## Đóng góp

Chúng tôi hoan nghênh mọi đóng góp! Vui lòng đọc [CONTRIBUTING.md](CONTRIBUTING.md) để biết thêm chi tiết.

## License

Dự án này được phân phối dưới giấy phép GPLv3. Xem [LICENSE](LICENSE) để biết thêm chi tiết.

## Disclaimer

⚠️ **Cảnh báo rủi ro**: Giao dịch tiền điện tử có rủi ro cao. Bạn có thể mất toàn bộ số tiền đầu tư. Hãy đảm bảo bạn hiểu rõ các rủi ro và chỉ đầu tư số tiền mà bạn có thể chấp nhận mất.

## Liên hệ

- Email: xline@example.com
- Telegram: @xline_support
- Discord: [Xline Community](https://discord.gg/xline)
