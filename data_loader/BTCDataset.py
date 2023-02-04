import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class BTCDataset:
    dataset = []

    def __init__(self, main_features, start_date=None, end_date=None, window_size=10):
        import requests

        # Fetching data from the server
        url = "https://web-api.coinmarketcap.com/v1/cryptocurrency/ohlcv/historical"
        # param = {"convert":"USD","slug":"bitcoin","time_end":"1601510400","time_start":"1367107200"}
        param = {"convert": "USD", "slug": "bitcoin", "time_end": "1672384689", "time_start": "1367107200"}
        content = requests.get(url=url, params=param).json()
        df = pd.json_normalize(content['data']['quotes'])

        # Extracting and renaming the important variables
        df['Date'] = pd.to_datetime(df['quote.USD.timestamp']).dt.tz_localize(None)
        df['Low'] = df['quote.USD.low']
        df['High'] = df['quote.USD.high']
        df['Open'] = df['quote.USD.open']
        df['Close'] = df['quote.USD.close']
        df['Volume'] = df['quote.USD.volume']

        # Drop original and redundant columns
        df = df.drop(columns=['time_open', 'time_close', 'time_high', 'time_low', 'quote.USD.low', 'quote.USD.high',
                              'quote.USD.open', 'quote.USD.close', 'quote.USD.volume', 'quote.USD.market_cap',
                              'quote.USD.timestamp'])

        # Creating a new feature for better representing day-wise values
        df['Mean'] = (df['Low'] + df['High']) / 2

        # Cleaning the data for any NaN or Null fields
        df = df.dropna()

        # Creating a copy for making small changes
        dataset_for_prediction = df.copy()
        # print(dataset_for_prediction.keys())
        dataset_for_prediction['Actual'] = dataset_for_prediction['Mean'].shift()
        dataset_for_prediction = dataset_for_prediction.dropna()

        # date time typecast
        dataset_for_prediction['Date'] = pd.to_datetime(dataset_for_prediction['Date'])
        dataset_for_prediction.index = dataset_for_prediction['Date']

        drop_cols = ['High', 'Low', 'Close', 'Open', 'Volume', 'Mean']
        for item in main_features:
            if item in drop_cols:
                drop_cols.remove(item)
        df = df.drop(drop_cols, axis=1)

        if start_date == '-1':
            start_date = df.iloc[0].Date
        else:
            start_date = datetime.strptime(str(start_date), '%Y-%m-%d %H:%M:%S')

        if end_date == '-1':
            end_date = df.iloc[-1].Date
        else:
            end_date = datetime.strptime(str(end_date), '%Y-%m-%d %H:%M:%S')

        start_index = 0
        end_index = df.shape[0] - 1
        for i in range(df.shape[0]):
            if df.Date[i] <= start_date:
                start_index = i

        for i in range(df.shape[0] - 1, -1, -1):
            if df.Date[i] >= end_date:
                end_index = i

        # prediction mean based upon open
        dates = df.Date[start_index:end_index]
        df = df.drop('Date', axis=1)
        arr = np.array(df, dtype='float32')
        arr = arr[start_index:end_index]
        features = df.columns

        self.create_dataset(arr, list(dates), look_back=window_size, features=features)

    def create_dataset(self, dataset, dates, look_back, features):
        data_x = []
        for i in range(len(dataset) - look_back - 1):
            a = dataset[i:(i + look_back), :]
            a = a.reshape(-1)
            b = [dates[i]]
            b = b + a.tolist()
            b.append(dataset[(i + look_back), :][-1])
            data_x.append(b)
        data_x = np.array(data_x)

        date_col = "Date"
        response_col = "prediction"
        regressor_col = []
        cols = ['Date']
        counter = 0
        counter_date = 0
        for i in range(data_x.shape[1] - 2):
            name = features[counter]
            regressor_col.append(f'{name}_{dates[counter_date]}')
            cols.append(f'{name}_{dates[counter_date]}')
            counter += 1
            if counter >= len(features):
                counter = 0
                counter_date += 1

        cols.append('prediction')

        data_frame = pd.DataFrame(data_x, columns=cols)

        self.dataset = data_frame

    def get_dataset(self):
        return self.dataset