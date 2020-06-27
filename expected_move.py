import models
from database import SessionLocal, engine
from models import Stock, Option
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
import math
import tools
import numpy as np


def get_expected_move(symbol, underlying_price, dte):
    two_atm_call_iv = None
    strikes = tools.strike_increments(symbol, dte)
    # print('strikes')
    # print(strikes)
    # print('underlying_price')
    # print(underlying_price)

    if strikes[0] < underlying_price and underlying_price < strikes[len(strikes) - 1]:
        two_atm_strikes = two_ntm_strikes(strikes, underlying_price)
        two_atm_call_iv = tools.get_option_prop(symbol, two_atm_strikes, 'CALL', 'impliedVolatility', dte)
        two_atm_put_iv = tools.get_option_prop(symbol, two_atm_strikes, 'PUT', 'impliedVolatility', dte)
        print('dte: ' + str(dte))
        print('two_atm_strikes')
        print(two_atm_strikes)
        # print('two_atm_call_iv')
        # print(two_atm_call_iv)
        expected_move_iv = calc_expected_move_iv(underlying_price, two_atm_call_iv, two_atm_put_iv, dte)
        return expected_move_iv

    else:

        return None

def calc_expected_move_iv(underlying_price, call_iv, put_iv, dte):

    iv_sum = 0
    for val in call_iv:
        iv_sum = iv_sum + val
        # print('iv_sum: ' + str(iv_sum))
    for val in put_iv:
        iv_sum = iv_sum + val
        # print('iv_sum: ' + str(iv_sum))
    
    avg_iv = iv_sum / 4
    expected_move = float(underlying_price) * (float(avg_iv) / 100) * (math.sqrt(int(dte)) / math.sqrt(365))
    # print('iv: ' + str(avg_iv))
    return expected_move

def two_ntm_strikes(strikes, underlying_price):

    # find 2 near-the-money strikes

    # First find the atm_strike
    strike_1 = tools.find_atm_strike_index(strikes, underlying_price)

    # If the underlying_price is less than the initial strike price
    if (underlying_price < strikes[strike_1]):
        strike_2 = strike_1 - 1
    else:
        strike_2 = strike_1 + 1

    return sorted([strikes[strike_1], strikes[strike_2]], key=float)

def get_expected_move_premium(symbol, underlying_price, dte):
    strikes = tools.strike_increments(symbol, dte)

    if strikes[0] < underlying_price and underlying_price < strikes[len(strikes) - 1]:
        if len(strikes) > 1:

            two_atm_strikes = two_ntm_strikes(strikes, underlying_price)
            two_premium_calls_bids = tools.get_option_prop(symbol, two_atm_strikes, 'CALL', 'bid', dte)
            two_premium_calls_asks = tools.get_option_prop(symbol, two_atm_strikes, 'CALL', 'ask', dte)
            two_premium_puts_bids = tools.get_option_prop(symbol, two_atm_strikes, 'PUT', 'bid', dte)
            two_premium_puts_asks = tools.get_option_prop(symbol, two_atm_strikes, 'PUT', 'ask', dte)

            # Since the underlying price won't be exactly on a strike, calculate the weighted difference between the nearest strikes
            strike_diff = abs(two_atm_strikes[1] - two_atm_strikes[0])
            price_distance = abs(underlying_price - two_atm_strikes[1])
            price_distance_percent = price_distance / strike_diff

            two_premium_calls_mid = (np.array(two_premium_calls_bids) + np.array(two_premium_calls_asks)) / 2.0
            two_premium_puts_mid = (np.array(two_premium_puts_bids) + np.array(two_premium_puts_asks)) / 2.0
            
            two_premium_calls_mid_diff = abs(two_premium_calls_mid[1] - two_premium_calls_mid[0])
            two_premium_puts_mid_diff = abs(two_premium_puts_mid[1] - two_premium_puts_mid[0])

            premium_call = two_premium_calls_mid[1] + (two_premium_calls_mid_diff * price_distance_percent)
            premium_put = two_premium_puts_mid[1] - (two_premium_puts_mid_diff * price_distance_percent)
            # print('premium_put')
            # print(premium_put)
            expected_move_premium = calc_expected_move_premium(underlying_price, premium_call, premium_put, dte)

            return expected_move_premium

    else:
        return None

def calc_expected_move_premium(underlying_price, prem_call, prem_put, dte):

    # average the two calls and puts premiums
    total_prem = prem_call + prem_put

    expected_move_premium_percent = total_prem * 85 / underlying_price
    expected_move_calc = expected_move_premium_percent / 100 * underlying_price

    return expected_move_calc
