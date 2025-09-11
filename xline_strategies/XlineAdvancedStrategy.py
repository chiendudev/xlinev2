"""
Xline Advanced Strategy Template
"""

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class XlineAdvancedStrategy(IStrategy):
    """
    Xline Advanced Trading Strategy

    This strategy combines multiple technical indicators with advanced
    risk management and position sizing.
    """

    INTERFACE_VERSION = 3

    # Strategy parameters
    minimal_roi = {
        "0": 0.20,  # 20% ROI initially
        "60": 0.10,  # 10% ROI after 60 minutes
        "120": 0.05,  # 5% ROI after 120 minutes
        "240": 0.02,  # 2% ROI after 240 minutes (exit)
    }

    stoploss = -0.08  # 8% stop loss
    timeframe = "5m"  # 5-minute timeframe

    # Hyperopt parameters
    rsi_buy = IntParameter(20, 40, default=30, space="buy")
    rsi_sell = IntParameter(60, 80, default=70, space="sell")
    bb_period = IntParameter(10, 30, default=20, space="buy")
    bb_std = DecimalParameter(1.5, 2.5, default=2.0, space="buy")

    # Position management
    use_custom_stoploss = True
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.05

    # Advanced features
    process_only_new_candles = True
    startup_candle_count: int = 30

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Populate indicators that will be used in entry and exit strategies
        """

        # RSI (Relative Strength Index)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=self.bb_period.value, stds=self.bb_std.value
        )
        dataframe["bb_lower"] = bollinger["lower"]
        dataframe["bb_middle"] = bollinger["mid"]
        dataframe["bb_upper"] = bollinger["upper"]
        dataframe["bb_percent"] = (dataframe["close"] - dataframe["bb_lower"]) / (
            dataframe["bb_upper"] - dataframe["bb_lower"]
        )

        # MACD
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        # EMA (Exponential Moving Averages)
        dataframe["ema_9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)

        # Volume indicators
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)

        # ATR for volatility
        dataframe["atr"] = ta.ATR(dataframe)

        # Support and Resistance levels
        dataframe["support"] = dataframe["low"].rolling(window=20).min()
        dataframe["resistance"] = dataframe["high"].rolling(window=20).max()

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define the buy signal conditions
        """

        dataframe.loc[
            (
                # RSI oversold
                (dataframe["rsi"] < self.rsi_buy.value)
                &
                # Price near lower Bollinger Band
                (dataframe["bb_percent"] < 0.2)
                &
                # MACD bullish divergence
                (dataframe["macd"] > dataframe["macdsignal"])
                &
                # Price above EMA 9
                (dataframe["close"] > dataframe["ema_9"])
                &
                # EMA trending up
                (dataframe["ema_9"] > dataframe["ema_21"])
                &
                # Volume higher than average
                (dataframe["volume"] > dataframe["volume_sma"] * 1.2)
                &
                # Price above support
                (dataframe["close"] > dataframe["support"] * 1.01)
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define the sell signal conditions
        """

        dataframe.loc[
            (
                # RSI overbought
                (dataframe["rsi"] > self.rsi_sell.value)
                |
                # Price near upper Bollinger Band
                (dataframe["bb_percent"] > 0.8)
                |
                # MACD bearish divergence
                (dataframe["macd"] < dataframe["macdsignal"])
                |
                # Price below EMA 9
                (dataframe["close"] < dataframe["ema_9"])
                |
                # Price near resistance
                (dataframe["close"] > dataframe["resistance"] * 0.99)
            ),
            "exit_long",
        ] = 1

        return dataframe

    def custom_stoploss(
        self,
        pair: str,
        trade: "Trade",
        current_time: "datetime",
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> float:
        """
        Custom stoploss implementation with trailing stop
        """

        # Get the trade duration in minutes
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 60

        # Dynamic stoploss based on trade duration
        if trade_duration < 60:
            return -0.08  # 8% stoploss for first hour
        elif trade_duration < 240:
            return -0.05  # 5% stoploss after first hour
        else:
            return -0.03  # 3% stoploss after 4 hours

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: "datetime",
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> bool:
        """
        Confirm trade entry with additional checks
        """

        # Add any additional confirmation logic here
        # For example, check market conditions, news, etc.

        return True

    def custom_exit(
        self,
        pair: str,
        trade: "Trade",
        current_time: "datetime",
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        """
        Custom exit logic
        """

        # Take profit at 15% for quick gains
        if current_profit > 0.15:
            return "quick_profit_15"

        # Exit if profit drops below 5% after being above 10%
        if hasattr(trade, "max_profit_reached"):
            if trade.max_profit_reached > 0.10 and current_profit < 0.05:
                return "profit_protection"
        else:
            trade.max_profit_reached = current_profit

        if current_profit > trade.max_profit_reached:
            trade.max_profit_reached = current_profit

        return None

    def informative_pairs(self):
        """
        Define additional informative pairs/timeframes
        """
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, "1h") for pair in pairs]
        return informative_pairs
