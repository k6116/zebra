import http
import json
import pandas as pd
import calendar
import os
from datetime import timedelta, date, datetime
from typing import Dict, List, Tuple
from http import client
from database import SessionLocal, engine
import models
from models import HistOption, HistStock
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
import yfinance as yf
import math

models.Base.metadata.create_all(bind=engine)

symbol = ''
text_file = open("stocks.txt", "r")
stock_list = text_file.read().splitlines()

class Tradier:
    def __init__(self, auth: str, storage_path="C:/WebDev/"):
        self.storage_path = storage_path
        self.connection = http.client.HTTPSConnection(
            "sandbox.tradier.com", 443, timeout=30)
        self.headers = headers = {"Accept": "application/json",
                                  "Authorization": "Bearer {}".format(auth)}
 
    def request(self, endpoint: str):
        self.connection.request("GET", endpoint, None, self.headers)
        try:
            response = self.connection.getresponse()
            content = response.read()
            # print(content)
            if int(str(response.status)) == 200:
                return json.loads(bytes.decode(content))
            return None
        except http.HTTPException as e:
            return e
 
    def options(self, symbol: str, year: int):
        return Options(self, symbol, year)
 
    def historical_data(self, symbol: str, year: int):
        endpoint = "/v1/markets/history?symbol={}&start={}-01-01".format(symbol, year)
        # print(endpoint)
        return self.request(endpoint)

    def load_data(self, symbol: str, year: int) -> pd.DataFrame:
        # df = pd.DataFrame(self.historical_data(symbol, year).get("history", {}).get("day", []))
        if self.historical_data(symbol, year) is None:
            return None
        else:
            history = self.historical_data(symbol, year).get("history", {})
            if history is None:
                return None
            else:
                day = history.get("day", [])
                if not isinstance(day, list):
                    day = [].append(day)
                df1 = pd.DataFrame(day)
                df2 = df1[~df1.isin(['NaN', 'NaT']).any(axis=1)] # Remove rows that contain NaN
                return df2

 
 
def third_fridays(d, n):
    """Given a date, calculates n next third fridays
   https://stackoverflow.com/questions/28680896/how-can-i-get-the-3rd-friday-of-a-month-in-python/28681097"""
 
    def next_third_friday(d):
        """ Given a third friday find next third friday"""
        d += timedelta(weeks=4)
        return d if d.day >= 15 else d + timedelta(weeks=1)
 
    # Find closest friday to 15th of month
    s = date(d.year, d.month, 15)
    result = [s + timedelta(days=(calendar.FRIDAY - s.weekday()) % 7)]
 
    # This month's third friday passed. Find next.
    if result[0] < d:
        result[0] = next_third_friday(result[0])
 
    for i in range(n - 1):
        result.append(next_third_friday(result[-1]))
 
    return result
 
 
class Options:
    def __init__(self, tradier: Tradier, symbol: str, year: int):
        self.api = tradier
        self.symbol = symbol
        self.year = year
        self.cache = {}
 
    def call(self, expiration: date, strike: int) -> pd.DataFrame:
        chain = "{symbol}{y}{m:02d}{d:02d}C{strike:05d}000".format(symbol=self.symbol, y=str(
            expiration.year)[2:], m=expiration.month, d=expiration.day, strike=strike)
        df = self.api.load_data(chain, self.year)
        # print('callcallcallcallcall')
        # print(chain)
        if df is not None:
            df_obj = df.to_dict('index')
            self.insert_data(self.symbol, strike, expiration, df_obj, 'CALL')
            return df

    def put(self, expiration: date, strike: int) -> pd.DataFrame:
        chain = "{symbol}{y}{m:02d}{d:02d}P{strike:05d}000".format(symbol=self.symbol, y=str(
            expiration.year)[2:], m=expiration.month, d=expiration.day, strike=strike)
        df = self.api.load_data(chain, self.year)
        # print('putputputputputputputput')
        # print(chain)
        if df is not None:
            df_obj = df.to_dict('index')
            self.insert_data(self.symbol, strike, expiration, df_obj, 'PUT')
            return df

    def initialize_repository(self):
        '''
       Download all of the historical price data for all monthly expirations within a 10%
       price range of the underlying for that month. This can be manually changed in the code
       below. By default, this downloads data from 2018 only. Beyond that is an exercise for the reader
       '''
        print('year: ' + str(self.year))
        # historical price data for the underlying, which we will merge in
        data = self.api.load_data(self.symbol, self.year)

        # calculate monthly high and low for the underlying
        monthly_range = {}
        for m in range(1, 13):
            # If Jan, start from first week of Jan instead of previous Dec
            if m == 1:
                expiration1 = datetime.strftime(date(self.year, m, 1), '%Y-%m-%d')
            else:
                expiration1 = third_fridays(date(self.year, m, 1), 1)[0]
            
            if m == 1:
                expiration2 = third_fridays(date(self.year, m, 1), 1)[0]
            elif m == 12: # if Dec, get the expiration for next year's Jan
                expiration2 = third_fridays(date(self.year + 1, 1, 1), 1)[0]
            else:
                expiration2 = third_fridays(date(self.year, m + 1, 1), 1)[0]
            
            mask = (data['date'] >= str(expiration1)) & (data['date'] <= str(expiration2))
            x = data.loc[mask]
            print(x)

            if x.empty:
                break
            else:
                monthly_range[m] = dict(low=min(x['low']), high=max(x['high']))
                
 
        for m, k in monthly_range.items():
            expiration = third_fridays(date(self.year, m, 1), 1)[0]
            # Get all strikes that are 10% below the monthly low and 10% above the monthly high

            strikes = [x for x in range(int(k['low'] * .9), int(k['high'] * 1.1))]
            if len(strikes) == 0:
                break
            else:
                # Download and save all of the option chains
                for s in strikes:
                    print('STRIKE: ' + str(s) + ' | Exp: ' + str(expiration))
                    self.call(expiration, s)
                    self.put(expiration, s)

# # ------------- Test Single Exp Date -------------------
#         # historical price data for the underlying, which we will merge in
#         data = self.api.load_data(self.symbol)

#         # calculate monthly high and low for the underlying
#         x = data[date(2020, 2, 1):date(2020, 2 + 1, 1)]

#         expiration = third_fridays(date(2020, 2, 1), 1)[0]
#         # Get all strikes that are 10% below the monthly low and 10% above the monthly high
#         strikes = [120, 130]

#         # Download and save all of the option chains
#         for s in strikes:
#             self.call(expiration, s)
#             self.put(expiration, s)

    def insert_data(self, symbol, strike, expiration, options, putCall):
        db = SessionLocal()
        db_options = []

        for key, value in options.items():
            date = value['date']
            datestamp = datetime.strptime(date, '%Y-%m-%d').date()
            insert_option = HistOption(
            symbol = symbol,
            strike = strike,
            putCall = putCall,
            expirationDate = expiration,
            daysToExpiration = (expiration - datestamp).days,
            open = value['open'],
            high = value['high'],
            low = value['low'],
            close = value['close'],
            volume = value['volume'],
            date = date
            )
            db_options.append(insert_option)
        db.bulk_save_objects(db_options)
        db.commit()

    def insert_stock_data(self, data):
        db = SessionLocal()
        db_stocks = []
        for key, value in data.items():
            date = str(key).split(' ')
            insert_stock = HistStock(
            symbol = self.symbol,
            date = date[0],
            open = value['Open'],
            high = value['High'],
            low = value['Low'],
            close = value['Close'],
            volume = value['Volume'],
            )
            db_stocks.append(insert_stock)
        db.bulk_save_objects(db_stocks)
        db.commit()

    def test(self):
        print('awefliufeh')
        # df = self.api.historical_data('SPY200619C00300000', self.year)
        df = self.api.historical_data('SPY190719C00253000', self.year)
        # df = self.api.historical_data('AAPL200619C00355000', self.year)
        # AAPL200619C00355000

api = Tradier("UNAGUmPNt1GPXWwWUxUGi4ekynpj")
start_year = 2020

for symbol in stock_list:
    stock = yf.Ticker(symbol)
    stock_hist = stock.history(period="10y")
    stock_data = stock_hist.to_dict('index')
    api.options(symbol, start_year).insert_stock_data(stock_data)

    print(symbol)
    for x in range(1):
        year = start_year + x
        api.options(symbol, year).initialize_repository()

# api.options('SPY', 2015).test()