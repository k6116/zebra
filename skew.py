import models
from database import SessionLocal, engine
from models import Stock, Option, Skew
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
import math
import tools
import numpy as np
import datetime



def iv_skew(skew_symbol, strikes, days_to_expirations):

    iv_calls = tools.get_option_prop(skew_symbol, strikes, 'CALL', 'impliedVolatility', days_to_expirations)
    iv_puts = tools.get_option_prop(skew_symbol, strikes, 'PUT', 'impliedVolatility', days_to_expirations)

    for i in range(len(strikes)):
        if i <= round(len(strikes) / 2) - 2:
            iv_calls[i] = None
        if i >= round(len(strikes) / 2) + 2:
            iv_puts[i] = None

    return iv_calls, iv_puts
    

def premium_skew(skew_symbol, strikes, days_to_expirations):
    premium_calls_bids = tools.get_option_prop(skew_symbol, strikes, 'CALL', 'bid', days_to_expirations)
    premium_calls_asks = tools.get_option_prop(skew_symbol, strikes, 'CALL', 'ask', days_to_expirations)
    premium_puts_bids = tools.get_option_prop(skew_symbol, strikes, 'PUT', 'bid', days_to_expirations)
    premium_puts_asks = tools.get_option_prop(skew_symbol, strikes, 'PUT', 'ask', days_to_expirations)

    premium_calls_mid = (np.array(premium_calls_bids) + np.array(premium_calls_asks)) / 2.0
    premium_puts_mid = (np.array(premium_puts_bids) + np.array(premium_puts_asks)) / 2.0

    for i in range(len(strikes)):
        if i <= round(len(strikes) / 2) - 2:
            premium_calls_mid[i] = None
        if i >= round(len(strikes) / 2) + 2:
            premium_puts_mid[i] = None
        
    # print('premium_calls_mid')
    # print(premium_calls_mid)
    return premium_calls_mid, premium_puts_mid


def calc_skew_quads(symbol, underlying_price, expiration_date, days_to_expirations, batch):
    db = SessionLocal()
    options_data = db.query(Option).filter(and_(Option.symbol == symbol, Option.expirationDate == expiration_date, Option.batch == batch)).all()
    
    if len(options_data) > 0:
        # get all the strikes for the stock's option chain for an expiration
        all_strikes = tools.strike_increments(symbol, days_to_expirations)
        strike_1 = tools.find_atm_strike_index(all_strikes, underlying_price)

        if strike_1 % 2 == 1:
            strike_beg = int(math.ceil(strike_1 * 0.5))
            strike_end = int(math.ceil(strike_1 * 1.5))
        else:
            strike_beg = int(strike_1 * 0.5)
            strike_end = int((strike_1 * 1.5) + 1)

        strikes = all_strikes[strike_beg:strike_end]
        print('symbol')
        print(symbol)
        # print('strike_1')
        # print(strike_1)
        print('DTE')
        print(days_to_expirations)
        # print('all_strikes')
        # print(all_strikes)
        print('strikes')
        print(strikes)

        # get the implied volatility values for the calls and puts
        iv_calls, iv_puts = iv_skew(symbol, strikes, days_to_expirations)
        # print('iv_calls')
        # print(iv_calls)
        # print('iv_puts')
        # print(iv_puts)

        premium_calls_bids = tools.get_option_prop(symbol, strikes, 'CALL', 'bid', days_to_expirations)
        premium_calls_asks = tools.get_option_prop(symbol, strikes, 'CALL', 'ask', days_to_expirations)

        premium_calls_mid = abs((np.array(premium_calls_bids) - np.array(premium_calls_asks)))
        avg_spread = sum(premium_calls_mid) / len(premium_calls_mid)
        spread_underlying_ratio = avg_spread / float(underlying_price) * 100 

        print('spread_underlying_ratio')
        print(spread_underlying_ratio)

        # If the spread-to-underlying percent is less than 2%, liquidity is good
        if spread_underlying_ratio < 5 and len(strikes) > 5:
            insert_skew_quads(iv_puts, iv_calls, symbol, underlying_price, days_to_expirations, expiration_date, batch)

def insert_skew_quads(iv_puts, iv_calls, symbol, underlying_price, days_to_expirations, expiration_date, batch):

    db = SessionLocal()

    # Get Quad 1 (OTM Put Side)
    quad1 = 0
    iterate = 0
    for iv in iv_puts:
        if iterate < 3:
            print('Quad 1 --- ' + str(iv))
            quad1 = quad1 + iv
            iterate = iterate + 1
        else:
            break
    quad1 = quad1 / 3

    # Get Quad 2 (ITM Put Side)
    quad2 = 0
    iterate = 0
    for iv in reversed(iv_puts):
        if iv != None:
            if iterate < 3:
                print('Quad 2 --- ' + str(iv))
                quad2 = quad2 + iv
                iterate = iterate + 1
            else:
                break
    quad2 = quad2 / 3

    # Get Quad 3 (ITM Call Side)
    quad3 = 0
    iterate = 0
    for iv in iv_calls:
        if iv != None:
            if iterate < 3:
                print('Quad 3 --- ' + str(iv))
                quad3 = quad3 + iv
                iterate = iterate + 1
            else:
                break
    quad3 = quad3 / 3

    # Get Quad 4 (OTM Call Side)
    quad4 = 0
    iterate = 0
    for iv in reversed(iv_calls):
        if iterate < 3:
            print('Quad 4 --- ' + str(iv))
            quad4 = quad4 + iv
            iterate = iterate + 1
        else:
            break
    quad4 = quad4 / 3
    print('Quad1: ' + str(quad1))
    print('Quad2: ' + str(quad2))
    print('Quad3: ' + str(quad3))
    print('Quad4: ' + str(quad4))
    quad_list = [quad1, quad2, quad3, quad4]
    maxQuadDiff = max(quad_list) - min(quad_list)
    quad1v2 = quad1 - quad2
    quad1v3 = quad1 - quad3
    quad1v4 = quad1 - quad4
    quad2v3 = quad2 - quad3
    quad2v4 = quad2 - quad4
    quad3v4 = quad3 - quad4

    skew_quad = Skew()
    skew_quad.symbol = symbol
    skew_quad.underlyingPrice = underlying_price
    skew_quad.expirationDate = expiration_date
    skew_quad.daysToExpiration = days_to_expirations
    skew_quad.quad1 = quad1
    skew_quad.quad2 = quad2
    skew_quad.quad3 = quad3
    skew_quad.quad4 = quad4
    skew_quad.maxQuadDiff = maxQuadDiff
    skew_quad.quad1v2 = quad1v2
    skew_quad.quad1v3 = quad1v3
    skew_quad.quad1v4 = quad1v4
    skew_quad.quad2v3 = quad2v3
    skew_quad.quad2v4 = quad2v4
    skew_quad.quad3v4 = quad3v4
    skew_quad.calculationDate = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    skew_quad.batch = batch

    db.add(skew_quad)
    db.commit()