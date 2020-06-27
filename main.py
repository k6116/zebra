import models
from models import Stock, Option, ExpectedMove, Skew
from database import SessionLocal, engine
import expected_move, skew
import tools
import config
import db_objects

import yfinance
from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from pydantic import BaseModel
from tda import auth, client
from tda.orders import EquityOrderBuilder, Duration, Session
import pandas as pd
import numpy as np

import datetime
import time
import json
import math

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

# Load the stock symbols from the text file
text_file = open("stocks.txt", "r")
stock_list = text_file.read().splitlines()

# TDA api authentication
try:
    c = auth.client_from_token_file(config.token_path, config.api_key)
except FileNotFoundError:
    from selenium import webdriver
    with webdriver.Chrome(executable_path=config.chromedriver_path) as driver:
        c = auth.client_from_login_flow(
            driver, config.api_key, config.redirect_uri, config.token_path)


def get_options_chains():

    db = SessionLocal()

    # Query the latest batch number
    options = db.query(Option.batch).order_by(desc(Option.batch)).first()

    # Increment the batch value for the database
    if options is None:
        dataset_batch = 1
    else:
        dataset_batch = options.batch + 1

    starttime=time.time()
    #  get option chain
    for stock in stock_list:
        print(stock + ' | start: ' + str(time.time()))

        # Get the options chain from TDA.
        # If no response from the api server, keep trying
        for _ in range(5):
            try:
                option_response = c.get_option_chain(stock)
                # optionsChainJSON = json.dumps(option_response.json(), indent=4)
                # print(optionsChainJSON)
                break
            except TimeoutError:
                time.sleep(0.5 - ((time.time() - starttime) % 0.5))
                pass
        
        # Get the stock quote
        quote_response = c.get_quote(stock)

        # Convert response content into json objects
        optionsChain = option_response.json()
        quote_data = quote_response.json()

        # Set the global symbol variable
        symbol = optionsChain['symbol']

        # The underlyingPrice is wrong in the options chain, so get it from the quote instead
        underlying_price = quote_data[symbol]['lastPrice']

        # Insert options chain into local database
        insert_data(symbol, optionsChain, underlying_price, dataset_batch)

        # Sleep for 0.5 seconds so we don't hit the rate limit on TDA's server
        time.sleep(0.5 - ((time.time() - starttime) % 0.5))

def insert_data(symbol, optionsChain, underlying_price, batch):
    db = SessionLocal()
    progress = '|'
    # loop through all Calls
    for exp in optionsChain['callExpDateMap']:
        print(progress)
        # Progress bar for the console
        progress = progress + '|'

        # Split the expiration date and days-to-expiration
        arrExp = exp.split(':')
        expiration_date = arrExp[0]
        days_to_expiration = arrExp[1]
        print('DTE: ' + str(days_to_expiration))

        for strike in optionsChain['callExpDateMap'][exp]:

            if len(optionsChain['callExpDateMap'][exp]) > 4 and strike in optionsChain['putExpDateMap'][exp]:

                # Insert the put/call option into the database
                for option_data in optionsChain['callExpDateMap'][exp][strike]:
                    option = db_objects.create_option_obj(symbol, option_data, underlying_price, batch, strike, expiration_date, days_to_expiration)
                    db.add(option)
                    db.commit()
                for option_data in optionsChain['putExpDateMap'][exp][strike]:
                    option = db_objects.create_option_obj(symbol, option_data, underlying_price, batch, strike, expiration_date, days_to_expiration)
                    db.add(option)
                    db.commit()
    print('Finished inserting data')
        
def get_expected_moves():
    # Calculate the expected move based on the IV and atm strikes and insert them into the database
    db = SessionLocal()

    # Query the latest batch number
    options = db.query(Option.batch).order_by(desc(Option.batch)).first()

    # Let the latest batch in the options table
    if options is None:
        batch = 1
    else:
        batch = options.batch

    for symbol in stock_list:

        options = db.query(Option.symbol, Option.underlyingPrice, Option.expirationDate, Option.daysToExpiration)

        options_data = (options
            .filter(and_(Option.symbol == symbol, Option.batch == batch))
            .distinct()
            .all()
        )

        underlying_price = float(options[0].underlyingPrice)

        for option in options_data:

            expiration_date = option[2] # [2] is the index for expirationDate
            days_to_expiration = option[3] # [2] is the index for daysToExpiration
            print('EXPIRATION: ' + str(expiration_date))

            # Get the expected move based on a calculation around option's implied volatilities
            em_iv = expected_move.get_expected_move(symbol, underlying_price, days_to_expiration)

            # Get a secondary expected move based on a calculation around atm option's premiums
            em_premium = expected_move.get_expected_move_premium(symbol, underlying_price, days_to_expiration)
            
            # Create the object for database insertion
            em = db_objects.create_em_obj(symbol, underlying_price, expiration_date, days_to_expiration, batch, em_iv, em_premium)

            db.add(em)
            db.commit()

            print('expected_move iv: ' + str(em_iv))
            print('expected_move premium: ' + str(em_premium))

def update_skew_quads():
    db = SessionLocal()

    # Query the latest batch number
    options = db.query(Option.batch).order_by(desc(Option.batch)).first()

    # Let the latest batch in the options table
    if options is None:
        batch = 1
    else:
        batch = options.batch

    options = db.query(Option.symbol, Option.underlyingPrice, Option.expirationDate, Option.daysToExpiration)

    for symbol in stock_list:
        options_data = options.filter(Option.symbol == symbol, Option.batch == batch).distinct(Option.expirationDate).all()

        underlying_price = float(options_data[0].underlyingPrice)
    
        for chain in options_data:
            expiration_date = chain[2]
            days_to_expiration = chain[3]
            if float(days_to_expiration) < 100:
                skew.calc_skew_quads(symbol, underlying_price, expiration_date, days_to_expiration, batch)

    # symbol = 'LUV'
    # expiration_date = '2020-07-17'
    # # expiration_date = '2020-08-21'
    # options_data = options.filter(Option.symbol == symbol).distinct(Option.expirationDate).all()
    # calc_skew_quads(symbol, expiration_date)

# Run the code
get_options_chains()
get_expected_moves()
update_skew_quads()
