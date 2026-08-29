from backtesting import Strategy
import pandas as pd
import numpy as np

from core.signals import compute_signal1 as _shared_signal1


class Strategies:
    def __init__(self, df):
        self.df = df

    def signal1(self):
        frame = self.df
        # Adapt column names used by Hydra backtest CSV
        work = frame.rename(columns={"predicted_mean": "predicted_mean", "Close": "Close"})
        if "predicted_mean" not in work.columns and "prediction" in work.columns:
            work = work.rename(columns={"prediction": "predicted_mean"})
        return _shared_signal1(work).tolist()

    def signal2(self):
        signal = [0] * self.df.shape[0]
        for i in range(10, len(signal)):
            buy_bool = True
            for j in range(10):
                if self.df['predicted_high'][i] < self.df['High'][i - j]:
                    buy_bool = False
            if buy_bool is True:
                signal[i] = 2
            sell_bool = True
            for j in range(10):
                if self.df['predicted_low'][i] > self.df['Low'][i - j]:
                    sell_bool = False
            if sell_bool is True:
                signal[i] = 1
        return signal

    def signal3(self):
        buy_price = []
        sell_price = []
        macd_signal = []
        signal = 0

        for i in range(len(self.df)):
            if self.df['macd'][i] > self.df['signal'][i]:
                if signal != 2:
                    signal = 2
                    macd_signal.append(signal)
                else:
                    macd_signal.append(0)
            elif self.df['macd'][i] < self.df['signal'][i]:
                if signal != 1:
                    signal = 1
                    macd_signal.append(signal)
                else:
                    macd_signal.append(0)
            else:
                macd_signal.append(0)

        return macd_signal

    def signal4(self):
        position = False
        signal = []
        for i in range(len(self.df)):
            if self.df['sma_30'][i] > self.df['sma_100'][i]:
                if not position:
                    signal.append(2)
                    position = True
                else:
                    signal.append(0)
            elif self.df['sma_30'][i] < self.df['sma_100'][i]:
                if position:
                    signal.append(1)
                    position = False
                else:
                    signal.append(0)
            else:
                signal.append(0)
        return signal
