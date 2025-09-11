"""
Xline Simple Strategy
A simplified trading strategy for beginners
"""

from freqtrade.strategy import IStrategy
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class XlineSimpleStrategy(IStrategy):
    """
    Simple Xline Strategy using RSI and Bollinger Bands
    """

    INTERFACE_VERSION = 3

    # Strategy parameters
    minimal_roi = {
        "0": 0.10,  # 10% ROI initially
        "60": 0.05,  # 5% ROI after 60 minutes
        "120": 0.02,  # 2% ROI after 120 minutes
        "240": 0.01,  # 1% ROI after 240 minutes
    }

    stoploss = -0.05  # 5% stop loss
    timeframe = "15m"  # 15-minute timeframe

    startup_candle_count: int = 20

    def populate_indicators(self, dataframe, metadata):
        """
        Add technical indicators
        """

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lower"] = bollinger["lower"]
        dataframe["bb_middle"] = bollinger["mid"]
        dataframe["bb_upper"] = bollinger["upper"]

        # Moving Averages
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["sma_50"] = ta.SMA(dataframe, timeperiod=50)

        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        """
        Buy signal: RSI oversold + price near lower BB + uptrend
        """

        dataframe.loc[
            (
                (dataframe["rsi"] < 30)
                & (dataframe["close"] < dataframe["bb_lower"])  # RSI oversold
                & (dataframe["close"] > dataframe["sma_50"])  # Price below lower BB
                & (dataframe["volume"] > 0)  # Price above long-term MA  # Volume check
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        """
        Sell signal: RSI overbought or price near upper BB
        """

        dataframe.loc[
            (
                (dataframe["rsi"] > 70)
                | (  # RSI overbought
                    dataframe["close"] > dataframe["bb_upper"]
                )  # Price above upper BB
            ),
            "exit_long",
        ] = 1

        return dataframe
