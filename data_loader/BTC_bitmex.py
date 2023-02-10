import os
import logging

import pandas as pd
import math
import os.path
import time
from bitmex import bitmex
# from binance.client import Client
from datetime import timedelta, datetime
from dateutil import parser
from tqdm import tqdm_notebook #(Optional, used for progress-bars)



logger = logging.getLogger(__name__)


class BitmexDataset:
    binsizes = {"1m": 1, "5m": 5, "1h": 60, "1d": 1440}



    def __init__(self, args):
        ### API
        bitmex_api_key = ''  # Enter your own API-key here
        bitmex_api_secret = ''  # Enter your own API-secret here
        # binance_api_key = '[REDACTED]'    #Enter your own API-key here
        # binance_api_secret = '[REDACTED]' #Enter your own API-secret here
        self.batch_size = args.batch_size
        self.type = args.type
        self.bin = args.binsize
        self.bitmex_client = bitmex(test=False, api_key=bitmex_api_key, api_secret=bitmex_api_secret)

    ### FUNCTIONS
    def minutes_of_new_data(self, symbol, kline_size, data, source):
        if len(data) > 0:
            old = parser.parse(data["timestamp"].iloc[-1])
        elif source == "binance":
            old = datetime.strptime('1 Jan 2017', '%d %b %Y')
        elif source == "bitmex":
            old = \
            self.bitmex_client.Trade.Trade_getBucketed(symbol=symbol, binSize=kline_size, count=1, reverse=False).result()[
                0][0]['timestamp']
        if source == "binance": new = pd.to_datetime(
            self.binance_client.get_klines(symbol=symbol, interval=kline_size)[-1][0], unit='ms')
        if source == "bitmex": new = \
        self.bitmex_client.Trade.Trade_getBucketed(symbol=symbol, binSize=kline_size, count=1, reverse=True).result()[0][0][
            'timestamp']
        return old, new

    def get_all_bitmex(self, symbol, kline_size, save=False):
        filename = '%s-%s-data.csv' % (symbol, kline_size)
        if os.path.isfile(filename):
            data_df = pd.read_csv(filename)
        else:
            data_df = pd.DataFrame()
        oldest_point, newest_point = self.minutes_of_new_data(symbol, kline_size, data_df, source="bitmex")
        delta_min = (newest_point - oldest_point).total_seconds() / 60
        available_data = math.ceil(delta_min / self.binsizes[kline_size])
        rounds = math.ceil(available_data / self.batch_size)
        if rounds > 0:
            print('Downloading %d minutes of new data available for %s, i.e. %d instances of %s data in %d rounds.' % (
            delta_min, symbol, available_data, kline_size, rounds))
            for round_num in tqdm_notebook(range(rounds)):
                time.sleep(3)
                new_time = (oldest_point + timedelta(minutes=round_num * self.batch_size * self.binsizes[kline_size]))
                data = self.bitmex_client.Trade.Trade_getBucketed(symbol=symbol, binSize=kline_size, count=batch_size,
                                                             startTime=new_time).result()[0]
                temp_df = pd.DataFrame(data)
                data_df = data_df.append(temp_df)
        data_df.set_index('timestamp', inplace=True)
        if save and rounds > 0: data_df.to_csv(filename)
        print('All caught up..!')
        return data_df

    def get_dataset(self):
        dataset = self.get_all_bitmex(self.type, self.bin, save=True)
        return dataset




